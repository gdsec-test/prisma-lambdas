#!/bin/bash

# Setup

## Create .venv for deploy.
echo "[+] Creating deploy virtual environment."
python3 -m venv .venv-deploy
source .venv-deploy/bin/activate
pip install -q --upgrade pip
pip install -qr requirements.txt

## Create .venv-local for commands.
echo "[+] Creating and Swithcing to local virtual environment."
python3 -m venv .venv-local
source .venv-local/bin/activate
pip install -q --upgrade pip
pip install -qr requirements-local.txt

# Variables

OPERATION=${1:-create} # create or update
ENVIRONMENT=${2:-dev-private}
PROJECT_CODE="prisma-lambdas"
BUCKET_NAME="gd-security-${ENVIRONMENT}-${PROJECT_CODE}-bucket"
LAMBDA_NAMES=("prisma-registry-cleaner")

function doExitCheck() {
    if [ "$?" -ne 0 ]; then
        echo "[-] Error found, exiting."
        exit 1
    fi
}

# Operation

for LAMBDA_NAME in "${LAMBDA_NAMES[@]}"
do
    LAMBDA_ZIP_NAME="${LAMBDA_NAME}.zip"
    if [ "${OPERATION}" == "create" ]; then
        printf "\n[+] Initiating ${LAMBDA_ZIP_NAME} creation.\n"

        echo "[+] Packaging site packages into ${LAMBDA_ZIP_NAME}"
        pushd ${PWD}/.venv-deploy/lib/python3.8/site-packages
        zip -r9q ${OLDPWD}/${LAMBDA_ZIP_NAME} .
        popd

        echo "[+] Packaging main.py into ${LAMBDA_ZIP_NAME}"
        pushd ${PWD}/src/${LAMBDA_NAME}
        zip -gq ${OLDPWD}/${LAMBDA_ZIP_NAME} main.py
        popd

        echo "[+] Publishing ${LAMBDA_ZIP_NAME} to s3."
        aws s3 cp ${LAMBDA_ZIP_NAME} s3://${BUCKET_NAME}/${LAMBDA_ZIP_NAME} --acl private
        doExitCheck

        echo "[+] Removing local ${LAMBDA_ZIP_NAME}"
        rm -rf ${LAMBDA_ZIP_NAME}
    fi
done

# Cleanup

echo "[+] Removing deploy virtual environment."
rm -rf ./.venv-deploy
