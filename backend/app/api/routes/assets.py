from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import User
from app.services.asset_service import get_assets_overview, sync_assets
from app.services.audit_service import write_audit

router = APIRouter(prefix='/assets', tags=['assets'])


class AssetSyncRequest(BaseModel):
    mode: str = 'INCREMENTAL'
    address_ids: list[str] = Field(default_factory=list)
    force: bool = False


@router.post('/sync')
def sync_assets_api(
    payload: AssetSyncRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = sync_assets(db, payload.address_ids or None)

    write_audit(
        db,
        actor_user_id=current_user.id,
        action='ASSET_SYNC',
        target_type='SYSTEM',
        detail={
            'mode': payload.mode,
            'force': payload.force,
            'processed': result.get('processed', 0),
            'failed': result.get('failed', 0),
            'warnings': len(result.get('warnings', [])),
        },
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get('user-agent'),
    )
    db.commit()

    return {
        'accepted': True,
        'task_id': f"sync_{result.get('processed', 0)}",
        'processed': result.get('processed', 0),
        'failed': result.get('failed', 0),
        'warnings': result.get('warnings', []),
    }


@router.get('/overview')
def overview(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    del current_user
    return get_assets_overview(db)
