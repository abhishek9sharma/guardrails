import sys
from string import Template
from typing import Any, Dict, Optional

import requests
from guardrails_hub_types import Manifest
from jwt import JWT
from jwt.exceptions import JWTDecodeError

from guardrails.classes.credentials import Credentials
from guardrails.cli.logger import logger

TOKEN_EXPIRED_MESSAGE = (
    "Your token has expired. Please run `guardrails configure` to update your token."
)
TOKEN_INVALID_MESSAGE = (
    "Your token is invalid. Please run `guardrails configure` to update your token."
)

validator_hub_service = "https://so4sg4q4pb.execute-api.us-east-1.amazonaws.com"
validator_manifest_endpoint = Template(
    "validator-manifests/${namespace}/${validator_name}"
)


class AuthenticationError(Exception):
    pass


class HttpError(Exception):
    status: int
    message: str


def fetch(url: str, token: Optional[str], anonymousUserId: Optional[str]):
    try:
        # For Debugging
        # headers = { "Authorization": f"Bearer {token}", "x-anonymous-user-id": anonymousUserId, "Cache-Control": "no-cache" }  # noqa
        headers = {
            "Authorization": f"Bearer {token}",
            "x-anonymous-user-id": anonymousUserId,
        }
        req = requests.get(url, headers=headers)
        body = req.json()

        if not req.ok:
            logger.error(req.status_code)
            logger.error(body.get("message"))
            http_error = HttpError()
            http_error.status = req.status_code
            http_error.message = body.get("message")
            raise http_error

        return body
    except HttpError as http_e:
        raise http_e
    except Exception as e:
        logger.error("An unexpected error occurred!", e)
        sys.exit(1)


def fetch_module_manifest(
    module_name: str, token: Optional[str], anonymousUserId: Optional[str] = None
) -> Dict[str, Any]:
    namespace, validator_name = module_name.split("/", 1)
    manifest_path = validator_manifest_endpoint.safe_substitute(
        namespace=namespace, validator_name=validator_name
    )
    manifest_url = f"{validator_hub_service}/{manifest_path}"
    return fetch(manifest_url, token, anonymousUserId)


def get_jwt_token(creds: Credentials) -> Optional[str]:
    token = creds.token

    # check for jwt expiration
    if token:
        try:
            JWT().decode(token, do_verify=False)
        except JWTDecodeError as e:
            # if the error message includes "Expired", then the token is expired
            if "Expired" in str(e):
                raise Exception(TOKEN_EXPIRED_MESSAGE)
            else:
                raise Exception(TOKEN_INVALID_MESSAGE)
    return token


def fetch_module(module_name: str) -> Manifest | None:
    creds = Credentials.from_rc_file(logger)
    token = get_jwt_token(creds)

    module_manifest_json = fetch_module_manifest(module_name, token, creds.id)
    return Manifest.from_dict(module_manifest_json)


# GET /validator-manifests/{namespace}/{validatorName}
def get_validator_manifest(module_name: str):
    try:
        module_manifest = fetch_module(module_name)
        if not module_manifest:
            logger.error(f"Failed to install hub://{module_name}")
            sys.exit(1)
        return module_manifest
    except HttpError:
        logger.error(f"Failed to install hub://{module_name}")
        sys.exit(1)
    except Exception as e:
        logger.error("An unexpected error occurred!", e)
        sys.exit(1)


# GET /auth
def get_auth():
    try:
        creds = Credentials.from_rc_file(logger)
        token = get_jwt_token(creds)
        auth_url = f"{validator_hub_service}/auth"
        response = fetch(auth_url, token, creds.id)
        if not response:
            raise AuthenticationError("Failed to authenticate!")
    except HttpError as http_error:
        logger.error(http_error)
        raise AuthenticationError("Failed to authenticate!")
    except Exception as e:
        logger.error("An unexpected error occurred!", e)
        raise AuthenticationError("Failed to authenticate!")


def post_validator_submit(package_name: str, content: str):
    try:
        creds = Credentials.from_rc_file(logger)
        token = get_jwt_token(creds)
        submission_url = f"{validator_hub_service}/validator/submit"

        headers = {
            "Authorization": f"Bearer {token}",
        }
        request_body = {"packageName": package_name, "content": content}
        req = requests.post(submission_url, data=request_body, headers=headers)

        body = req.json()
        if not req.ok:
            logger.error(req.status_code)
            logger.error(body.get("message"))
            http_error = HttpError()
            http_error.status = req.status_code
            http_error.message = body.get("message")
            raise http_error

        return body
    except HttpError as http_e:
        raise http_e
    except Exception as e:
        logger.error("An unexpected error occurred!", e)
        sys.exit(1)
