import os
from contextlib import asynccontextmanager
from datetime import date
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI
from passlib.context import CryptContext
from pymongo import MongoClient

from .common_utils import generate_credential_id
from .logging_utils import setup_logging

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
logger = setup_logging(__name__)

def setup_db():
    client = MongoClient(MONGODB_URI)
    db = client["certify"]
    return db,client

db,client = setup_db()

def seed_signatures():
    signatures = db["signatures"]
    if signatures.count_documents({}) == 0:
        with open("test_signature.b64", "r") as f:
            base64_signature_1 = f.read().strip()
        signatures.insert_many([
            {"id": "pmvodpn5", "name": "Amal", "post": "President", "image_b64": base64_signature_1},
            {"id": "szoii2l2", "name": "Kamal", "post": "Secretary", "image_b64": base64_signature_1}
        ])
        logger.info("Inserted sample signatures: %s, %s", "pmvodpn5", "szoii2l2")
    else:
        logger.info("Signatures collection already has data, skipping seed.")

def seed_certificates():
    certificates = db["certificates"]
    if certificates.count_documents({}) == 0:
        cred_id = generate_credential_id()
        certificates.insert_one({
            "credentialId": cred_id,
            "name": "Saman Sliva",
            "course": "Club Member",
            "categoryCode": "LC",
            "categoryName": "Leadership & Contribution",
            "dateIssued": date.today().isoformat(),
            "issuer": "Mozilla Campus Club SLIIT",
            "signatures": ["pmvodpn5", "szoii2l2"]
        })
        logger.info("Inserted sample certificate with credentialId: %s", cred_id)
    else:
        logger.info("Certificates collection already has data, skipping seed.")

def seed_users():
    users = db["users"]
    if users.count_documents({}) == 0:
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        fake_users = [
            {
                "name": "Admin User",
                "email": "admin@example.com",
                "password": pwd_context.hash("1234"),
                "role": "admin"
            },
            {
                "name": "Regular User",
                "email": "user@example.com",
                "password": pwd_context.hash("1234"),
                "role": "user"
            }
        ]
        users.insert_many(fake_users)
        logger.info("Inserted sample users: admin@example.com, user@example.com")
    else:
        logger.info("Users collection already has data, skipping seed.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        client.admin.command("ping")
        logger.info("Successfully connected to MongoDB")
    except Exception as e:
        logger.error("MongoDB connection failed: %s", e)

    seed_signatures()
    seed_certificates()
    seed_users()

    yield

def get_certificate_by_credential(credential_id: str) -> Optional[dict]:
    cert = db["certificates"].find_one({"credentialId": credential_id})
    if cert:
        cert["_id"] = str(cert["_id"])
    return cert

def get_signatures_by_ids(signature_ids: list) -> list[dict]:
    signature_docs = list(db["signatures"].find({"id": {"$in": signature_ids}}))
    for sig in signature_docs:
        sig["_id"] = str(sig.get("_id", ""))

    logger.info(
        "Fetched %d signature(s) for IDs: %s",
        len(signature_docs),
        signature_ids
    )

    if len(signature_docs) < len(signature_ids):
        missing = set(signature_ids) - {sig["id"] for sig in signature_docs}
        logger.warning("Signatures not found for IDs: %s", list(missing))

    return signature_docs

def get_user_by_email(email: str):
    user = db["users"].find_one({"email": email})
    if user:
        logger.info("Found user with email: %s", email)
    else:
        logger.warning("No user found with email: %s", email)
    return user