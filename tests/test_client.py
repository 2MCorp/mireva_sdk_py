"""SDK unit tests — mocked HTTP only, no mireva_core."""

from __future__ import annotations

from datetime import date

import httpx
import pytest

from mireva_sdk import (
    MirevaAuthenticationError,
    MirevaClient,
    MirevaClaimInput,
    MirevaModelError,
    MirevaValidationError,
)
from mireva_sdk.models import PatientBlock, VisitBlock


def _claim() -> MirevaClaimInput:
    return MirevaClaimInput(
        claim_id="C1",
        visit=VisitBlock(visit_start_date=date(2024, 1, 1)),
        patient=PatientBlock(patient_id="P1", age=40, gender_concept_id=8507),
        claimed_amount=100.0,
    )


def _prediction_json() -> dict:
    return {
        "claim_id": "C1",
        "final_decision": "APPROVE",
        "fraud_score": 0.1,
        "risk_level": "LOW",
        "confidence": 0.9,
        "hard_rules": {"decision": "PASS", "rules_fired": []},
        "soft_rules": {"score": 0.0, "rules_fired": []},
        "model_version": "mireva-origin",
        "processed_at": "2024-01-01T00:00:00Z",
        "probabilities": [0.9, 0.05, 0.05],
        "skipped_model": False,
    }


def test_predict_sends_auth_and_model_version(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["auth"] = request.headers.get("Authorization")
        return httpx.Response(200, json=_prediction_json())

    transport = httpx.MockTransport(handler)

    class PatchedClient(httpx.Client):
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = transport
            super().__init__(*args, **kwargs)

    monkeypatch.setattr("mireva_sdk.client.httpx.Client", PatchedClient)

    client = MirevaClient(
        "http://example.test",
        api_key="mv_live_test.secret",
        model_version="mireva-concord",
    )
    pred = client.predict(_claim())
    assert pred.final_decision == "APPROVE"
    assert "model_version=mireva-concord" in captured["url"]
    assert captured["auth"] == "Bearer mv_live_test.secret"


def test_predict_401(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"detail": "Unauthorized"})

    transport = httpx.MockTransport(handler)

    class PatchedClient(httpx.Client):
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = transport
            super().__init__(*args, **kwargs)

    monkeypatch.setattr("mireva_sdk.client.httpx.Client", PatchedClient)
    client = MirevaClient("http://example.test", api_key="bad")
    with pytest.raises(MirevaAuthenticationError):
        client.predict(_claim())


def test_predict_404_model(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="unknown model")

    transport = httpx.MockTransport(handler)

    class PatchedClient(httpx.Client):
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = transport
            super().__init__(*args, **kwargs)

    monkeypatch.setattr("mireva_sdk.client.httpx.Client", PatchedClient)
    client = MirevaClient("http://example.test", api_key="k", model_version="nope")
    with pytest.raises(MirevaModelError):
        client.predict(_claim())


def test_predict_422(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(422, json={"detail": "bad"})

    transport = httpx.MockTransport(handler)

    class PatchedClient(httpx.Client):
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = transport
            super().__init__(*args, **kwargs)

    monkeypatch.setattr("mireva_sdk.client.httpx.Client", PatchedClient)
    client = MirevaClient("http://example.test", api_key="k")
    with pytest.raises(MirevaValidationError):
        client.predict({"claim_id": "x"})


def test_claim_model_carries_context_fields():
    from mireva_sdk.models import MirevaClaimInput

    claim = MirevaClaimInput.model_validate(
        {
            "claim_id": "c1",
            "visit": {"visit_start_date": "2025-03-10"},
            "patient": {"patient_id": "p", "age": 4, "gender_concept_id": 8532, "allergy_concept_ids": [7], "poverty": True},
            "drugs": [{"concept_id": 1, "unit_price": 12.0, "tariff_unit_price": 10.0}],
            "procedures": [{"concept_id": 2, "quantity": 2, "unit_price": 5.0}],
            "claimed_amount": 10,
            "facility": {"level": "D", "care_type": "O"},
            "provider_license_valid": False,
        }
    )
    dumped = claim.model_dump(mode="json")
    assert dumped["patient"]["allergy_concept_ids"] == [7]
    assert dumped["drugs"][0]["tariff_unit_price"] == 10.0
    assert dumped["procedures"][0]["quantity"] == 2
    assert dumped["facility"] == {"level": "D", "care_type": "O"}
    assert dumped["provider_license_valid"] is False
