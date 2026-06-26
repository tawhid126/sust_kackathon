# RUNBOOK — QueueStorm Investigator

Step-by-step guide to bring up the service locally. A stranger should be able to follow these commands without guessing.

---

## Prerequisites

- Python 3.11+ installed
- A DeepSeek API key (get one at https://platform.deepseek.com)
- `pip` and `venv` available

---

## Option A: Run Locally (Recommended)

```bash
# 1. Clone the repository
git clone https://github.com/YOUR_USERNAME/queuestorm-investigator.git
cd queuestorm-investigator

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate    # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
cp .env.example .env
# Edit .env and replace 'your_deepseek_api_key_here' with your actual API key:
#   DEEPSEEK_API_KEY=sk-your-actual-key-here

# 5. Start the service
uvicorn app.main:app --host 0.0.0.0 --port 8000

# 6. Verify health (in another terminal)
curl http://localhost:8000/health
# Expected: {"status":"ok"}

# 7. Test with a sample case
curl -X POST http://localhost:8000/analyze-ticket \
  -H "Content-Type: application/json" \
  -d '{
    "ticket_id": "TKT-001",
    "complaint": "I sent 5000 taka to a wrong number around 2pm today.",
    "language": "en",
    "channel": "in_app_chat",
    "user_type": "customer",
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

## Option B: Run with Docker

```bash
# 1. Clone the repository
git clone https://github.com/YOUR_USERNAME/queuestorm-investigator.git
cd queuestorm-investigator

# 2. Build the Docker image
docker build -t queuestorm-investigator .

# 3. Run the container
docker run -p 8000:8000 \
  -e DEEPSEEK_API_KEY=sk-your-actual-key-here \
  queuestorm-investigator

# 4. Verify health
curl http://localhost:8000/health
# Expected: {"status":"ok"}
```

---

## Run Tests

```bash
# Make sure the service is running on localhost:8000 first
pip install pytest
python -m pytest tests/ -v
```

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `DEEPSEEK_API_KEY` | Yes | — | Your DeepSeek API key |
| `DEEPSEEK_BASE_URL` | No | `https://api.deepseek.com` | DeepSeek API base URL |
| `DEEPSEEK_MODEL` | No | `deepseek-chat` | Model name to use |
| `HOST` | No | `0.0.0.0` | Server bind host |
| `PORT` | No | `8000` | Server bind port |
| `LLM_TIMEOUT` | No | `25` | LLM request timeout (seconds) |

---

## Troubleshooting

| Issue | Fix |
|---|---|
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` in your venv |
| `DEEPSEEK_API_KEY not set` | Create `.env` from `.env.example` and add your key |
| Timeout on `/analyze-ticket` | Check your internet connection and DeepSeek API status |
| `Connection refused` on test | Make sure the service is running before running tests |
