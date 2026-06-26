"""Safety guardrail checks for ticket analysis responses.

Two-layer defense:
  Layer 1: LLM system prompt forbids unsafe content (in prompts.py)
  Layer 2: This module scans and rewrites responses post-LLM (defense in depth)
"""

import re
from typing import Dict, Any


# ──────────────────────────────────────────────
# Unsafe Patterns
# ──────────────────────────────────────────────

# Patterns that request credentials from customers
CREDENTIAL_REQUEST_PATTERNS = [
    r'\b(?:share|provide|send|give|enter|type|input|submit|confirm|verify|tell)\b.*?\b(?:pin|otp|password|passcode|cvv|card\s*number|secret\s*code|security\s*code|mpin|verification\s*code)\b',
    r'\b(?:pin|otp|password|passcode|cvv|card\s*number|secret\s*code|security\s*code|mpin|verification\s*code)\b.*?\b(?:share|provide|send|give|enter|type|input|submit|confirm|verify|tell)\b',
    r'\bwhat\s+is\s+your\s+(?:pin|otp|password|passcode)\b',
    r'\bfor\s+verification.*?(?:pin|otp|password)\b',
    r'\bto\s+verify.*?(?:pin|otp|password)\b',
    r'\bplease\s+(?:share|provide|send|give|enter).*?(?:pin|otp|password|passcode|cvv)\b',
    # Bangla patterns
    r'\b(?:পিন|ওটিপি|পাসওয়ার্ড)\b.*?\b(?:দিন|জানান|পাঠান|শেয়ার)\b',
    r'\b(?:দিন|জানান|পাঠান|শেয়ার)\b.*?\b(?:পিন|ওটিপি|পাসওয়ার্ড)\b',
]

# Patterns that confirm refunds/reversals without authority
UNAUTHORIZED_REFUND_PATTERNS = [
    r'\bwe\s+will\s+refund\b',
    r'\bwe\s+will\s+reverse\b',
    r'\byour\s+(?:money|amount|balance|fund|taka)\s+(?:will\s+be|has\s+been|is\s+being)\s+(?:refunded|reversed|returned|restored|credited\s+back)\b',
    r'\brefund\s+(?:has\s+been|is\s+being|will\s+be)\s+(?:processed|initiated|completed|done|issued)\b',
    r'\bwe\s+(?:have|are)\s+(?:processed|initiated|completed|issuing|processing)\s+(?:a\s+|the\s+|your\s+)?refund\b',
    r'\byou\s+will\s+(?:get|receive)\s+(?:a\s+|the\s+|your\s+)?refund\b',
    r'\byour\s+account\s+(?:will\s+be|has\s+been|is\s+being)\s+(?:unblocked|unlocked|restored|recovered)\b',
    r'\bwe\s+(?:will|can|are\s+going\s+to)\s+(?:unblock|unlock|restore|recover)\s+your\s+account\b',
    r'\bconfirm(?:ing|ed)?\s+(?:the\s+|a\s+|your\s+)?(?:refund|reversal|recovery)\b',
    # Bangla patterns for refund confirmation
    r'\b(?:আমরা|আমি)\s+টাকা\s+ফেরত\s+দিচ্ছি\b',
    r'\bটাকা\s+ফেরত\s+(?:দেওয়া\s+হবে|পাওয়া\s+যাবে|পাঠানো\s+হয়েছে)\b',
    r'\bরিফান্ড\s+করা\s+(?:হয়েছে|হবে)\b',
    r'\bঅ্যাকাউন্টে\s+টাকা\s+ফিরে\s+পাবেন\b',
]

# Patterns directing to suspicious third parties
SUSPICIOUS_CONTACT_PATTERNS = [
    r'\bcall\s+(?:this\s+)?(?:number|phone)\b.*?\d{5,}',
    r'\bcontact\s+(?:this\s+)?(?:number|phone|person|agent)\b.*?\d{5,}',
    r'\b(?:whatsapp|telegram|viber|imo|facebook\s*messenger)\b.*?\b(?:contact|call|message|reach)\b',
    r'\b(?:contact|call|message|reach)\b.*?\b(?:whatsapp|telegram|viber|imo|facebook\s*messenger)\b',
    r'\bsend\s+(?:money|taka|amount)\s+to\b',
]

