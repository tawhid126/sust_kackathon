"""Core ticket analysis engine using Gemini via Google GenAI SDK."""

import json
import logging
from typing import Dict, Any, Optional
from google import genai
from google.genai import types

from app.config import GEMINI_API_KEY, GEMINI_MODEL
from app.prompts import SYSTEM_PROMPT, build_user_prompt
from app.safety import sanitize_response
from app.schemas import (
    TicketRequest, TicketResponse,
    CaseType, Department, Severity, EvidenceVerdict,
)

logger = logging.getLogger(__name__)


# Valid enum values for validation
VALID_CASE_TYPES = {e.value for e in CaseType}
VALID_DEPARTMENTS = {e.value for e in Department}
VALID_SEVERITIES = {e.value for e in Severity}
VALID_VERDICTS = {e.value for e in EvidenceVerdict}

# Initialize GenAI client
_client: Optional[genai.Client] = None


def _get_client() -> genai.Client:
    """Lazy-initialize the Google GenAI client."""
    global _client
    if _client is None:
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client


def _build_fallback_response(ticket_id: str, complaint: str) -> Dict[str, Any]:
    """Build a safe fallback response when LLM fails or returns garbage."""
    return {
        "ticket_id": ticket_id,
        "relevant_transaction_id": None,
        "evidence_verdict": "insufficient_data",
        "case_type": "other",
        "severity": "medium",
        "department": "customer_support",
        "agent_summary": f"Automated analysis was unable to fully process this ticket. Manual review required. Customer complaint: {complaint[:200]}",
        "recommended_next_action": "Manually review the customer complaint and transaction history. Classify and route the case based on agent judgment.",
        "customer_reply": (
            "Thank you for reaching out. We have received your concern and our team "
            "is reviewing it. For security, please never share your PIN, OTP, or "
            "password with anyone, including our support staff. Our customer care "
            "team will get back to you shortly through official channels."
        ),
        "human_review_required": True,
        "confidence": 0.1,
        "reason_codes": ["llm_fallback", "manual_review_needed"],
    }


