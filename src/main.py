from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from src.models import Certificate
from src.utils import (
    get_certificate_by_credential,
    get_signatures_by_ids,
    lifespan,
    process_login_request,
    setup_db,
    setup_logging,
)
from src.utils.certificate_img_utils import generate_certificate_image

logger = setup_logging(__name__)
db,client = setup_db()
app = FastAPI(lifespan=lifespan)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def read_root():
    logger.info("Root endpoint '/' was called")
    return {"message": "Hello, Certify!"}
    
@app.post("/api/login")
async def login(request: Request):
    return await process_login_request(request)


@app.get("/api/certificate/{credential_id}")
async def get_certificate(credential_id: str):
    logger.info(credential_id)
    cert_doc = get_certificate_by_credential(credential_id)
    if not cert_doc:
        raise HTTPException(status_code=404, detail="Certificate not found")

    signatures = get_signatures_by_ids(cert_doc.get("signatures", []))
    cert_doc["signatures"] = signatures

    cert = Certificate(**cert_doc)
    img_b64 = generate_certificate_image(cert)

    # Return all certificate fields plus image_b64
    cert_dict = cert.dict(by_alias=True)
    cert_dict["image_b64"] = img_b64
    return cert_dict


# Note: To use the PORT variable, run the server with:
# python -m uvicorn src.main:app --reload --port %PORT%
# (on Windows CMD; use $PORT for bash)