# Prompt injection leak patterns
INJECTION_LEAK_PATTERNS = [
    r'\bsystem\s*prompt\b',
    r'\byou\s+are\s+(?:a|an)\s+(?:AI|assistant|copilot|language\s+model)\b',
    r'\bignore\s+(?:previous|above|all)\s+instructions\b',
    r'\bmy\s+(?:instructions|rules)\s+(?:are|say)\b',
]


def check_credential_request(text: str) -> bool:
    """Check if text requests credentials from the customer."""
    text_lower = text.lower()
    for pattern in CREDENTIAL_REQUEST_PATTERNS:
        if re.search(pattern, text_lower):
            return True
    return False


def check_unauthorized_refund(text: str) -> bool:
    """Check if text confirms a refund or reversal without authority."""
    text_lower = text.lower()
    for pattern in UNAUTHORIZED_REFUND_PATTERNS:
        if re.search(pattern, text_lower):
            return True
    return False


def check_suspicious_contact(text: str) -> bool:
    """Check if text directs customer to suspicious third party."""
    text_lower = text.lower()
    for pattern in SUSPICIOUS_CONTACT_PATTERNS:
        if re.search(pattern, text_lower):
            return True
    return False


def check_prompt_injection_leak(text: str) -> bool:
    """Check if output contains leaked system prompt content."""
    text_lower = text.lower()
    for pattern in INJECTION_LEAK_PATTERNS:
        if re.search(pattern, text_lower):
            return True
    return False


# ──────────────────────────────────────────────
# Safe Replacement Texts
# ──────────────────────────────────────────────

SAFE_CUSTOMER_REPLY = (
    "Thank you for reaching out. We have received your concern and our team is "
    "reviewing it. For security, please never share your PIN, OTP, or password "
    "with anyone, including our support staff. If any resolution is applicable, "
    "it will be processed through official channels. You can reach our official "
    "customer care team for further assistance."
)

SAFE_NEXT_ACTION = (
    "Escalate to the relevant department for manual review. Verify the transaction "
    "details in the internal system before taking any action."
)


def sanitize_response(response: Dict[str, Any]) -> Dict[str, Any]:
    """Apply safety checks and sanitize the response.
    
    Returns the sanitized response dict with any unsafe content replaced.
    Also returns a list of violations found.
    """
    violations = []

    # Check customer_reply
    customer_reply = response.get("customer_reply", "")
    if check_credential_request(customer_reply):
        violations.append("credential_request_in_reply")
        response["customer_reply"] = SAFE_CUSTOMER_REPLY
        response["human_review_required"] = True

    if check_unauthorized_refund(customer_reply):
        violations.append("unauthorized_refund_in_reply")
        # Rewrite the reply to be safe
        response["customer_reply"] = (
            "Thank you for reaching out regarding your transaction. We have noted your "
            "concern and our team is looking into it. If any eligible amount is applicable, "
            "it will be processed through official channels. Please do not share your PIN, "
            "OTP, or password with anyone. For further assistance, please contact our "
            "official customer care team."
        )
        response["human_review_required"] = True

    if check_suspicious_contact(customer_reply):
        violations.append("suspicious_contact_in_reply")
        response["customer_reply"] = SAFE_CUSTOMER_REPLY
        response["human_review_required"] = True

    # Check recommended_next_action
    next_action = response.get("recommended_next_action", "")
    if check_unauthorized_refund(next_action):
        violations.append("unauthorized_refund_in_action")
        response["recommended_next_action"] = SAFE_NEXT_ACTION
        response["human_review_required"] = True

    # Check all text fields for prompt injection leaks
    text_fields = ["agent_summary", "recommended_next_action", "customer_reply"]
    for field in text_fields:
        value = response.get(field, "")
        if value and check_prompt_injection_leak(value):
            violations.append(f"injection_leak_in_{field}")
            if field == "customer_reply":
                response[field] = SAFE_CUSTOMER_REPLY
            elif field == "recommended_next_action":
                response[field] = SAFE_NEXT_ACTION
            else:
                response[field] = "Case requires manual review by support agent."
            response["human_review_required"] = True

    return response
