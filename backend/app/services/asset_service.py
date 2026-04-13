from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.ids import ensure_uuid_list
from app.models import Address, AddressStatus, AssetSnapshot, AssetType
from app.services.tron_service import TronService


def _upsert_snapshot(db: Session, address_id, asset: AssetType, balance_raw: int, decimals: int):
    row = db.scalar(
        select(AssetSnapshot).where(
            AssetSnapshot.address_id == address_id,
            AssetSnapshot.asset == asset,
        )
    )
    balance_dec = balance_raw / (10**decimals)
    if row:
        row.balance_raw = balance_raw
        row.balance_dec = balance_dec
        row.updated_at = datetime.now(timezone.utc)
    else:
        db.add(
            AssetSnapshot(
                address_id=address_id,
                asset=asset,
                balance_raw=balance_raw,
                balance_dec=balance_dec,
            )
        )


def sync_assets(db: Session, address_ids: list[str] | None = None) -> dict:
    tron = TronService()

    query = select(Address).where(Address.status == AddressStatus.ACTIVE)
    if address_ids:
        query = query.where(Address.id.in_(ensure_uuid_list(address_ids)))

    addresses = db.scalars(query).all()
    processed = 0
    failed = 0
    warnings: list[dict] = []

    for addr in addresses:
        got_any = False

        try:
            resource = tron.get_account_resources(addr.address_base58)
            addr.energy_balance = int(resource.get('energy_balance') or 0)
            addr.bandwidth_balance = int(resource.get('bandwidth_balance') or 0)
            got_any = True
        except Exception as exc:
            warnings.append({'address': addr.address_base58, 'asset': 'RESOURCE', 'error': str(exc)[:200]})

        try:
            trx_raw = tron.get_trx_balance_sun(addr.address_base58)
            _upsert_snapshot(db, addr.id, AssetType.TRX, trx_raw, 6)
            got_any = True
        except Exception as exc:
            warnings.append({'address': addr.address_base58, 'asset': AssetType.TRX.value, 'error': str(exc)[:200]})

        try:
            usdt_raw = tron.get_usdt_balance_raw(addr.address_base58)
            _upsert_snapshot(db, addr.id, AssetType.USDT_TRC20, usdt_raw, 6)
            got_any = True
        except Exception as exc:
            warnings.append({'address': addr.address_base58, 'asset': AssetType.USDT_TRC20.value, 'error': str(exc)[:200]})

        if got_any:
            addr.last_scanned_at = datetime.now(timezone.utc)
            processed += 1
        else:
            failed += 1

    db.commit()
    return {'processed': processed, 'failed': failed, 'warnings': warnings}


def get_assets_overview(db: Session) -> dict:
    trx_rows = db.scalars(select(AssetSnapshot).where(AssetSnapshot.asset == AssetType.TRX)).all()
    usdt_rows = db.scalars(select(AssetSnapshot).where(AssetSnapshot.asset == AssetType.USDT_TRC20)).all()

    trx_total_raw = sum(int(x.balance_raw) for x in trx_rows)
    usdt_total_raw = sum(int(x.balance_raw) for x in usdt_rows)

    return {
        'total_addresses': len({str(x.address_id) for x in trx_rows + usdt_rows}),
        'trx_total_dec': f'{trx_total_raw / 1_000_000:.6f}',
        'usdt_total_dec': f'{usdt_total_raw / 1_000_000:.6f}',
        'non_zero_trx_addresses': sum(1 for x in trx_rows if int(x.balance_raw) > 0),
        'non_zero_usdt_addresses': sum(1 for x in usdt_rows if int(x.balance_raw) > 0),
        'updated_at': datetime.now(timezone.utc).isoformat(),
    }
