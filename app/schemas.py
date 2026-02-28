from pydantic import BaseModel, ConfigDict


class LinkBase(BaseModel):
    target_url: str

class LinkCreate(LinkBase):
    code: str | None = None

class LinkUpdate(BaseModel):
    target_url: str

class LinkOut(BaseModel):
    code: str
    target_url: str
    click_count: int

    model_config = ConfigDict(from_attributes=True)

class PaginatedLinks(BaseModel):
    items: list[LinkOut]
    total: int
    skip: int
    limit: int

class Token(BaseModel):
    access_token: str
    token_type: str

class MessageOut(BaseModel):
    ok: bool
    detail: str
