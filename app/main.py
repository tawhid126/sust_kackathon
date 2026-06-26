"""QueueStorm Investigator — FastAPI Application

AI/API SupportOps Service for Digital Finance
SUST CSE Carnival 2026 — Codex Community Hackathon
"""

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.analyzer import analyze_ticket
from app.schemas import TicketRequest, TicketResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Track service start time
SERVICE_START_TIME = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("🚀 QueueStorm Investigator service starting...")
    logger.info(f"Service ready in {time.time() - SERVICE_START_TIME:.2f}s")
    yield
    logger.info("🛑 QueueStorm Investigator service shutting down...")


app = FastAPI(
    title="QueueStorm Investigator",
    description="AI/API SupportOps Copilot for Digital Finance — SUST CSE Carnival 2026",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ──────────────────────────────────────────────
# GET /health
# ──────────────────────────────────────────────

@app.get("/health")
async def health():
    """Health check endpoint. Returns {"status": "ok"} when service is ready."""
    return {"status": "ok"}


# ──────────────────────────────────────────────
# POST /analyze-ticket
# ──────────────────────────────────────────────

@app.post("/analyze-ticket", response_model=TicketResponse)
async def analyze_ticket_endpoint(request: Request):
    """Analyze a customer support ticket.
    
    Accepts a JSON body with complaint text and optional transaction history.
    Returns a structured analysis with classification, routing, evidence
    reasoning, and a safe customer reply.
    """
    # Parse request body
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            status_code=400,
            content={"error": "Invalid JSON in request body."},
        )

    # Validate required fields
    if not isinstance(body, dict):
        return JSONResponse(
            status_code=400,
            content={"error": "Request body must be a JSON object."},
        )

    if "ticket_id" not in body:
        return JSONResponse(
            status_code=400,
            content={"error": "Missing required field: ticket_id"},
        )

    if "complaint" not in body:
        return JSONResponse(
            status_code=400,
            content={"error": "Missing required field: complaint"},
        )

    # Check for empty complaint (422)
    complaint = body.get("complaint", "")
    if isinstance(complaint, str) and complaint.strip() == "":
        return JSONResponse(
            status_code=422,
            content={"error": "Complaint text cannot be empty."},
        )

    # Parse into Pydantic model
    try:
        ticket_request = TicketRequest(**body)
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={"error": f"Invalid request format: {str(e)}"},
        )

    # Analyze the ticket
    try:
        logger.info(f"📩 Analyzing ticket: {ticket_request.ticket_id}")
        start = time.time()

        result = await analyze_ticket(ticket_request)

        elapsed = time.time() - start
        logger.info(f"✅ Ticket {ticket_request.ticket_id} analyzed in {elapsed:.2f}s")

        return result

    except Exception as e:
        logger.error(f"❌ Error analyzing ticket {ticket_request.ticket_id}: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error during ticket analysis."},
        )


# ──────────────────────────────────────────────
# Global exception handler
# ──────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all exception handler to prevent crashes and secret leaks."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "An unexpected error occurred. Please try again."},
    )


if __name__ == "__main__":
    import uvicorn
    from app.config import HOST, PORT
    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=True)
