import time
from collections import defaultdict, deque
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.chat import service
from app.core.config import get_settings
from app.core.deps import current_user
from app.db.base import User
from app.db.session import get_db

router = APIRouter()
_hits: dict[str, deque] = defaultdict(deque)


class Turn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=2000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    history: list[Turn] = Field(default_factory=list, max_length=12)


def _limited(user: str) -> bool:
    """Per-user sliding window; every chat message can cost an LLM call, so this is tighter than the global limit."""
    now, q = time.time(), _hits[user]
    while q and now - q[0] > 60:
        q.popleft()
    if len(q) >= get_settings().CHAT_RATE_LIMIT_PER_MINUTE:
        return True
    q.append(now)
    return False


@router.get("/assistant/suggestions")
def suggestions(_: User = Depends(current_user)):
    return {"suggestions": service.SUGGESTIONS}


@router.post("/assistant/chat")
def chat(body: ChatRequest, db: Session = Depends(get_db), user: User = Depends(current_user)):
    if _limited(user.username):
        raise HTTPException(429, "You're sending messages too quickly. Try again in a minute.", headers={"Retry-After": "60"})
    return service.answer(db, body.message.strip(), [t.model_dump() for t in body.history])
