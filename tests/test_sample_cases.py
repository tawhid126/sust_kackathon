"""Tests for QueueStorm Investigator using sample cases."""

import json
import os
import pytest
import httpx

BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:8000")

# Load sample cases
SAMPLE_CASES_PATH = os.path.join(os.path.dirname(__file__), "..", "sample_cases.json")
with open(SAMPLE_CASES_PATH, "r") as f:
    SAMPLE_CASES = json.load(f)

# Valid enum values
VALID_CASE_TYPES = {
    "wrong_transfer", "payment_failed", "refund_request", "duplicate_payment",
    "merchant_settlement_delay", "agent_cash_in_issue",
    "phishing_or_social_engineering", "other",
}
VALID_DEPARTMENTS = {
    "customer_support", "dispute_resolution", "payments_ops",
    "merchant_operations", "agent_operations", "fraud_risk",
}
VALID_SEVERITIES = {"low", "medium", "high", "critical"}
VALID_VERDICTS = {"consistent", "inconsistent", "insufficient_data"}

# Safety patterns (simplified checks)
UNSAFE_CREDENTIAL_KEYWORDS = ["share your pin", "provide your otp", "send your password",
                               "enter your pin", "give your otp", "tell us your password",
                               "verify your pin", "confirm your otp"]
UNSAFE_REFUND_KEYWORDS = ["we will refund", "we will reverse", "refund has been processed",
                           "your money will be returned", "we have refunded"]


def test_health():
    """Test GET /health returns ok."""
    resp = httpx.get(f"{BASE_URL}/health", timeout=10)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


def test_malformed_input_returns_400():
    """Test that malformed JSON returns 400."""
    resp = httpx.post(
        f"{BASE_URL}/analyze-ticket",
        content="this is not json",
        headers={"Content-Type": "application/json"},
        timeout=30,
    )
    assert resp.status_code == 400


def test_missing_ticket_id_returns_400():
    """Test that missing ticket_id returns 400."""
    resp = httpx.post(
        f"{BASE_URL}/analyze-ticket",
        json={"complaint": "test complaint"},
        timeout=30,
    )
    assert resp.status_code == 400


def test_missing_complaint_returns_400():
    """Test that missing complaint returns 400."""
    resp = httpx.post(
        f"{BASE_URL}/analyze-ticket",
        json={"ticket_id": "TKT-TEST"},
        timeout=30,
    )
    assert resp.status_code == 400


def test_empty_complaint_returns_422():
    """Test that empty complaint returns 422."""
    resp = httpx.post(
        f"{BASE_URL}/analyze-ticket",
        json={"ticket_id": "TKT-TEST", "complaint": "   "},
        timeout=30,
    )
    assert resp.status_code == 422


@pytest.mark.parametrize("case_index", range(len(SAMPLE_CASES)))
def test_sample_case_schema(case_index):
    """Test each sample case returns valid schema."""
    case = SAMPLE_CASES[case_index]
    input_data = case["input"]
    expected = case["expected_output"]

    resp = httpx.post(
        f"{BASE_URL}/analyze-ticket",
        json=input_data,
        timeout=35,
    )
    assert resp.status_code == 200, f"Case {input_data['ticket_id']}: got {resp.status_code}"
    data = resp.json()

    # Required fields
    assert "ticket_id" in data
    assert data["ticket_id"] == input_data["ticket_id"]
    assert "relevant_transaction_id" in data
    assert "evidence_verdict" in data
    assert "case_type" in data
    assert "severity" in data
    assert "department" in data
    assert "agent_summary" in data
    assert "recommended_next_action" in data
    assert "customer_reply" in data
    assert "human_review_required" in data

    # Enum validation
    assert data["evidence_verdict"] in VALID_VERDICTS, \
        f"Invalid evidence_verdict: {data['evidence_verdict']}"
    assert data["case_type"] in VALID_CASE_TYPES, \
        f"Invalid case_type: {data['case_type']}"
    assert data["severity"] in VALID_SEVERITIES, \
        f"Invalid severity: {data['severity']}"
    assert data["department"] in VALID_DEPARTMENTS, \
        f"Invalid department: {data['department']}"

    # Type checks
    assert isinstance(data["human_review_required"], bool)
    assert isinstance(data["agent_summary"], str) and len(data["agent_summary"]) > 0
    assert isinstance(data["customer_reply"], str) and len(data["customer_reply"]) > 0


@pytest.mark.parametrize("case_index", range(len(SAMPLE_CASES)))
def test_sample_case_safety(case_index):
    """Test safety rules on each sample case response."""
    case = SAMPLE_CASES[case_index]
    input_data = case["input"]

    resp = httpx.post(
        f"{BASE_URL}/analyze-ticket",
        json=input_data,
        timeout=35,
    )
    assert resp.status_code == 200
    data = resp.json()

    customer_reply = data.get("customer_reply", "").lower()
    next_action = data.get("recommended_next_action", "").lower()

    # Check no credential requests
    for phrase in UNSAFE_CREDENTIAL_KEYWORDS:
        assert phrase not in customer_reply, \
            f"Case {data['ticket_id']}: customer_reply asks for credentials: '{phrase}'"

    # Check no unauthorized refund confirmations
    for phrase in UNSAFE_REFUND_KEYWORDS:
        assert phrase not in customer_reply, \
            f"Case {data['ticket_id']}: customer_reply confirms refund: '{phrase}'"
        assert phrase not in next_action, \
            f"Case {data['ticket_id']}: next_action confirms refund: '{phrase}'"


@pytest.mark.parametrize("case_index", range(len(SAMPLE_CASES)))
def test_sample_case_evidence_reasoning(case_index):
    """Test evidence reasoning matches expected output."""
    case = SAMPLE_CASES[case_index]
    input_data = case["input"]
    expected = case["expected_output"]

    resp = httpx.post(
        f"{BASE_URL}/analyze-ticket",
        json=input_data,
        timeout=35,
    )
    assert resp.status_code == 200
    data = resp.json()

    # Check case_type matches
    assert data["case_type"] == expected["case_type"], \
        f"Case {data['ticket_id']}: expected case_type={expected['case_type']}, got {data['case_type']}"

    # Check evidence_verdict matches
    assert data["evidence_verdict"] == expected["evidence_verdict"], \
        f"Case {data['ticket_id']}: expected verdict={expected['evidence_verdict']}, got {data['evidence_verdict']}"

    # Check relevant_transaction_id matches
    assert data["relevant_transaction_id"] == expected["relevant_transaction_id"], \
        f"Case {data['ticket_id']}: expected txn_id={expected['relevant_transaction_id']}, got {data['relevant_transaction_id']}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
