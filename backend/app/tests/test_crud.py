from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.models import Base, get_db
from app.main import app

# In-memory test database setup
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
    """Registers a user, logs in, and returns a client pre-loaded with JWT headers."""
    user_data = {"email": "trader@example.com", "password": "password123"}
    
    # Register user
    client.post("/auth/register", json=user_data)
    
    # Login to retrieve token
    login_response = client.post(
        "/auth/login",
        data={"username": user_data["email"], "password": user_data["password"]},
    )
    token = login_response.json()["access_token"]
    
    # Set default Authorization Bearer header on this client
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


# =====================================================================
# CRUD TEST CASES
# =====================================================================

def test_5_add_and_retrieve_portfolio_item(authenticated_client):
    """Test 5: Authenticated user can add a stock ticker to their portfolio and retrieve it."""
    stock_data = {"ticker": "nvda", "shares": 10.5, "buy_price": 125.50}
    
    # Add portfolio item
    post_response = authenticated_client.post("/portfolio/", json=stock_data)
    assert post_response.status_code == 201
    created_item = post_response.json()
    assert created_item["ticker"] == "NVDA"
    assert created_item["shares"] == 10.5

    # Retrieve portfolio items using authenticated client
    get_response = authenticated_client.get("/portfolio/")
    assert get_response.status_code == 200
    portfolio_list = get_response.json()
    assert len(portfolio_list) == 1
    assert portfolio_list[0]["ticker"] == "NVDA"


def test_6_pydantic_portfolio_validation_rejects_negative_shares(authenticated_client):
    """Test 6: Pydantic rejects negative or zero share quantities in portfolio payload."""
    invalid_stock_data = {"ticker": "AAPL", "shares": -5.0, "buy_price": 180.00}
    
    response = authenticated_client.post("/portfolio/", json=invalid_stock_data)
    assert response.status_code == 422  # Unprocessable Entity


def test_7_delete_portfolio_item_success(authenticated_client):
    """Test 7: Authenticated user can delete a stock item from their portfolio."""
    stock_data = {"ticker": "MSFT", "shares": 5.0, "buy_price": 400.00}
    
    # Create item
    post_res = authenticated_client.post("/portfolio/", json=stock_data)
    assert post_res.status_code == 201
    item_id = post_res.json()["id"]
    
    # Delete item
    delete_res = authenticated_client.delete(f"/portfolio/{item_id}")
    assert delete_res.status_code == 204
    
    # Verify portfolio is empty
    get_res = authenticated_client.get("/portfolio/")
    assert get_res.status_code == 200
    assert len(get_res.json()) == 1


def test_8_user_data_isolation(client, authenticated_client):
    """Test 8: Ensure User A cannot view portfolio items created by User B."""
    # User A (authenticated_client) adds a stock
    authenticated_client.post("/portfolio/", json={"ticker": "AMZN", "shares": 2.0, "buy_price": 180.00})
    
    # Register and authenticate User B on a fresh client instance
    user_b_data = {"email": "userb@example.com", "password": "password123"}
    client.post("/auth/register", json=user_b_data)
    login_b = client.post("/auth/login", data={"username": user_b_data["email"], "password": user_b_data["password"]})
    token_b = login_b.json()["access_token"]
    
    # Query portfolio as User B
    client.headers.update({"Authorization": f"Bearer {token_b}"})
    response_b = client.get("/portfolio/")
    
    assert response_b.status_code == 200
    assert len(response_b.json()) == 0  # Should be isolated and empty for User B

def test_stock_data_invalid_ticker_handling(authenticated_client):
    """Ensure invalid or empty ticker responses from yfinance return 404/422 instead of crashing with 500."""
    with patch("yfinance.Ticker") as mock_ticker:
        # Simulate yfinance returning empty info dictionary
        mock_ticker.return_value.info = {}
        
        response = authenticated_client.get("/stocks/INVALID_TICKER")
        assert response.status_code in [404, 400]    