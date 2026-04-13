from datetime import datetime, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.ids import ensure_uuid
from app.models import (
    Address,
    AddressStatus,
    AssetSnapshot,
    AssetType,
    ItemStatus,
    JobStatus,
    SweepJob,
    SweepJobItem,
    TxRecord,
)
from app.services.queue_service import get_queue


def _dispatch_job(job_id: str) -> None:
    settings = get_settings()
    if settings.job_execution_mode.lower() == 'inline':
        from app.tasks.sweep_tasks import run_sweep_job

        run_sweep_job(job_id)
        return

    queue = get_queue()
    queue.enqueue('app.tasks.sweep_tasks.run_sweep_job', job_id, job_timeout=3600)


def _load_snapshots_for_addresses(db: Session, address_ids: list) -> dict:
    rows = db.scalars(select(AssetSnapshot).where(AssetSnapshot.address_id.in_(address_ids))).all()
    m: dict = {}
    for row in rows:
        key = str(row.address_id)
        m.setdefault(key, {})[row.asset.value] = int(row.balance_raw)
    return m


def preview_sweep(
    db: Session,
    *,
    target_address_base58: str,
    assets: list[str],
    min_trx_raw: int,
    min_usdt_raw: int,
    reserve_trx_raw: int,
    reserve_usdt_raw: int = 0,
    status: str = 'ACTIVE',
    tag_prefix: str | None = None,
) -> dict:
    settings = get_settings()

    query = select(Address).where(Address.status == AddressStatus(status))
    if tag_prefix:
        query = query.where(Address.tag.like(f'{tag_prefix}%'))

    addresses = db.scalars(query).all()
    if not addresses:
        return {
            'plan_digest': 'empty',
            'summary': {
                'candidate_addresses': 0,
                'trx_collect_raw': '0',
                'usdt_collect_raw': '0',
                'estimated_fee_trx_raw': '0',
                'need_topup_count': 0,
                'need_topup_trx_raw': '0',
            },
            'expires_in_sec': 300,
        }

    snapshots = _load_snapshots_for_addresses(db, [x.id for x in addresses])

    trx_collect_raw = 0
    usdt_collect_raw = 0
    need_topup_count = 0
    need_topup_trx_raw = 0
    estimated_fee_trx_raw = 0

    for addr in addresses:
        data = snapshots.get(str(addr.id), {})
        trx_raw = int(data.get('TRX', 0))
        usdt_raw = int(data.get('USDT_TRC20', 0))

        if 'USDT_TRC20' in assets:
            collect_usdt = max(0, usdt_raw - reserve_usdt_raw)
            if collect_usdt >= min_usdt_raw and collect_usdt > 0:
                usdt_collect_raw += collect_usdt
                estimated_fee_trx_raw += settings.default_usdt_fee_limit_sun
                if trx_raw < reserve_trx_raw:
                    need_topup_count += 1
                    need_topup_trx_raw += reserve_trx_raw - trx_raw

        if 'TRX' in assets and trx_raw > reserve_trx_raw + min_trx_raw:
            trx_collect_raw += trx_raw - reserve_trx_raw

    digest_raw = (
        f'{target_address_base58}|{assets}|{min_trx_raw}|{min_usdt_raw}|{reserve_trx_raw}|{reserve_usdt_raw}|'
        f'{trx_collect_raw}|{usdt_collect_raw}|{need_topup_count}'
    )

    import hashlib

    plan_digest = hashlib.sha256(digest_raw.encode('utf-8')).hexdigest()

    return {
        'plan_digest': plan_digest,
        'summary': {
            'candidate_addresses': len(addresses),
            'trx_collect_raw': str(trx_collect_raw),
            'usdt_collect_raw': str(usdt_collect_raw),
            'estimated_fee_trx_raw': str(estimated_fee_trx_raw),
            'need_topup_count': need_topup_count,
            'need_topup_trx_raw': str(need_topup_trx_raw),
        },
        'expires_in_sec': 300,
    }


