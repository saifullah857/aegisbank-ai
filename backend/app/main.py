"""AegisBank AI — API core: auth, customers, transaction scoring."""
from datetime import datetime
from typing import Literal

from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import time
from collections import defaultdict, deque

from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import get_settings, validate_production_secrets
from app.api.assistant import router as assistant_router
from app.api.banking import router as banking_router
from app.api.cases import router as cases_router
from app.api.extras import router as extras_router
from app.api.insights import router as insights_router
from app.core.metrics import metrics
from app.core.deps import INVESTIGATE, current_user, require_roles
from app.core.security import create_access_token, hash_password, verify_password
from app.db.base import Customer, Transaction, User
from app.db.session import get_db
from app.services import payments
from app.services.ledger import LedgerError

settings = get_settings()
validate_production_secrets(settings)
app = FastAPI(title=settings.APP_NAME, description=settings.TAGLINE, version="0.1.0", docs_url="/api/docs")
app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"])
P = settings.API_V1_PREFIX
app.include_router(cases_router, prefix=P)
app.include_router(insights_router, prefix=P)
app.include_router(extras_router, prefix=P)
app.include_router(banking_router, prefix=P)
app.include_router(assistant_router, prefix=P)
_DUMMY_HASH = hash_password("timing-equalization-dummy")  # equalizes login timing for unknown usernames


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


class TransactionCreate(BaseModel):
    customer_id: int = Field(gt=0)
    amount: float = Field(gt=0, le=100_000_000)
    transaction_type: Literal["TRANSFER", "WITHDRAWAL", "DEPOSIT", "CARD_PAYMENT", "BILL_PAYMENT", "ONLINE_PURCHASE"]
    merchant: str = Field(min_length=1, max_length=255)
    merchant_category: str = Field(min_length=1, max_length=64)
    location: str = Field(min_length=1, max_length=64)
    device_id: str = Field(min_length=1, max_length=64)
    beneficiary_account: str | None = Field(default=None, max_length=64)
    occurred_at: datetime | None = None


def txn_out(t: Transaction) -> dict:
    return dict(id=t.id, transaction_ref=t.transaction_ref, customer_id=t.customer_id, amount=float(t.amount), currency=t.currency,
                transaction_type=t.transaction_type, status=t.status, merchant=t.merchant, merchant_category=t.merchant_category,
                location=t.location, device_id=t.device_id, beneficiary_account=t.beneficiary_account,
                occurred_at=t.occurred_at, risk_score=t.risk_score, rule_score=t.rule_risk_score, ml_anomaly_score=t.ml_anomaly_score, risk_level=t.risk_level, risk_indicators=t.risk_indicators,
                account_id=t.account_id, failure_reason=t.failure_reason)


_api_hits: dict[str, deque] = defaultdict(deque)


def _api_rate_limited(key: str) -> bool:
    """Sliding one-minute window per client IP across the whole API (in-process; use Redis to share across replicas)."""
    now, q = time.time(), _api_hits[key]
    while q and now - q[0] > 60:
        q.popleft()
    if len(q) >= settings.API_RATE_LIMIT_PER_MINUTE:
        return True
    q.append(now)
    return False


@app.middleware("http")
async def security_and_metrics(request: Request, call_next):
    start = time.perf_counter()
    if request.url.path.startswith(P) and _api_rate_limited(request.client.host if request.client else "unknown"):
        return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded. Try again shortly.", "code": "rate_limited"}, headers={"Retry-After": "60"})
    response = await call_next(request)
    metrics.record((time.perf_counter() - start) * 1000, response.status_code)
    response.headers["X-Content-Type-Options"] = "nosniff"
    if not settings.ALLOW_IFRAME:
        response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    if request.url.path.startswith(P):
        response.headers["Cache-Control"] = "no-store"
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
    if settings.ENVIRONMENT.lower() == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


@app.exception_handler(OperationalError)
async def database_unavailable(request: Request, exc: OperationalError):
    return JSONResponse(status_code=503, content={"detail": "Database temporarily unavailable. Please try again shortly.", "code": "database_unavailable"})


_login_attempts: dict[str, deque] = defaultdict(deque)


def _rate_limited(key: str) -> bool:
    """Sliding one-minute window per client IP (in-process; fine for a single worker, use Redis to share across replicas)."""
    now, q = time.time(), _login_attempts[key]
    while q and now - q[0] > 60:
        q.popleft()
    if len(q) >= settings.LOGIN_RATE_LIMIT_PER_MINUTE:
        return True
    q.append(now)
    return False