def _validate_and_fix_enums(response: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure all enum fields contain valid values, fix if possible."""
    # Fix case_type
    ct = response.get("case_type", "")
    if ct not in VALID_CASE_TYPES:
        # Try common normalizations
        ct_lower = ct.lower().strip().replace(" ", "_").replace("-", "_")
        if ct_lower in VALID_CASE_TYPES:
            response["case_type"] = ct_lower
        else:
            response["case_type"] = "other"

    # Fix department
    dept = response.get("department", "")
    if dept not in VALID_DEPARTMENTS:
        dept_lower = dept.lower().strip().replace(" ", "_").replace("-", "_")
        if dept_lower in VALID_DEPARTMENTS:
            response["department"] = dept_lower
        else:
            # Infer department from case_type
            response["department"] = _infer_department(response.get("case_type", "other"))

    # Fix severity
    sev = response.get("severity", "")
    if sev not in VALID_SEVERITIES:
        sev_lower = sev.lower().strip()
        if sev_lower in VALID_SEVERITIES:
            response["severity"] = sev_lower
        else:
            response["severity"] = "medium"

    # Fix evidence_verdict
    ev = response.get("evidence_verdict", "")
    if ev not in VALID_VERDICTS:
        ev_lower = ev.lower().strip().replace(" ", "_").replace("-", "_")
        if ev_lower in VALID_VERDICTS:
            response["evidence_verdict"] = ev_lower
        else:
            response["evidence_verdict"] = "insufficient_data"

    return response


def _infer_department(case_type: str) -> str:
    """Infer department from case type using the taxonomy mapping."""
    mapping = {
        "wrong_transfer": "dispute_resolution",
        "payment_failed": "payments_ops",
        "refund_request": "dispute_resolution",
        "duplicate_payment": "payments_ops",
        "merchant_settlement_delay": "merchant_operations",
        "agent_cash_in_issue": "agent_operations",
        "phishing_or_social_engineering": "fraud_risk",
        "other": "customer_support",
    }
    return mapping.get(case_type, "customer_support")


def _ensure_required_fields(response: Dict[str, Any], ticket_id: str) -> Dict[str, Any]:
    """Ensure all required fields are present with sensible defaults."""
    defaults = {
        "ticket_id": ticket_id,
        "relevant_transaction_id": None,
        "evidence_verdict": "insufficient_data",
        "case_type": "other",
        "severity": "medium",
        "department": "customer_support",
        "agent_summary": "Case requires manual review.",
        "recommended_next_action": "Review the case manually and take appropriate action.",
        "customer_reply": (
            "Thank you for reaching out. We have received your concern and our team "
            "is reviewing it. For security, please never share your PIN, OTP, or "
            "password with anyone. Our team will assist you through official channels."
        ),
        "human_review_required": True,
        "confidence": 0.5,
        "reason_codes": [],
    }

    for key, default_value in defaults.items():
        if key not in response or response[key] is None and key not in ("relevant_transaction_id",):
            response[key] = default_value

    # Always ensure ticket_id matches
    response["ticket_id"] = ticket_id

    # Ensure human_review_required is boolean
    if not isinstance(response.get("human_review_required"), bool):
        response["human_review_required"] = True

    # Ensure confidence is a float between 0 and 1
    try:
        conf = float(response.get("confidence", 0.5))
        response["confidence"] = max(0.0, min(1.0, conf))
    except (TypeError, ValueError):
        response["confidence"] = 0.5

    # Ensure reason_codes is a list
    if not isinstance(response.get("reason_codes"), list):
        response["reason_codes"] = []

    return response


def _parse_llm_response(raw_text: str) -> Optional[Dict[str, Any]]:
    """Parse JSON from LLM response, handling potential markdown wrapping."""
    text = raw_text.strip()

    # Remove markdown code block if present
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first and last lines (``` markers)
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON object in the text
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass
    return None


async def analyze_ticket(request: TicketRequest) -> TicketResponse:
    """Analyze a support ticket using Gemini via Google GenAI SDK.
    
    Process:
    1. Build prompt with complaint + transaction history
    2. Call Gemini API
    3. Parse and validate response
    4. Apply safety guardrails
    5. Return structured response
    """
    ticket_id = request.ticket_id
    complaint = request.complaint

    # Build transaction history list
    txn_history = []
    if request.transaction_history:
        txn_history = [t.model_dump() for t in request.transaction_history]

    # Build the user prompt
    user_prompt = build_user_prompt(
        ticket_id=ticket_id,
        complaint=complaint,
        transaction_history=txn_history,
        language=request.language,
        channel=request.channel,
        user_type=request.user_type,
        campaign_context=request.campaign_context,
    )

    # Call Gemini API
    try:
        if not GEMINI_API_KEY:
            logger.warning("No Gemini API key configured, using fallback response")
            response_dict = _build_fallback_response(ticket_id, complaint)
        else:
            response_dict = await _call_llm(user_prompt, ticket_id, complaint)
    except Exception as e:
        logger.error(f"LLM call failed for {ticket_id}: {e}")
        response_dict = _build_fallback_response(ticket_id, complaint)

    # Ensure all required fields present
    response_dict = _ensure_required_fields(response_dict, ticket_id)

    # Validate and fix enum values
    response_dict = _validate_and_fix_enums(response_dict)

    # Apply safety guardrails (Layer 2)
    response_dict = sanitize_response(response_dict)

    # Build and return Pydantic model
    return TicketResponse(**response_dict)


async def _call_llm(user_prompt: str, ticket_id: str, complaint: str) -> Dict[str, Any]:
    """Call Gemini API using Google GenAI SDK."""
    try:
        client = _get_client()

        # Call the generate_content API asynchronously
        response = await client.aio.models.generate_content(
            model=GEMINI_MODEL,
            contents=[user_prompt],
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.1,  # Low temperature for consistent, precise outputs
                response_mime_type="application/json",
            ),
        )

        raw_content = response.text
        logger.info(f"LLM response for {ticket_id}: {raw_content[:300]}...")

        parsed = _parse_llm_response(raw_content)
        if parsed is None:
            logger.error(f"Failed to parse LLM response for {ticket_id}")
            return _build_fallback_response(ticket_id, complaint)

        return parsed

    except Exception as e:
        logger.error(f"Gemini API error for {ticket_id}: {e}")
        return _build_fallback_response(ticket_id, complaint)

