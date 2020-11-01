# prisma-lambdas

![Tartufo : main](https://github.com/gdcorp-infosec/prisma-lambdas/workflows/Tartufo%20Validate%20Workflow/badge.svg?branch=main)

Repostiory for Prisma related lambda processes.

## Supported Lambdas

- Prisma Registry Cleaner
  - Cleans Registry setting on Prisma every day.
- Prisma Secret Rotator
  - Rotate Prisma Secrets every 30 days.

## How to run

### Setup Local Environment
```bash
$ python3 -m venv .venv-local
$ source .venv-local/bin/activate
(venv-local) $ $ pip install --upgrade pip
(venv-local) $ pip install -r requirements-local.txt
(venv-local) $ pre-commit install --install-hooks
```

### Creating Infrastructure
```bash
# Authenticate to specific AWS account.
(venv-local) $ OKTA_DOMAIN="godaddy.okta.com"; KEY=$(openssl rand -hex 18); eval $(aws-okta-processor authenticate -e -o $OKTA_DOMAIN -u $USER -k $KEY)

# Run sceptre to build infrasturcture & deploy lambda. ex) dev-private
(venv-local) $ sceptre create dev-private

##### You may need to go remove all versions of zip files from the S3 bucket before next step.

# [WHEN DONE] Remove infrastructure. ex) dev-private
(venv-local) $ sceptre delete dev-private

# Clean up virtualenv
(venv-local) $ deactivate && rm -rf .venv-local
```
