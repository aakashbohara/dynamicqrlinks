import secrets
import string

import models
import schemas
from sqlalchemy.orm import Session

ALPHABET = string.ascii_letters + string.digits

def generate_code(length: int = 7) -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(length))

def create_link(db: Session, link_in: schemas.LinkCreate) -> models.ShortLink:
    code = (link_in.code or generate_code()).strip()
    while db.query(models.ShortLink).filter_by(code=code).first():
        code = generate_code()
    link = models.ShortLink(code=code, target_url=link_in.target_url)
    db.add(link)
    db.commit()
    db.refresh(link)
    return link

def update_link(db: Session, code: str, target_url: str) -> models.ShortLink | None:
    link = db.query(models.ShortLink).filter_by(code=code).first()
    if not link:
        return None
    link.target_url = target_url
    db.commit()
    db.refresh(link)
    return link

def delete_link(db: Session, code: str) -> bool:
    link = db.query(models.ShortLink).filter_by(code=code).first()
    if not link:
        return False
    db.delete(link)
    db.commit()
    return True

def get_link(db: Session, code: str) -> models.ShortLink | None:
    return db.query(models.ShortLink).filter_by(code=code).first()

def get_links(db: Session, skip: int = 0, limit: int = 100) -> list[models.ShortLink]:
    return (
        db.query(models.ShortLink)
        .order_by(models.ShortLink.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

def count_links(db: Session) -> int:
    return db.query(models.ShortLink).count()

def increment_click(db: Session, code: str) -> None:
    link = db.query(models.ShortLink).filter_by(code=code).first()
    if link:
        link.click_count = (link.click_count or 0) + 1
        db.commit()
