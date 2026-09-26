import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure all database models are explicitly imported first
from app.db.models import Base, get_db, User, Portfolio
from backend.app.main import app

# Use StaticPool to persist in-memory SQLite tables across multiple session connections
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Apply FastAPI dependency override
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_and_teardown_db():
    """Create clean database tables before each test and drop them after."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    """Provide a clean TestClient instance for testing FastAPI endpoints."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def authenticated_client(client):
    """Fixture that registers a user, logs in, and yields a client with JWT headers."""
    user_data = {"email": "trader@example.com", "password": "password123"}
    
    # Register user
    client.post("/auth/register", json=user_data)
    
    # Login to retrieve token
    login_response = client.post(
        "/auth/login",
        data={"username": user_data["email"], "password": user_data["password"]},
    )
    token = login_response.json()["access_token"]
    
    # Configure client with Authorization Bearer header
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


# =====================================================================
# TEST CASES
# =====================================================================

def test_1_user_registration_success(client):
    """Test 1: User registration with valid email and password."""
    response = client.post(
        "/auth/register",
        json={"email": "newuser@example.com", "password": "securepassword123"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert "id" in data
    assert "hashed_password" not in data  # Ensure sensitive hash is not exposed


def test_2_duplicate_user_registration_fails(client):
    """Test 2: Registering an existing email returns 400 Bad Request."""
    user_payload = {"email": "duplicate@example.com", "password": "password123"}
    
    # Initial registration
    client.post("/auth/register", json=user_payload)
    
    # Duplicate attempt
    response = client.post("/auth/register", json=user_payload)
    assert response.status_code == 400
    assert response.json()["detail"] == "Email is already registered"


def test_3_pydantic_validation_fails_for_invalid_input(client):
    """Test 3: Verify Pydantic schema validation rejects bad requests (invalid email & short password)."""
    invalid_payload = {"email": "not-an-email", "password": "123"}
    
    response = client.post("/auth/register", json=invalid_payload)
    assert response.status_code == 422  # Unprocessable Entity
    errors = response.json()["detail"]
    assert len(errors) >= 1


def test_4_unauthenticated_portfolio_access_denied(client):
    """Test 4: Requesting protected portfolio endpoints without JWT token fails with 401 Unauthorized."""
    response = client.get("/portfolio/")
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_5_authenticated_portfolio_access_success(authenticated_client):
    """Test 5: Requesting portfolio endpoint with valid JWT token succeeds (completes requirement for 5 passing tests)."""
    response = authenticated_client.get("/portfolio/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)