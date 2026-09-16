import os
import tomllib
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.db.models import Base, engine, get_db, User, Portfolio
from app.schemas.schemas import UserCreate, UserResponse, Token, PortfolioCreate, PortfolioResponse, StockDataResponse
from app.core.security import get_password_hash, verify_password, create_access_token, get_current_user
from app.services.yahoo_services import get_stock_data

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "config.toml")

# Read TOML settings
if os.path.exists(CONFIG_PATH):
    with open(CONFIG_PATH, "rb") as f:
        config = tomllib.load(f)
else:
    config = {}

# Extract nested TOML sections with fallbacks
app_config = config.get("app", {})
server_config = config.get("server", {})

# =====================================================================
# FASTAPI APP INITIALIZATION
# =====================================================================
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=app_config.get("title", "Yahoo Finance RAG Tracker API"),
    version=app_config.get("version", "1.0.0"),
    description=app_config.get("description", "API for portfolio tracking and RAG financial research"),
)

# Optional CORS middleware setup using allowed origins from config.toml
allowed_origins = server_config.get("cors_origins", ["*"])
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =====================================================================
# AUTHENTICATION ENDPOINTS
# =====================================================================
@app.post("/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED, tags=["Auth"])
def register_user(user_in: UserCreate, db: Session = Depends(get_db)):
    """Register a new user with password validation."""
    db_user = db.query(User).filter(User.email == user_in.email).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already registered"
        )
    
    hashed_pwd = get_password_hash(user_in.password)
    new_user = User(email=user_in.email, hashed_password=hashed_pwd)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@app.post("/auth/login", response_model=Token, tags=["Auth"])
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Authenticate user and generate JWT token."""
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

# Fetching Yahoo Finance API Service
@app.get("/stocks/{ticker}", response_model=StockDataResponse,tags=["Stocks"])
def fetch_stock_info(ticker: str):
    try:
        data = get_stock_data(ticker)
        return data
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch ticker data: {str(e)}")
# =====================================================================
# PORTFOLIO ENDPOINTS (PROTECTED)
# =====================================================================
@app.post("/portfolio/", response_model=PortfolioResponse, status_code=status.HTTP_201_CREATED, tags=["Portfolio"])
def add_portfolio_item(
    item_in: PortfolioCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a stock holding to the current user's portfolio."""
    ticker_upper = item_in.ticker.upper().strip()
    
    portfolio_item = Portfolio(
        user_id=current_user.id,
        ticker=ticker_upper,
        shares=item_in.shares,
        buy_price=item_in.buy_price
    )
    db.add(portfolio_item)
    db.commit()
    db.refresh(portfolio_item)
    return portfolio_item


@app.get("/portfolio/", response_model=list[PortfolioResponse], tags=["Portfolio"])
def get_user_portfolio(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Fetch all portfolio holdings belonging to the authenticated user."""
    return db.query(Portfolio).filter(Portfolio.user_id == current_user.id).all()


@app.delete("/portfolio/{portfolio_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Portfolio"])
def delete_portfolio_item(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove a stock holding from the portfolio."""
    item = db.query(Portfolio).filter(
        Portfolio.id == portfolio_id, 
        Portfolio.user_id == current_user.id
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Portfolio item not found")
        
    db.delete(item)
    db.commit()
    return None