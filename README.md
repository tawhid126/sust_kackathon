# 🔍 QueueStorm Investigator

**AI/API SupportOps Copilot for Digital Finance**  
*SUST CSE Carnival 2026 — bKash presents Codex Community Hackathon*

An intelligent support ticket analysis API that classifies, routes, and explains customer complaints for a digital finance platform. Built with evidence-based reasoning and multi-layer safety guardrails.

---

## 🏗 Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Framework** | FastAPI (Python 3.11) | Async API framework with auto-validation |
| **LLM** | Gemini 2.5 Flash | Ticket analysis & evidence reasoning |
| **Validation** | Pydantic v2 | Request/response schema enforcement |
| **HTTP Client** | google-genai | Async LLM API calls |
| **Deployment** | Render / Docker | Free-tier cloud hosting |

---

## 🚀 Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/YOUR_USERNAME/queuestorm-investigator.git
cd queuestorm-investigator
python -m venv venv
source venv/bin/activate    # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env and add your Gemini API key (Google AI Studio)
```

### 3. Run the Service

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 4. Test

```bash
# Health check
curl http://localhost:8000/health

# Analyze a ticket
curl -X POST http://localhost:8000/analyze-ticket \
  -H "Content-Type: application/json" \
  -d '{
    "ticket_id": "TKT-001",
    "complaint": "I sent 5000 taka to a wrong number",
    "transaction_history": [
      {
        "transaction_id": "TXN-9101",
        "timestamp": "2026-04-14T14:08:22Z",
        "type": "transfer",
        "amount": 5000,
        "counterparty": "+8801719876543",
        "status": "completed"
      }
    ]
  }'
```

---

## 🐳 Docker

```bash
# Build
docker build -t queuestorm-investigator .

# Run
docker run -p 8000:8000 -e GEMINI_API_KEY=your_key_here queuestorm-investigator
```

---

## 📡 API Endpoints

### `GET /health`
Returns `{"status": "ok"}` when the service is ready.

### `POST /analyze-ticket`
Accepts a support ticket with complaint text and transaction history. Returns structured analysis.

**Request:**
```json
{
  "ticket_id": "TKT-001",
  "complaint": "Customer complaint text...",
  "language": "en",
  "channel": "in_app_chat",
  "user_type": "customer",
  "transaction_history": [...]
}
```

**Response:**
```json
{
  "ticket_id": "TKT-001",
  "relevant_transaction_id": "TXN-9101",
  "evidence_verdict": "consistent",
  "case_type": "wrong_transfer",
  "severity": "high",
  "department": "dispute_resolution",
  "agent_summary": "...",
  "recommended_next_action": "...",
  "customer_reply": "...",
  "human_review_required": true,
  "confidence": 0.9,
  "reason_codes": ["wrong_transfer", "transaction_match"]
}
```

---

## 🧠 AI Approach

### Evidence-Based Investigation
The system doesn't just classify complaints — it **investigates** them:

1. **Read** the customer complaint (supports English, Bangla, Banglish)
2. **Examine** the transaction history (2-5 recent transactions)
3. **Cross-reference** complaint claims against transaction data
4. **Determine** evidence verdict: `consistent`, `inconsistent`, or `insufficient_data`
5. **Classify** case type, severity, and route to appropriate department
6. **Draft** a safe, professional customer reply

### Model Selection
- **Gemini 2.5 Flash**: Chosen for its incredibly fast inference, strong reasoning capabilities, and large context window. Uses structured JSON output mode for reliable schema compliance. Temperature set to 0.1 for consistent, deterministic outputs.

### Why Gemini Flash?
- Native structured output (JSON) support via Google GenAI SDK
- Lightning fast response times
- Generous free tier via Google AI Studio
- Excellent instruction following and reasoning for complex scenarios
- Multilingual support (English, Bangla, Banglish)

---

## 🛡 Safety Logic

### Two-Layer Defense System

**Layer 1 — LLM System Prompt:**
- Explicitly instructs the model to never request PIN, OTP, password, or card numbers
- Prohibits confirming refunds, reversals, or account actions
- Directs customers only to official channels
- Includes anti-prompt-injection instructions

**Layer 2 — Post-Processing Safety Scan (`safety.py`):**
- Regex-based scanning of `customer_reply` and `recommended_next_action`
- Detects credential requests, unauthorized refund confirmations, suspicious contact instructions
- Detects prompt injection leakage in all output fields
- **Rewrites** any unsafe content with safe alternatives
- Automatically sets `human_review_required = true` for any safety violation

### Prompt Injection Defense
- Customer complaint text is delimited and marked as "untrusted input"
- System prompt includes explicit anti-injection instructions
- Post-processing scans for leaked system prompt content

---

## 📊 MODELS Section

| Model | Provider | Where it runs | Why chosen |
|---|---|---|---|
| `gemini-2.5-flash` | Google (AI Studio) | Google Cloud API | Fast inference, structured JSON output, generous free tier, strong reasoning |

**No GPU required.** The service makes API calls to Google's GenAI endpoints. A 2 vCPU / 4 GB RAM machine is sufficient.

---

## ⚠️ Known Limitations

1. **LLM Dependency**: Service quality depends on Google Gemini API availability and response quality
2. **No Real Data Integration**: All transaction data is synthetic; no real payment system integration
3. **Single-Ticket Processing**: Handles one ticket at a time (no batch processing)
4. **Language Coverage**: Primarily optimized for English and common Bangla/Banglish phrases
5. **Fallback Mode**: If the LLM fails, returns a safe fallback response requiring human review

---

## 📂 Project Structure

```
├── app/
│   ├── main.py          # FastAPI endpoints (/health, /analyze-ticket)
│   ├── analyzer.py      # Core analysis engine + LLM integration
│   ├── schemas.py       # Pydantic request/response models
│   ├── prompts.py       # LLM system & user prompt templates
│   ├── safety.py        # Post-processing safety guardrails
│   └── config.py        # Environment configuration
├── tests/
│   └── test_sample_cases.py  # Automated test suite
├── sample_cases.json    # 10 sample test cases
├── requirements.txt     # Python dependencies
├── Dockerfile           # Docker build config
├── render.yaml          # Render deployment config
├── .env.example         # Environment variable template
├── README.md            # This file
└── RUNBOOK.md           # Step-by-step setup guide
```

---

## 📜 License

Built for SUST CSE Carnival 2026 — Codex Community Hackathon.
