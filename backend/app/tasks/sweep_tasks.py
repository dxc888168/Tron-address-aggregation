from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select

from app.core.ids import ensure_uuid
from app.db.session import SessionLocal
from app.models import (
    Address,
    AssetType,
    ItemStatus,
    JobStatus,
    KeyEncrypted,
    SweepJob,
    SweepJobItem,
    SystemSetting,
    TxRecord,
    TxStatus,
)
from app.services.crypto_service import decrypt_secret
from app.services.tron_service import TronService


def _now():
    return datetime.now(timezone.utc)


def _load_private_key_hex(db, address_id):
    key_row = db.scalar(select(KeyEncrypted).where(KeyEncrypted.address_id == address_id))
    if not key_row:
        raise RuntimeError('missing encrypted key row')
    return decrypt_secret(key_row.encrypted_private_key, key_row.iv, key_row.auth_tag)


def _record_tx(db, *, txid: str, asset: AssetType, from_addr: str, to_addr: str, amount_raw: int, related_job_id, raw=None):
    exists = db.scalar(select(TxRecord).where(TxRecord.txid == txid))
    if exists:
        return
    db.add(
        TxRecord(
            txid=txid,
            asset=asset,
            from_address_base58=from_addr,
            to_address_base58=to_addr,
            amount_raw=amount_raw,
            status=TxStatus.PENDING,
            raw_json=raw,
            related_job_id=related_job_id,
        )
    )


def _get_topup_source(db):
    row = db.get(SystemSetting, 'topup_source_address')
    if not row:
        return None
    return row.value.get('address')


def _maybe_topup_trx(db, tron: TronService, source_addr: Address, reserve_trx_raw: int, job_id, item: SweepJobItem):
    cur_trx = tron.get_trx_balance_sun(source_addr.address_base58)
    if cur_trx >= reserve_trx_raw:
        return None

    topup_source_base58 = _get_topup_source(db)
    if not topup_source_base58:
        return 'NO_TOPUP_SOURCE_CONFIGURED'

    topup_source = db.scalar(select(Address).where(Address.address_base58 == topup_source_base58))
    if not topup_source:
        return 'TOPUP_SOURCE_NOT_MANAGED'

    need = reserve_trx_raw - cur_trx
    topup_pk = _load_private_key_hex(db, topup_source.id)

    topup_result = tron.transfer_trx(
        from_address=topup_source.address_base58,
        to_address=source_addr.address_base58,
        amount_sun=need,
        private_key_hex=topup_pk,
    )

    item.topup_trx_raw = need
    item.topup_txid = topup_result.txid

    _record_tx(
        db,
        txid=topup_result.txid,
        asset=AssetType.TRX,
        from_addr=topup_source.address_base58,
        to_addr=source_addr.address_base58,
        amount_raw=need,
        related_job_id=job_id,
        raw=topup_result.raw,
    )
    return None