def create_sweep_job(
    db: Session,
    *,
    created_by,
    target_address_base58: str,
    assets: list[str],
    min_trx_raw: int,
    min_usdt_raw: int,
    reserve_trx_raw: int,
    reserve_usdt_raw: int = 0,
    idem_key: str | None,
) -> SweepJob:
    exists = None
    if idem_key:
        exists = db.scalar(select(SweepJob).where(SweepJob.idem_key == idem_key))
    if exists:
        return exists

    max_job_no = db.scalar(select(func.max(SweepJob.job_no)))
    job_no = 1 if max_job_no is None else int(max_job_no) + 1

    addresses = db.scalars(select(Address).where(Address.status == AddressStatus.ACTIVE)).all()
    snapshots = _load_snapshots_for_addresses(db, [x.id for x in addresses])

    job = SweepJob(
        job_no=job_no,
        status=JobStatus.CREATED,
        target_address_base58=target_address_base58,
        asset_list=','.join(assets),
        min_trx_raw=min_trx_raw,
        min_usdt_raw=min_usdt_raw,
        reserve_trx_raw=reserve_trx_raw,
        created_by=created_by,
        idem_key=idem_key,
        started_at=None,
        ended_at=None,
    )
    db.add(job)
    db.flush()

    planned = 0
    selected_assets = set(assets)

    for addr in addresses:
        data = snapshots.get(str(addr.id), {})
        trx_raw = int(data.get('TRX', 0))
        usdt_raw = int(data.get('USDT_TRC20', 0))

        if 'USDT_TRC20' in selected_assets:
            usdt_amount = max(0, usdt_raw - reserve_usdt_raw)
            usdt_skip_reason = None
            if usdt_amount <= 0:
                usdt_skip_reason = 'USDT_AFTER_RESERVE_ZERO'
            elif usdt_amount < min_usdt_raw:
                usdt_skip_reason = 'USDT_BELOW_MIN'

            if usdt_skip_reason:
                db.add(
                    SweepJobItem(
                        job_id=job.id,
                        address_id=addr.id,
                        asset=AssetType.USDT_TRC20,
                        status=ItemStatus.SKIPPED,
                        plan_amount_raw=0,
                        fail_reason=usdt_skip_reason,
                    )
                )
            else:
                db.add(
                    SweepJobItem(
                        job_id=job.id,
                        address_id=addr.id,
                        asset=AssetType.USDT_TRC20,
                        status=ItemStatus.PENDING,
                        plan_amount_raw=usdt_amount,
                    )
                )
                planned += 1

        if 'TRX' in selected_assets:
            trx_amount = trx_raw - reserve_trx_raw
            trx_skip_reason = None
            if trx_amount <= 0:
                trx_skip_reason = 'TRX_AFTER_RESERVE_ZERO'
            elif trx_amount < min_trx_raw:
                trx_skip_reason = 'TRX_BELOW_MIN'

            if trx_skip_reason:
                db.add(
                    SweepJobItem(
                        job_id=job.id,
                        address_id=addr.id,
                        asset=AssetType.TRX,
                        status=ItemStatus.SKIPPED,
                        plan_amount_raw=0,
                        fail_reason=trx_skip_reason,
                    )
                )
            else:
                db.add(
                    SweepJobItem(
                        job_id=job.id,
                        address_id=addr.id,
                        asset=AssetType.TRX,
                        status=ItemStatus.PENDING,
                        plan_amount_raw=trx_amount,
                    )
                )
                planned += 1

    job.planned_count = planned
    if planned == 0:
        job.error_message = 'NO_ELIGIBLE_ITEMS'
    db.commit()

    _dispatch_job(str(job.id))

    return job


def list_jobs(db: Session, status: str | None, page: int, page_size: int):
    query = select(SweepJob).order_by(SweepJob.created_at.desc())
    if status:
        query = query.where(SweepJob.status == JobStatus(status))

    total = len(db.scalars(query).all())
    items = db.scalars(query.offset((page - 1) * page_size).limit(page_size)).all()
    return total, items


def get_job_detail(db: Session, job_id):
    job_uuid = ensure_uuid(job_id)
    job = db.get(SweepJob, job_uuid)
    if not job:
        return None, []
    all_items = db.scalars(select(SweepJobItem).where(SweepJobItem.job_id == job_uuid)).all()
    failed = [x for x in all_items if x.status == ItemStatus.FAILED]
    return job, all_items, failed


def retry_failed_items(db: Session, job_id, max_items: int):
    job_uuid = ensure_uuid(job_id)
    job = db.get(SweepJob, job_uuid)
    if not job:
        raise ValueError('job not found')

    failed_items = db.scalars(
        select(SweepJobItem)
        .where(SweepJobItem.job_id == job_uuid, SweepJobItem.status == ItemStatus.FAILED)
        .limit(max_items)
    ).all()

    for item in failed_items:
        item.status = ItemStatus.PENDING
        item.fail_reason = None

    job.status = JobStatus.CREATED
    job.error_message = None
    db.commit()

    _dispatch_job(str(job.id))

    return len(failed_items)


def clear_job_history(db: Session) -> dict:
    job_ids = db.scalars(select(SweepJob.id)).all()
    if not job_ids:
        return {'jobs': 0, 'items': 0, 'tx_records': 0}

    items_res = db.execute(delete(SweepJobItem).where(SweepJobItem.job_id.in_(job_ids)))
    tx_res = db.execute(delete(TxRecord).where(TxRecord.related_job_id.in_(job_ids)))
    jobs_res = db.execute(delete(SweepJob).where(SweepJob.id.in_(job_ids)))

    items_count = max(0, int(items_res.rowcount or 0))
    tx_count = max(0, int(tx_res.rowcount or 0))
    jobs_count = max(0, int(jobs_res.rowcount or 0))

    return {'jobs': jobs_count, 'items': items_count, 'tx_records': tx_count}
