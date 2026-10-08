"""Pytest configuration and reusable fixtures for backend test suite."""
import os
import pytest
from typing import Generator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker, Session

# Configure test environment variables prior to app import
os.environ["ENVIRONMENT"] = "development"
os.environ["DEMO_MODE"] = "true"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["DEMO_JWT_SECRET"] = "pytest-secret-key-32-chars-long-minimum"

from app.core.database import Base, get_db
from app.models.models import Candidate, Policy, Evaluation, Approval, ReleaseManifest, AuditLog
from app.core.security import create_demo_token
from app.main import app

# In-memory SQLite engine using StaticPool so tables persist across connections
test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    future=True
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine, future=True)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Create all database tables and seed baseline policies for the test session."""
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    try:
        import json
        p = Policy(
            name="Test-Default-Policy",
            task_type="text-generation",
            description="Default test policy",
            rules=json.dumps([
                {
                    "metric_name": "accuracy",
                    "operator": ">=",
                    "threshold": 0.80,
                    "tolerance": 0.02,
                    "severity": "blocker",
                    "description": "Accuracy threshold"
                },
                {
                    "metric_name": "latency_ms",
                    "operator": "<=",
                    "threshold": 200.0,
                    "tolerance": 10.0,
                    "severity": "warning",
                    "description": "Latency threshold"
                }
            ]),
            is_default=True,
            version=1,
            created_by="pytest-init"
        )
        db.add(p)
        db.commit()
    finally:
        db.close()
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Provide a fresh transactional session for a test."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """TestClient overriding get_db dependency to point to in-memory database."""
    def override_get_db():
        try:
            yield db_session
            db_session.commit()
        except Exception:
            db_session.rollback()
            raise

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def viewer_token() -> str:
    """Valid JWT bearer token with viewer role."""
    return create_demo_token(username="alice-viewer", email="alice@example.com", role="viewer")


@pytest.fixture
def analyst_token() -> str:
    """Valid JWT bearer token with analyst role."""
    return create_demo_token(username="bob-analyst", email="bob@example.com", role="analyst")


@pytest.fixture
def admin_token() -> str:
    """Valid JWT bearer token with admin role."""
    return create_demo_token(username="carol-admin", email="carol@example.com", role="admin")
