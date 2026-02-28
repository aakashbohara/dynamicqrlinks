import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Explicitly load .env from project root (parent of app/)
ENV_PATH = Path(__file__).parent.parent / ".env"
load_dotenv(ENV_PATH)
ENVIRONMENT = os.getenv("ENVIRONMENT", "dev")

# Dev: SQLite (zero config), Prod: PostgreSQL
if ENVIRONMENT == "prod":
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL must be set in production")
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=1800,
    )
else:
    # SQLite for local dev — stored next to the app folder
    DB_PATH = Path(__file__).parent.parent / "qrlinks_dev.db"
    DATABASE_URL = f"sqlite:///{DB_PATH}"
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},  # needed for SQLite + FastAPI
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
