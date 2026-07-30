"""HTTP client for mireva_serve — pure requests only."""

from __future__ import annotations

from typing import Any

import httpx

from mireva_sdk.exceptions import (
    MirevaAuthenticationError,
    MirevaConnectionError,
    MirevaModelError,
    MirevaTimeoutError,
    MirevaValidationError,
)
from mireva_sdk.models import MirevaClaimInput, MirevaPrediction


class MirevaClient:
    """Calls authenticated MIREVA endpoints over HTTP."""

    def __init__(
        self,
        base_url: str,
        *,
        api_key: str | None = None,
        model_version: str = "mireva-origin",
        timeout_s: float = 60.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model_version = model_version
        self.timeout_s = timeout_s
        self._headers: dict[str, str] = {}
        if api_key:
            self._headers["Authorization"] = f"Bearer {api_key}"

    def predict(
        self,
        claim: MirevaClaimInput | dict[str, Any],
        *,
        model_version: str | None = None,
    ) -> MirevaPrediction:
        payload = claim.model_dump(mode="json") if isinstance(claim, MirevaClaimInput) else dict(claim)
        version = model_version or self.model_version
        if not version:
            raise MirevaValidationError("model_version is required")
        url = f"{self.base_url}/predict"
        params = {"model_version": version}
        try:
            with httpx.Client(timeout=self.timeout_s) as client:
                r = client.post(url, json=payload, params=params, headers=self._headers)
        except httpx.ConnectError as e:
            raise MirevaConnectionError(str(e)) from e
        except httpx.TimeoutException as e:
            raise MirevaTimeoutError(str(e)) from e

        return self._parse_prediction(r)

    def health_check(self) -> dict[str, object]:
        url = f"{self.base_url}/health"
        try:
            with httpx.Client(timeout=self.timeout_s) as client:
                r = client.get(url, headers=self._headers)
        except httpx.ConnectError as e:
            raise MirevaConnectionError(str(e)) from e
        except httpx.TimeoutException as e:
            raise MirevaTimeoutError(str(e)) from e

        self._raise_for_status(r)
        return dict(r.json())

    def list_models(self) -> dict[str, object]:
        url = f"{self.base_url}/model/versions"
        try:
            with httpx.Client(timeout=self.timeout_s) as client:
                r = client.get(url, headers=self._headers)
        except httpx.ConnectError as e:
            raise MirevaConnectionError(str(e)) from e
        except httpx.TimeoutException as e:
            raise MirevaTimeoutError(str(e)) from e

        self._raise_for_status(r)
        return dict(r.json())

    def _parse_prediction(self, r: httpx.Response) -> MirevaPrediction:
        self._raise_for_status(r)
        return MirevaPrediction.model_validate(r.json())

    def _raise_for_status(self, r: httpx.Response) -> None:
        if r.status_code == 401:
            raise MirevaAuthenticationError("Invalid or missing API key")
        if r.status_code == 404:
            raise MirevaModelError(r.text or "Model version not found")
        if r.status_code == 422:
            try:
                detail = r.json()
            except Exception:
                detail = r.text
            raise MirevaValidationError("Validation failed", detail=detail)
        if r.status_code >= 500:
            raise MirevaModelError(r.text or f"Server error {r.status_code}")
        r.raise_for_status()
