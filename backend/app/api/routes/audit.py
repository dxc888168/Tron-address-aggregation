from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import AuditLog, User

router = APIRouter(prefix='/audit-logs', tags=['audit'])


@router.get('')
def list_audit_logs(
    page: int = 1,
    page_size: int = 50,
    action: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    del current_user

    query = select(AuditLog).order_by(AuditLog.created_at.desc())
    if action:
        query = query.where(AuditLog.action == action)

    all_items = db.scalars(query).all()
    total = len(all_items)
    rows = all_items[(page - 1) * page_size : (page - 1) * page_size + page_size]

    items = [
        {
            'id': str(x.id),
            'actor_user_id': str(x.actor_user_id) if x.actor_user_id else None,
            'action': x.action,
            'target_type': x.target_type,
            'target_id': x.target_id,
            'created_at': x.created_at.isoformat() if x.created_at else None,
        }
        for x in rows
    ]

    return {'items': items, 'page': page, 'page_size': page_size, 'total': total}
