"""Common response builders for Lambda handlers."""

import json
from typing import Any


def build_lambda_response(status_code: int, payload: dict[str, Any]) -> dict[str, Any]:
    """Build the API Gateway-style envelope returned by ``lambda_handler``.

    The body is always a JSON string so the handler can be used behind API
    Gateway or invoked directly with the same response contract.
    """
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(payload, ensure_ascii=True)
    }
