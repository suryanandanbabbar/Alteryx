"""HTTP client for the Azure License API.

Uses ``urllib.request`` from the standard library so no additional HTTP
dependency is required.  The client returns the raw JSON dict alongside
the parsed Pydantic model so that signature verification operates on the
exact byte representation the server signed.
"""

from __future__ import annotations

import json
import logging
import secrets
import uuid
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .config import LicenseConfig
from .errors import LicenseInvalidError, LicenseNetworkError
from .models import LicenseValidationRequest, LicenseValidationResponse

logger = logging.getLogger("awa.licensing.client")

# Stable instance identifier — generated once per process lifetime.
# Not based on personal data or machine fingerprints.
_INSTANCE_ID: str | None = None


def get_instance_id() -> str:
    """Return (or lazily create) a process-stable client instance identifier."""
    global _INSTANCE_ID
    if _INSTANCE_ID is None:
        _INSTANCE_ID = str(uuid.uuid4())
    return _INSTANCE_ID


_get_instance_id = get_instance_id


def validate_license(
    config: LicenseConfig,
    request_id: str | None = None,
    client_instance_id: str | None = None,
) -> tuple[dict[str, Any], LicenseValidationResponse, str, str]:
    """Call the Azure License API to validate the current license.

    Args:
        config: License configuration.
        request_id: Optional explicit cryptographically random nonce.
            If None, a fresh 32-byte secure token is generated.
        client_instance_id: Optional explicit client instance ID.
            If None, process-stable instance ID is used.

    Returns:
        A 4-tuple of ``(raw_response_dict, parsed_response, sent_request_id, sent_client_instance_id)``.
        The raw dict is used for signature verification.
        The sent_request_id is used for nonce binding verification.
        The sent_client_instance_id is used for client instance binding verification.

    Raises:
        LicenseNetworkError: If the API is unreachable or returns an HTTP error.
        LicenseInvalidError: If the response body is malformed.
    """
    url = f"{config.api_url.rstrip('/')}/v1/license/validate"
    nonce = request_id or secrets.token_urlsafe(32)
    inst_id = client_instance_id or _get_instance_id()

    request_model = LicenseValidationRequest(
        license_id=config.license_id,
        product=config.product,
        client_instance_id=inst_id,
        environment=config.environment,
        request_id=nonce,
    )

    req_body = request_model.model_dump_json().encode("utf-8")

    try:
        req = Request(
            url,
            data=req_body,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "AWA-LicenseClient/1.0",
            },
            method="POST",
        )

        logger.debug("License validation request → %s", url)

        with urlopen(req, timeout=15) as resp:
            resp_body = resp.read().decode("utf-8")

    except HTTPError as exc:
        status_code = exc.code
        try:
            error_body = exc.read().decode("utf-8", errors="replace")[:500]
        except Exception:
            error_body = ""
        logger.warning(
            "License API returned HTTP %d: %s", status_code, error_body[:200]
        )
        raise LicenseNetworkError(
            f"License API returned HTTP {status_code}."
        ) from exc

    except URLError as exc:
        logger.warning("License API unreachable: %s", exc.reason)
        raise LicenseNetworkError(
            f"License API unreachable: {exc.reason}"
        ) from exc

    except Exception as exc:
        logger.warning(
            "License API request failed: %s — %s",
            type(exc).__name__,
            str(exc)[:200],
        )
        raise LicenseNetworkError(
            f"License API request failed: {type(exc).__name__}"
        ) from exc

    # Parse raw JSON
    try:
        raw_dict: dict[str, Any] = json.loads(resp_body)
    except (json.JSONDecodeError, ValueError) as exc:
        raise LicenseInvalidError(
            "License API returned a non-JSON response."
        ) from exc

    # Validate required fields via Pydantic
    try:
        response = LicenseValidationResponse(**raw_dict)
    except Exception as exc:
        raise LicenseInvalidError(
            f"License API response is missing required fields: {type(exc).__name__}"
        ) from exc

    return raw_dict, response, nonce, inst_id