@app.get(f"{P}/health/ready")
def readiness(db: Session = Depends(get_db)):
    """Readiness (can this instance serve?) as opposed to /health (is the process up?)."""
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        return JSONResponse(status_code=503, content={"status": "unavailable", "reason": "database unreachable"})
    return {"status": "ready"}


@app.get(f"{P}/health")
def health():
    return {"status": "ok", "app": settings.APP_NAME, "llm_provider": settings.LLM_PROVIDER, "llm_configured": settings.llm_available}


@app.post(f"{P}/auth/login")
def login(body: LoginRequest, request: Request, db: Session = Depends(get_db)):
    if _rate_limited(request.client.host if request.client else "unknown"):
        raise HTTPException(429, "Too many login attempts. Try again in a minute.", headers={"Retry-After": "60"})
    user = db.query(User).filter(User.username == body.username).first()
    ok = verify_password(body.password, user.hashed_password if user else _DUMMY_HASH)
    if not user or not ok or not user.is_active:
        raise HTTPException(401, "Incorrect username or password", headers={"WWW-Authenticate": "Bearer"})
    return {"access_token": create_access_token(user.username, user.role), "token_type": "bearer", "role": user.role}


@app.get(f"{P}/customers")
def list_customers(page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100), db: Session = Depends(get_db), _: User = Depends(current_user)):
    q = db.query(Customer)
    rows = q.order_by(Customer.id).offset((page - 1) * page_size).limit(page_size).all()
    return {"total": q.count(), "page": page, "page_size": page_size,
            "items": [dict(id=c.id, customer_code=c.customer_code, full_name=c.full_name, home_city=c.home_city,
                           avg_transaction_amount=float(c.avg_transaction_amount)) for c in rows]}


@app.get(f"{P}/transactions")
def list_transactions(customer_id: int | None = Query(None, gt=0), risk_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] | None = None,
                      page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100),
                      db: Session = Depends(get_db), _: User = Depends(current_user)):
    q = db.query(Transaction)
    if customer_id:
        q = q.filter(Transaction.customer_id == customer_id)
    if risk_level:
        q = q.filter(Transaction.risk_level == risk_level)
    rows = q.order_by(Transaction.occurred_at.desc(), Transaction.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"total": q.count(), "page": page, "page_size": page_size, "items": [txn_out(t) for t in rows]}


@app.post(f"{P}/transactions", status_code=201)
def create_transaction(body: TransactionCreate, db: Session = Depends(get_db), user: User = Depends(require_roles(*INVESTIGATE)),
                       idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", min_length=8, max_length=64)):
    """Submits a payment through the ledger: it is risk-scored, then either POSTED (balances move, double-entry), HELD for analyst
    review (HIGH/CRITICAL risk, nothing moves yet) or FAILED (e.g. insufficient funds). Send an Idempotency-Key header so a retried
    request can never move money twice."""
    customer = db.get(Customer, body.customer_id)
    if not customer:
        raise HTTPException(404, f"Customer {body.customer_id} not found")
    try:
        out = payments.submit(db, customer, body.model_dump(), idempotency_key, user.username)
    except LedgerError as exc:
        db.rollback()
        raise HTTPException(exc.http_status, exc.message)
    db.commit()
    db.refresh(out.txn)
    payload = {**txn_out(out.txn), "case_number": out.case.case_number if out.case else None, "replayed": out.replayed}
    if out.error:  # the failed attempt IS stored (it feeds the risk engine), but the caller is told it did not go through
        return JSONResponse(status_code=out.error.http_status, content=jsonable_encoder({"detail": out.error.message, "code": out.error.code, "transaction": payload}))
    if out.replayed:
        return JSONResponse(status_code=200, content=jsonable_encoder(payload))
    return payload


# ---- optional: serve the built React app from this same process (single-container deploys such as Hugging Face Spaces) ----
_DIST = Path(settings.FRONTEND_DIST).resolve() if settings.FRONTEND_DIST else None
if _DIST and (_DIST / "index.html").is_file():
    if (_DIST / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(404, "Not found")
        candidate = (_DIST / full_path).resolve()
        if full_path and candidate.is_file() and candidate.is_relative_to(_DIST):  # is_relative_to blocks ../ traversal
            return FileResponse(candidate)
        return FileResponse(_DIST / "index.html", headers={"Cache-Control": "no-cache"})
