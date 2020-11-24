import base64
import boto3
from botocore.exceptions import ClientError
from enum import Enum
import json
import logging
import requests
from urllib3 import Retry


log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


PRISMA_COMPUTE_REST_API_URL = (
    "https://us-east1.cloud.twistlock.com/us-2-158254964/api/v1"
)


class ExitPrismaCleaner(Exception):
    """Exiting Prisma Cleaner due to fatal failure"""

    pass


class SecretManagerRetrievalError(Exception):
    """Unable to retrieve API keys from Secret Manager"""

    pass


class HTTPMethod(Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"


def lambda_handler(event, context):
    init()

    try:
        token = get_prisma_token()
        registry = get_prisma_registry(token)
        trim_prisma_registry(registry)
        put_prisma_registry(token, registry)

        return {"statusCode": 200, "body": json.dumps("Successfully Updated")}
    except:
        log.exception("Error while executing prisma cleaner")
        raise


def trim_prisma_registry(registry):
    """Trim prisma registry"""
    registry["specifications"] = []


def put_prisma_registry(token, registry):
    """Override prisma registry setting"""

    return invoke_prisma_api(
        HTTPMethod.PUT, "/settings/registry", payload=registry, token=token
    )


def get_prisma_registry(token):
    """Fetch Prisma Registry"""

    return invoke_prisma_api(HTTPMethod.GET, "/settings/registry", token=token)


def get_prisma_secrets():
    """Retrieve prisma secrets from AWS secretsmanager"""
    log.info("Fetching Prisma AccessKeys from Secrets Manager.")
    secret_name = "PrismaAccessKeys"
    region_name = "us-east-1"

    client = boto3.client("secretsmanager", region_name)

    try:
        response = client.get_secret_value(SecretId=secret_name)
    except ClientError:
        raise SecretManagerRetrievalError
    else:
        # Depending on whether the secret is a string or binary, one of these fields will be populated.
        if "SecretString" in response:
            response_secret = response["SecretString"]
        else:
            response_secret = base64.b64decode(response["SecretBinary"])

    secret = json.loads(response_secret)

    if not secret:
        log.error("Unable to retrieve access keys")
        raise SecretManagerRetrievalError

    log.info("Successfully fetched an AccessKeys from Secrets Manager.")
    return secret


def invoke_prisma_api(http_method, route, payload=None, token=None):
    """Helper function to make Prisma API request"""
    headers = None
    response = None
    full_url = f"{PRISMA_COMPUTE_REST_API_URL}{route}"
    pp_request = f"{http_method.value}{route}"
    payload = json.dumps(payload)

    log.info(f"Invoking {pp_request} to Prisma API")

    # As we may hit Prisma API limits, try hitting Prisma at least 3 times before shutting down Vulnerability Scanner
    retries = Retry(
        total=3,
        status_forcelist={429, 501, 502, 503, 504},
        backoff_factor=1,
        respect_retry_after_header=True,
    )

    if token is not None:
        headers = {"Authorization": f"Bearer {token}"}
    else:
        headers = {"content-type": "application/json; charset=UTF-8"}

    try:
        adapter = requests.adapters.HTTPAdapter(max_retries=retries)

        # initiate the session and then attach the Retry adaptor.
        session = requests.Session()
        session.mount("https://", adapter)
        session.headers = headers

        if http_method is HTTPMethod.POST:
            response = session.post(full_url, data=payload, timeout=5.0)
        elif http_method is HTTPMethod.PUT:
            response = session.put(full_url, data=payload, timeout=60.0)
        else:
            response = session.get(full_url, data=payload, timeout=5.0)
    except:
        log.exception(f"Exception occurred in making {pp_request} to Prisma API")
        raise ExitPrismaCleaner

    status_code = response.status_code

    if status_code != 200:
        log.error(f"Prisma API {pp_request} failed with status code: {status_code}")
        raise ExitPrismaCleaner

    log.info(f"Successfully Invoked {pp_request} to Prisma API")

    if not response.text:
        return {}

    return json.loads(response.text)


def get_prisma_token():
    """Fetch Prisma Access key and secret key id from Secret Manager"""

    prisma_secret = get_prisma_secrets()

    payload = {
        "username": prisma_secret["prismaAccessKeyId"],
        "password": prisma_secret["prismaSecretKey"],
    }

    response = invoke_prisma_api(HTTPMethod.POST, "/authenticate", payload)
    token = response["token"]

    return token


def init():
    logging.basicConfig(
        level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s"
    )
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("boto3").setLevel(logging.INFO)
    logging.getLogger("urllib3").setLevel(logging.CRITICAL)


def main():
    # main() is useful for testing locally. not used when run in Lambda
    test_event = {
        "function-name": "echo",
        "new-version": "1",
        "alias-name": "myalias",
        "steps": 10,
        "interval": 5,
        "type": "linear",
        "health-check": True,
    }
    log.info(lambda_handler(test_event, ""))


if __name__ == "__main__":
    main()
