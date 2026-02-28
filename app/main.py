import logging
import os
import re
from pathlib import Path

import auth
import crud
import database
import models
import qr_utils
import schemas
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles

load_dotenv(Path(__file__).parent.parent / ".env")

ENVIRONMENT = os.getenv("ENVIRONMENT", "dev")

# --- Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger("qrlinks")

# --- DB tables ---
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(
    title="Dynamic QR Links",
    description="Create short links with dynamic QR codes. Update destinations without changing the QR.",
    version="1.0.0",
)

# --- CORS (allow frontend dev servers, etc.) ---
origins = ["*"] if ENVIRONMENT == "dev" else [
    os.getenv("PUBLIC_BASE_URL", "http://localhost:8000"),
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Serve frontend (same origin) ----
FRONTEND_DIR = Path(__file__).parent / "frontend"
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

@app.get("/", include_in_schema=False)
def serve_index():
    return FileResponse(FRONTEND_DIR / "index.html")

# Gate dashboard by cookie token
@app.get("/dashboard", include_in_schema=False)
def serve_dashboard(request: Request):
    if not auth.get_user_from_cookie(request):
        return RedirectResponse("/", status_code=307)
    return FileResponse(FRONTEND_DIR / "dashboard.html")

# Small config for frontend to know public base URL
@app.get("/config", include_in_schema=False)
def get_config(request: Request):
    base = os.getenv("PUBLIC_BASE_URL") or str(request.base_url).rstrip("/")
    return {"public_base_url": base}

# Health check (useful for uptime monitors & load balancers)
@app.get("/health", include_in_schema=False)
def health():
    return {"status": "ok", "env": ENVIRONMENT}

# ---------- API ----------
@app.post("/login", response_model=schemas.Token)
def login(response: Response, form_data: OAuth2PasswordRequestForm = Depends()):
    if not auth.authenticate_user(form_data.username, form_data.password):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    token = auth.create_access_token({"sub": form_data.username})
    # Only set secure cookie if HTTPS is configured
    is_https = os.getenv("PUBLIC_BASE_URL", "").startswith("https://")
    response.set_cookie(
        key="access_token", value=token,
        httponly=True, samesite="lax", secure=is_https, path="/", max_age=3600
    )
    return {"access_token": token, "token_type": "bearer"}

@app.post("/logout", include_in_schema=False)
def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    return {"ok": True}

@app.post("/create", response_model=schemas.LinkOut)
def create_link(link_in: schemas.LinkCreate, db=Depends(database.get_db), user=Depends(auth.get_current_user)):
    logger.info("Creating link: code=%s target=%s by=%s", link_in.code, link_in.target_url, user)
    return crud.create_link(db, link_in)

@app.patch("/update/{code}", response_model=schemas.LinkOut)
def update_link(code: str, link_in: schemas.LinkUpdate, db=Depends(database.get_db), user=Depends(auth.get_current_user)):
    link = crud.update_link(db, code, link_in.target_url)
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    logger.info("Updated link %s → %s by=%s", code, link_in.target_url, user)
    return link

@app.delete("/delete/{code}", response_model=schemas.MessageOut)
def delete_link(code: str, db=Depends(database.get_db), user=Depends(auth.get_current_user)):
    ok = crud.delete_link(db, code)
    if not ok:
        raise HTTPException(status_code=404, detail="Link not found")
    logger.info("Deleted link %s by=%s", code, user)
    return {"ok": True, "detail": f"Link '{code}' deleted"}

@app.get("/links", response_model=schemas.PaginatedLinks)
def list_links(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db=Depends(database.get_db),
    user=Depends(auth.get_current_user),
):
    items = crud.get_links(db, skip=skip, limit=limit)
    total = crud.count_links(db)
    return {"items": items, "total": total, "skip": skip, "limit": limit}

# Back-compat /r/{code}
@app.get("/r/{code}", include_in_schema=False)
def redirect_r(code: str, db=Depends(database.get_db)):
    link = crud.get_link(db, code)
    if not link:
        raise HTTPException(status_code=404, detail="Not found")
    try:
        crud.increment_click(db, code)
    except Exception:
        logger.exception("Failed to increment click for %s", code)
    return RedirectResponse(url=link.target_url, status_code=307)

# Pretty redirect /{code}
RESERVED = {"", "docs", "openapi.json", "redoc", "static", "dashboard", "config",
            "login", "logout", "create", "update", "delete", "links", "qr",
            "favicon.ico", "health"}

@app.get("/{code}", include_in_schema=False)
def redirect_pretty(code: str, db=Depends(database.get_db)):
    if code in RESERVED or not re.fullmatch(r"[A-Za-z0-9_-]{2,32}", code):
        raise HTTPException(status_code=404, detail="Not found")
    link = crud.get_link(db, code)
    if not link:
        raise HTTPException(status_code=404, detail="Not found")
    try:
        crud.increment_click(db, code)
    except Exception:
        logger.exception("Failed to increment click for %s", code)
    return RedirectResponse(url=link.target_url, status_code=307)

@app.get("/qr/{code}")
def qr_code(code: str, request: Request, db=Depends(database.get_db)):
    link = crud.get_link(db, code)
    if not link:
        raise HTTPException(status_code=404, detail="Not found")
    base = os.getenv("PUBLIC_BASE_URL") or str(request.base_url).rstrip("/")
    qr_b64 = qr_utils.generate_qr_base64(f"{base}/{link.code}")
    return {"qr_base64": qr_b64}
