import os
from pathlib import Path
import tomllib
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from app.core.config import config

# Resolve the backend directory (/app inside the container)
# Path(__file__) = /app/app/schemas/schemas.py
# .parent (schemas) -> .parent (app) -> .parent (/app)
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Check every possible location where config.toml might exist
POSSIBLE_PATHS = [
    BASE_DIR / "config.toml",              # /app/config.toml
    Path.cwd() / "config.toml",            # Current working directory (/app/config.toml)
    Path("/app/config.toml"),              # Explicit container path
]

CONFIG_PATH = next((p for p in POSSIBLE_PATHS if p.exists()), None)

config = {}
if CONFIG_PATH and CONFIG_PATH.is_file():
    with open(CONFIG_PATH, "rb") as f:
        config = tomllib.load(f)
else:
    print(f"WARNING: config.toml not found in {POSSIBLE_PATHS}. Proceeding with default values.")

db_user_config = config.get("database", {}).get("users", {})

class UserCreate(BaseModel):
    # Set default values from [database.users] if desired
    email: EmailStr = Field(default=db_user_config.get("admin_email", "user@example.com"))
    password: str = Field(
        ...,
        min_length=6,
        max_length=70,
        description="Password must be between 6 and 70 characters long"
    )


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    email: str | None = None

class PortfolioCreate(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=10, description="Stock ticker symbol (e.g., AAPL, NVDA)")
    shares: float = Field(..., gt=0, description="Number of shares owned (must be > 0)")
    buy_price: float = Field(..., gt=0, description="Purchase price per share (must be > 0)")


class PortfolioResponse(PortfolioCreate):
    id: int
    user_id: int
    added_at: datetime

    class Config:
        from_attributes = True    

class StockDataResponse(BaseModel):
    ticker: str
    company_name: str
    current_price: float
    currency: str = "USD"
    previous_close: Optional[float] = None
    market_cap: Optional[int] = None
    year_to_date_high: Optional[float] = None
    year_to_date_low: Optional[float] = None
    trailing_pe: Optional[float] = None
    forward_pe: Optional[float] = None
    summary: str = "No summary available."
