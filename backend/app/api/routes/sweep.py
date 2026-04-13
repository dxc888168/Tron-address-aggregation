from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from tronpy.keys import is_base58check_address

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.db.session import get_db
from app.models import Address, User
from app.services.audit_service import write_audit
from app.services.sweep_service import (
    clear_job_history,
    create_sweep_job,
    get_job_detail,
    list_jobs,
    preview_sweep,
    retry_failed_items,
)

router = APIRouter(prefix='/sweep', tags=['sweep'])


class AddressFilter(BaseModel):
    status: str = 'ACTIVE'
    tag_prefix: str | None = None


class SweepPreviewRequest(BaseModel):
    target_address_base58: str = Field(min_length=1)
    assets: list[str] = Field(default_factory=lambda: ['TRX', 'USDT_TRC20'])
    min_trx_raw: int = Field(default_factory=lambda: get_settings().default_trx_min_sweep_sun)
    min_usdt_raw: int = Field(default_factory=lambda: get_settings().default_usdt_min_sweep_raw)
    reserve_trx_raw: int = Field(default_factory=lambda: get_settings().default_trx_reserve_sun)
    reserve_usdt_raw: int = 0
    address_filter: AddressFilter = Field(default_factory=AddressFilter)


class SweepRunRequest(SweepPreviewRequest):
    plan_digest: str | None = None
    idem_key: str | None = None


class RetryRequest(BaseModel):
    only_failed: bool = True
    max_items: int = 100


@router.post('/preview')
def preview(
    payload: SweepPreviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    del current_user
    target = payload.target_address_base58.strip()
    if not target:
        raise HTTPException(status_code=400, detail='归集目标地址不能为空')
    if not is_base58check_address(target):
        raise HTTPException(status_code=400, detail='归集目标地址格式不正确')

    return preview_sweep(
        db,
        target_address_base58=target,
        assets=payload.assets,
        min_trx_raw=payload.min_trx_raw,
        min_usdt_raw=payload.min_usdt_raw,
        reserve_trx_raw=payload.reserve_trx_raw,
        reserve_usdt_raw=payload.reserve_usdt_raw,
        status=payload.address_filter.status,
        tag_prefix=payload.address_filter.tag_prefix,
    )


@router.post('/run')
def run(
    payload: SweepRunRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    target = payload.target_address_base58.strip()
    if not target:
        raise HTTPException(status_code=400, detail='归集目标地址不能为空')
    if not is_base58check_address(target):
        raise HTTPException(status_code=400, detail='归集目标地址格式不正确')

    job = create_sweep_job(
        db,
        created_by=current_user.id,
        target_address_base58=target,
        assets=payload.assets,
        min_trx_raw=payload.min_trx_raw,
        min_usdt_raw=payload.min_usdt_raw,
        reserve_trx_raw=payload.reserve_trx_raw,
        reserve_usdt_raw=payload.reserve_usdt_raw,
        idem_key=payload.idem_key,
    )

    write_audit(
        db,
        actor_user_id=current_user.id,
        action='SWEEP_RUN',
        target_type='SWEEP_JOB',
        target_id=str(job.id),
        detail={
            'assets': payload.assets,
            'target': target,
            'idem_key': payload.idem_key,
            'plan_digest': payload.plan_digest,
        },
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get('user-agent'),
    )
    db.commit()

    return {'job_id': str(job.id), 'job_no': job.job_no, 'status': job.status.value}


@router.get('/jobs')
def jobs(
    page: int = 1,
    page_size: int = 20,
    status: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    del current_user
    total, rows = list_jobs(db, status, page, page_size)
    items = [
        {
            'id': str(x.id),
            'job_no': x.job_no,
            'status': x.status.value,
            'planned_count': x.planned_count,
            'success_count': x.success_count,
            'failed_count': x.failed_count,
            'error_message': x.error_message,
            'created_at': x.created_at.isoformat() if x.created_at else None,
        }
        for x in rows
    ]
    return {'items': items, 'page': page, 'page_size': page_size, 'total': total}


@router.get('/jobs/{job_id}')
def job_detail(job_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    del current_user
    job, all_items, failed = get_job_detail(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail='job not found')

    addr_ids = [x.address_id for x in failed]
    addr_rows = db.scalars(select(Address).where(Address.id.in_(addr_ids))).all() if addr_ids else []
    addr_map = {str(x.id): x.address_base58 for x in addr_rows}

    failed_payload = [
        {
            'address_base58': addr_map.get(str(row.address_id)),
            'asset': row.asset.value,
            'fail_reason': row.fail_reason,
            'attempt_count': row.attempt_count,
        }
        for row in failed
    ]

    checked_addresses = len({str(x.address_id) for x in all_items})
    planned_items = sum(1 for x in all_items if int(x.plan_amount_raw or 0) > 0)
    planned_addresses = len({str(x.address_id) for x in all_items if int(x.plan_amount_raw or 0) > 0})
    skipped_items = sum(1 for x in all_items if x.status.value == 'SKIPPED')

    skip_reasons: dict[str, int] = {}
    for row in all_items:
        if row.status.value != 'SKIPPED':
            continue
        reason = row.fail_reason or 'SKIPPED'
        skip_reasons[reason] = skip_reasons.get(reason, 0) + 1

    return {
        'job': {
            'id': str(job.id),
            'job_no': job.job_no,
            'status': job.status.value,
            'target_address_base58': job.target_address_base58,
            'asset_list': job.asset_list,
            'planned_count': job.planned_count,
            'success_count': job.success_count,
            'failed_count': job.failed_count,
            'error_message': job.error_message,
            'started_at': job.started_at.isoformat() if job.started_at else None,
            'ended_at': job.ended_at.isoformat() if job.ended_at else None,
        },
        'summary': {
            'checked_addresses': checked_addresses,
            'planned_addresses': planned_addresses,
            'planned_items': planned_items,
            'skipped_items': skipped_items,
            'skip_reasons': skip_reasons,
        },
        'failed_items': failed_payload,
    }


@router.post('/jobs/{job_id}/retry')
def retry(
    job_id: str,
    payload: RetryRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not payload.only_failed:
        raise HTTPException(status_code=400, detail='only_failed=false is not supported in v1')

    try:
        count = retry_failed_items(db, job_id, payload.max_items)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    write_audit(
        db,
        actor_user_id=current_user.id,
        action='SWEEP_RETRY',
        target_type='SWEEP_JOB',
        target_id=job_id,
        detail={'count': count, 'max_items': payload.max_items},
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get('user-agent'),
    )
    db.commit()

    return {'accepted': True, 'job_id': job_id, 'retry_batch': 1, 'retry_count': count}


@router.post('/jobs/clear')
def clear_jobs(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = clear_job_history(db)

    write_audit(
        db,
        actor_user_id=current_user.id,
        action='SWEEP_CLEAR_HISTORY',
        target_type='SWEEP_JOB',
        target_id='all',
        detail=result,
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get('user-agent'),
    )
    db.commit()

    return {'ok': True, **result}
