from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import Address, SystemSetting, User
from app.services.audit_service import write_audit

router = APIRouter(prefix='/system', tags=['system'])


class TopupSourceRequest(BaseModel):
    address_base58: str


@router.get('/topup-source')
def get_topup_source(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    del current_user
    row = db.get(SystemSetting, 'topup_source_address')
    return {'address_base58': row.value.get('address') if row else None}


@router.post('/topup-source')
def set_topup_source(
    payload: TopupSourceRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    address = db.scalar(select(Address).where(Address.address_base58 == payload.address_base58))
    if not address:
        raise HTTPException(status_code=400, detail='address is not managed by this system')

    row = db.get(SystemSetting, 'topup_source_address')
    if row:
        row.value = {'address': payload.address_base58}
    else:
        db.add(SystemSetting(key='topup_source_address', value={'address': payload.address_base58}))

    write_audit(
        db,
        actor_user_id=current_user.id,
        action='SET_TOPUP_SOURCE',
        target_type='SYSTEM_SETTING',
        target_id='topup_source_address',
        detail={'address_base58': payload.address_base58},
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get('user-agent'),
    )
    db.commit()
    return {'ok': True, 'address_base58': payload.address_base58}