def run_sweep_job(job_id: str):
    db = SessionLocal()
    tron = TronService()

    try:
        job_uuid = ensure_uuid(job_id)
        job = db.get(SweepJob, job_uuid)
        if not job:
            return

        job.status = JobStatus.SCANNING
        job.started_at = job.started_at or _now()
        db.commit()

        items = db.scalars(
            select(SweepJobItem)
            .where(SweepJobItem.job_id == job.id, SweepJobItem.status.in_([ItemStatus.PENDING, ItemStatus.FAILED]))
            .order_by(SweepJobItem.asset.desc(), SweepJobItem.created_at.asc())
        ).all()

        if not items:
            all_items = db.scalars(select(SweepJobItem).where(SweepJobItem.job_id == job.id)).all()
            job.success_count = sum(1 for x in all_items if x.status == ItemStatus.SUCCESS)
            job.failed_count = sum(1 for x in all_items if x.status == ItemStatus.FAILED)
            job.skipped_count = sum(1 for x in all_items if x.status == ItemStatus.SKIPPED)
            job.status = JobStatus.SUCCESS
            job.ended_at = _now()
            db.commit()
            return

        for item in items:
            item.status = ItemStatus.PROCESSING
            item.attempt_count = int(item.attempt_count) + 1
            db.commit()

            source_addr = db.get(Address, item.address_id)
            if not source_addr:
                item.status = ItemStatus.FAILED
                item.fail_reason = 'ADDRESS_NOT_FOUND'
                db.commit()
                continue

            try:
                pk_hex = _load_private_key_hex(db, source_addr.id)

                if item.asset == AssetType.USDT_TRC20:
                    job.status = JobStatus.SWEEPING_USDT
                    db.commit()

                    topup_reason = _maybe_topup_trx(
                        db,
                        tron,
                        source_addr,
                        int(job.reserve_trx_raw),
                        job.id,
                        item,
                    )
                    if topup_reason:
                        item.status = ItemStatus.FAILED
                        item.fail_reason = topup_reason
                        db.commit()
                        continue

                    amount_raw = int(item.plan_amount_raw)
                    if amount_raw <= 0:
                        item.status = ItemStatus.SKIPPED
                        db.commit()
                        continue

                    result = tron.transfer_usdt(
                        from_address=source_addr.address_base58,
                        to_address=job.target_address_base58,
                        amount_raw=amount_raw,
                        private_key_hex=pk_hex,
                    )
                    item.sweep_txid = result.txid
                    item.actual_amount_raw = amount_raw
                    item.status = ItemStatus.SUCCESS

                    _record_tx(
                        db,
                        txid=result.txid,
                        asset=AssetType.USDT_TRC20,
                        from_addr=source_addr.address_base58,
                        to_addr=job.target_address_base58,
                        amount_raw=amount_raw,
                        related_job_id=job.id,
                        raw=result.raw,
                    )

                elif item.asset == AssetType.TRX:
                    job.status = JobStatus.SWEEPING_TRX
                    db.commit()

                    amount_sun = int(item.plan_amount_raw)
                    if amount_sun <= 0:
                        item.status = ItemStatus.SKIPPED
                        db.commit()
                        continue

                    result = tron.transfer_trx(
                        from_address=source_addr.address_base58,
                        to_address=job.target_address_base58,
                        amount_sun=amount_sun,
                        private_key_hex=pk_hex,
                    )
                    item.sweep_txid = result.txid
                    item.actual_amount_raw = amount_sun
                    item.status = ItemStatus.SUCCESS

                    _record_tx(
                        db,
                        txid=result.txid,
                        asset=AssetType.TRX,
                        from_addr=source_addr.address_base58,
                        to_addr=job.target_address_base58,
                        amount_raw=amount_sun,
                        related_job_id=job.id,
                        raw=result.raw,
                    )
                else:
                    item.status = ItemStatus.FAILED
                    item.fail_reason = 'UNSUPPORTED_ASSET'

                db.commit()
            except Exception as exc:
                item.status = ItemStatus.FAILED
                item.fail_reason = str(exc)[:500]
                db.commit()

        job.status = JobStatus.RECONCILING
        db.commit()

        all_items = db.scalars(select(SweepJobItem).where(SweepJobItem.job_id == job.id)).all()
        success_count = sum(1 for x in all_items if x.status == ItemStatus.SUCCESS)
        failed_count = sum(1 for x in all_items if x.status == ItemStatus.FAILED)
        skipped_count = sum(1 for x in all_items if x.status == ItemStatus.SKIPPED)

        job.success_count = success_count
        job.failed_count = failed_count
        job.skipped_count = skipped_count

        if failed_count == 0:
            job.status = JobStatus.SUCCESS
        elif success_count > 0:
            job.status = JobStatus.PARTIAL_FAILED
        else:
            job.status = JobStatus.FAILED

        job.ended_at = _now()
        db.commit()
    except Exception as exc:
        try:
            job_uuid = ensure_uuid(job_id)
        except Exception:
            job_uuid = None

        job = db.get(SweepJob, job_uuid) if job_uuid else None
        if job:
            job.status = JobStatus.FAILED
            job.error_message = str(exc)[:500]
            job.ended_at = _now()
            db.commit()
    finally:
        db.close()
