import os
from pathlib import Path
import bcrypt
import tomllib
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from app.core.config import config

from app.db.models import User, get_db
from app.schemas.schemas import TokenData

# /app/app/core/security.py -> .parent (core) -> .parent (app) -> .parent (/app)
BASE_DIR = Path(__file__).resolve().parent.parent.parent

POSSIBLE_PATHS = [
    BASE_DIR / "config.toml",              # /app/config.toml
    Path.cwd() / "config.toml",            # Current working directory
    Path("/app/config.toml"),              # Explicit container working path
]

CONFIG_PATH = next((p for p in POSSIBLE_PATHS if p.exists()), None)

config = {}
if CONFIG_PATH and CONFIG_PATH.is_file():
    with open(CONFIG_PATH, "rb") as f:
        config = tomllib.load(f)
else:
    print(f"WARNING: config.toml not found in {POSSIBLE_PATHS}. Fallback to env or defaults.")

# Access variables via the [database.users] table dictionary
db_user_config = config.get("database", {}).get("users", {})

SECRET_KEY = db_user_config.get("jwt_secret", "fallback-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    pwd_bytes = plain_password.encode('utf-8')[:72]
    hash_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(pwd_bytes, hash_bytes)


def get_password_hash(password: str) -> str:
    # Encode string to UTF-8 bytes and truncate to max 72 bytes
    pwd_bytes = password.encode('utf-8')[:72]
    # Generate salt and hash
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode('utf-8')


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.email == token_data.email).first()
    if user is None:
        raise credentials_exception
    return user