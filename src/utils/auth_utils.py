from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, Request
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from passlib.context import CryptContext

from src.config import ACCESS_TOKEN_EXPIRE_MINUTES, ALGORITHM, SECRET_KEY
from src.utils.db_utils import get_user_by_email
from src.utils.logging_utils import setup_logging

logger = setup_logging(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def verify_password(plain_password, hashed_password):
    result = pwd_context.verify(plain_password, hashed_password)
    logger.info("Password verification result: %s", result)
    return result

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta if expires_delta else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    logger.info("JWT created for sub: %s, role: %s", to_encode.get("sub"), to_encode.get("role"))
    return token

def authenticate_user(email: str, password: str):
    logger.info("Authenticating user with email: %s", email)
    user = get_user_by_email(email)
    if not user:
        logger.warning("Authentication failed: user not found for email: %s", email)
        return None
    if not verify_password(password, user["password"]):
        logger.warning("Authentication failed: invalid password for email: %s", email)
        return None
    logger.info("Authentication successful for email: %s", email)
    return user

async def process_login_request(request: Request):
    try:
        data = await request.json()
    except Exception:
        logger.error("Failed to read JSON body in login request")
        raise HTTPException(status_code=400, detail="Invalid request payload")

    email = data.get("email")
    password = data.get("password")

    logger.info("Login attempt for email: %s", email)

    if not email or not password:
        logger.warning("Login failed: missing email or password for email: %s", email)
        raise HTTPException(status_code=400, detail="Email and password required")

    user = authenticate_user(email, password)
    if not user:
        logger.warning("Login failed: invalid credentials for email: %s", email)
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token_data = {"sub": user["email"], "role": user["role"]}
    access_token = create_access_token(token_data)

    logger.info("Login successful for email: %s", email)
    return {"access_token": access_token, "token_type": "bearer"}