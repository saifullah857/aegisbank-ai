import os

# Must be set before any `app` import: Settings is cached on first use.
import tempfile

_TMP = tempfile.mkdtemp(prefix="aegis-test-")
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["ML_MODEL_PATH"] = f"{_TMP}/model.joblib"            # absent until a test trains one
os.environ["CHROMA_PERSIST_DIR"] = f"{_TMP}/chroma"
os.environ["RAG_EMBEDDER_PATH"] = f"{_TMP}/embedder.joblib"
os.environ["API_RATE_LIMIT_PER_MINUTE"] = "1000000"
os.environ["LOGIN_RATE_LIMIT_PER_MINUTE"] = "100000"            # a dedicated test lowers it
os.environ.pop("GROQ_API_KEY", None)
os.environ["JWT_SECRET"] = "test-secret-" + "x" * 40

from datetime import datetime, timedelta, timezone  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.core.security import hash_password  # noqa: E402
from app.db.base import Account, Base, Customer, Transaction, User  # noqa: E402
from app.services.ledger import CLEARING_NUMBER  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402

PASSWORD = "TestPass123!"


@pytest.fixture(scope="session", autouse=True)
def policy_index():
    """Build the policy vector index once, in the temp dir, so retrieval is real in every test."""
    from app.rag import policy_service
    policy_service.ingest()


@pytest.fixture(autouse=True)
def isolate_ml_and_llm():
    """No ML model and no LLM unless a test explicitly sets one up — keeps tests order-independent."""
    from app.ml import inference
    from app.services.llm import GroqClient, set_llm_client
    inference.reset()
    if inference.model_path().exists():
        inference.model_path().unlink()
    set_llm_client(GroqClient(None, "test-model"))
    yield
    inference.reset()
    set_llm_client(None)


@pytest.fixture
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False)()
    yield session
    session.close()


@pytest.fixture
def client(db):
    app.dependency_overrides[get_db] = lambda: (yield db)
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def users(db):
    for name, role in [("admin", "ADMIN"), ("analyst01", "FRAUD_ANALYST"), ("auditor01", "AUDITOR"), ("viewer01", "VIEWER")]:
        db.add(User(username=name, full_name=name, role=role, hashed_password=hash_password(PASSWORD)))
    db.commit()


def login_headers(client, username):
    r = client.post("/api/v1/auth/login", json={"username": username, "password": PASSWORD})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def analyst(client, users):
    return login_headers(client, "analyst01")


@pytest.fixture
def viewer(client, users):
    return login_headers(client, "viewer01")


@pytest.fixture
def world(db):
    """One Lahore customer with 6 ordinary grocery transactions on a known device."""
    c = Customer(customer_code="CUST-T1", full_name="Test Customer", home_city="Lahore", avg_transaction_amount=8000,
                 typical_locations=["Lahore"], known_devices=["device-known"], known_beneficiaries=[])
    db.add(c)
    db.commit()
    db.add_all([Account(account_number=CLEARING_NUMBER, account_type="SYSTEM"),
                Account(account_number="PK36AEGBTEST000000000001", customer_id=c.id, opening_balance=50_000_000, balance=50_000_000)])
    db.commit()
    base = datetime.now(timezone.utc) - timedelta(days=10)
    for i in range(6):
        db.add(Transaction(transaction_ref=f"TXN-H{i}", customer_id=c.id, amount=7500, transaction_type="CARD_PAYMENT",
                           merchant="Al-Fatah", merchant_category="Grocery", location="Lahore", device_id="device-known",
                           occurred_at=(base + timedelta(days=i)).replace(hour=14)))
    db.commit()
    return c


@pytest.fixture
def admin(client, users):
    return login_headers(client, "admin")


@pytest.fixture
def auditor(client, users):
    return login_headers(client, "auditor01")
