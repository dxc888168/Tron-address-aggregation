from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.ids import ensure_uuid
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/api/v1/auth/login', auto_error=False)


def get_current_user(token: str | None = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    settings = get_settings()
    if settings.auth_disabled:
        user = db.scalar(select(User).where(User.username == settings.admin_username, User.is_active.is_(True)))
        if user:
            return user
        user = db.scalar(select(User).where(User.is_active.is_(True)).order_by(User.created_at.asc()))
        if user:
            return user
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='No active user available')

    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Missing token')

    user_id = decode_access_token(token)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid token')

    try:
        user_uuid = ensure_uuid(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid token subject') from exc

    user = db.scalar(select(User).where(User.id == user_uuid, User.is_active.is_(True)))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='User not found')

    return user
