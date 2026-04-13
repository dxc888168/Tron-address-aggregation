from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session
from tronpy.keys import is_base58check_address, to_hex_address

from app.core.ids import ensure_uuid, ensure_uuid_list
from app.models import Address, AddressStatus, AssetSnapshot, KeyEncrypted, SweepJobItem, Wallet
from app.services.crypto_service import decrypt_secret
from app.services.crypto_service import encrypt_secret
from app.services.tron_service import TronService


def get_or_create_default_wallet(db: Session) -> Wallet:
    wallet = db.scalar(select(Wallet).where(Wallet.is_default.is_(True)))
    if wallet:
        return wallet

    wallet = Wallet(name='Default Wallet', type='MASTER', is_default=True)
    db.add(wallet)
    db.flush()
    return wallet


def batch_generate_addresses(
    db: Session,
    *,
    wallet_id,
    count: int,
    start_index: int | None,
    tag_prefix: str | None,
) -> list[Address]:
    if count <= 0:
        raise ValueError('count must be > 0')

    wallet_uuid = ensure_uuid(wallet_id)
    wallet = db.get(Wallet, wallet_uuid)
    if not wallet:
        raise ValueError('wallet not found')

    if start_index is None:
        active_count = db.scalar(
            select(func.count(Address.id)).where(Address.wallet_id == wallet_uuid, Address.status == AddressStatus.ACTIVE)
        )
        if not active_count:
            archived_ids = db.scalars(
                select(Address.id).where(Address.wallet_id == wallet_uuid, Address.status == AddressStatus.ARCHIVED)
            ).all()
            if archived_ids:
                _delete_addresses_with_dependencies(db, archived_ids)

        used_idx = set(db.scalars(select(Address.addr_index).where(Address.wallet_id == wallet_uuid)).all())
        planned_indexes: list[int] = []
        idx = 1
        while len(planned_indexes) < count:
            if idx not in used_idx:
                planned_indexes.append(idx)
            idx += 1
    else:
        planned_indexes = [start_index + offset for offset in range(count)]

    tron = TronService()
    created: list[Address] = []

    for idx in planned_indexes:
        exists = db.scalar(
            select(Address.id).where(Address.wallet_id == wallet_uuid, Address.addr_index == idx)
        )
        if exists:
            continue

        account = tron.generate_account()
        addr = Address(
            wallet_id=wallet_uuid,
            addr_index=idx,
            address_base58=account['address_base58'],
            address_hex=account['address_hex'],
            status=AddressStatus.ACTIVE,
            tag=f"{tag_prefix}{idx}" if tag_prefix else None,
        )
        db.add(addr)
        db.flush()

        encrypted = encrypt_secret(account['private_key_hex'])
        db.add(
            KeyEncrypted(
                address_id=addr.id,
                encrypted_private_key=encrypted['encrypted_private_key'],
                iv=encrypted['iv'],
                auth_tag=encrypted['auth_tag'],
                key_fingerprint=encrypted['key_fingerprint'],
                checksum_sha256=encrypted['checksum_sha256'],
            )
        )
        created.append(addr)

    db.commit()
    return created


def export_private_keys(
    db: Session,
    *,
    status: str = 'ACTIVE',
    tag: str | None = None,
    address_ids: list[str] | None = None,
) -> list[dict]:
    try:
        status_enum = AddressStatus(status)
    except ValueError as exc:
        raise ValueError('invalid status') from exc

    query = (
        select(Address, KeyEncrypted)
        .join(KeyEncrypted, KeyEncrypted.address_id == Address.id)
        .where(Address.status == status_enum)
        .order_by(Address.addr_index.asc())
    )

    if tag:
        query = query.where(Address.tag.like(f'%{tag}%'))

    if address_ids:
        query = query.where(Address.id.in_(ensure_uuid_list(address_ids)))

    rows = db.execute(query).all()
    result: list[dict] = []
    for addr, key_row in rows:
        private_key_hex = decrypt_secret(key_row.encrypted_private_key, key_row.iv, key_row.auth_tag)
        result.append(
            {
                'id': str(addr.id),
                'addr_index': addr.addr_index,
                'address_base58': addr.address_base58,
                'address_hex': addr.address_hex,
                'status': addr.status.value,
                'tag': addr.tag,
                'private_key_hex': private_key_hex,
            }
        )
    return result


def update_address_tag(db: Session, *, address_id: str, tag: str | None) -> Address:
    addr_uuid = ensure_uuid(address_id)
    row = db.get(Address, addr_uuid)
    if not row:
        raise ValueError('address not found')

    row.tag = tag.strip() if isinstance(tag, str) and tag.strip() else None
    return row


def _delete_addresses_with_dependencies(db: Session, address_uuids: list) -> int:
    if not address_uuids:
        return 0

    db.execute(delete(SweepJobItem).where(SweepJobItem.address_id.in_(address_uuids)))
    db.execute(delete(AssetSnapshot).where(AssetSnapshot.address_id.in_(address_uuids)))
    db.execute(delete(KeyEncrypted).where(KeyEncrypted.address_id.in_(address_uuids)))
    result = db.execute(delete(Address).where(Address.id.in_(address_uuids)))
    rowcount = int(result.rowcount or 0)
    return max(0, rowcount)


def batch_delete_addresses(db: Session, *, address_ids: list[str]) -> int:
    if not address_ids:
        return 0

    addr_uuids = ensure_uuid_list(address_ids)
    return _delete_addresses_with_dependencies(db, addr_uuids)


def import_address_private_pairs(
    db: Session,
    *,
    wallet_id,
    pairs: list[str],
    tag_prefix: str | None = None,
) -> dict:
    wallet_uuid = ensure_uuid(wallet_id)
    wallet = db.get(Wallet, wallet_uuid)
    if not wallet:
        raise ValueError('wallet not found')

    used_idx = set(db.scalars(select(Address.addr_index).where(Address.wallet_id == wallet_uuid)).all())
    next_idx = 1

    def alloc_idx() -> int:
        nonlocal next_idx
        while next_idx in used_idx:
            next_idx += 1
        out = next_idx
        used_idx.add(out)
        next_idx += 1
        return out

    imported_rows: list[Address] = []
    errors: list[dict] = []
    skipped_count = 0
    seen_input_addresses: set[str] = set()

    for line_no, raw in enumerate(pairs, start=1):
        line = (raw or '').strip()
        if not line:
            continue

        address_hint = None
        private_key_hex = line
        if '-' in line:
            left, right = line.split('-', 1)
            address_hint = left.strip() or None
            private_key_hex = right.strip()

        private_key_hex = private_key_hex.strip().lower()
        if not private_key_hex:
            errors.append({'line': line_no, 'raw': line, 'reason': 'EMPTY_PRIVATE_KEY'})
            continue

        if address_hint and not is_base58check_address(address_hint):
            errors.append({'line': line_no, 'raw': line, 'reason': 'INVALID_TRON_ADDRESS_HINT'})
            continue

        if len(private_key_hex) != 64:
            errors.append({'line': line_no, 'raw': line, 'reason': 'INVALID_PRIVATE_KEY_LENGTH'})
            continue

        try:
            int(private_key_hex, 16)
        except ValueError:
            errors.append({'line': line_no, 'raw': line, 'reason': 'INVALID_PRIVATE_KEY_HEX'})
            continue

        try:
            derived_address = TronService.load_private_key(private_key_hex).public_key.to_base58check_address()
        except Exception:
            errors.append({'line': line_no, 'raw': line, 'reason': 'PRIVATE_KEY_PARSE_FAILED'})
            continue

        if address_hint and derived_address != address_hint:
            errors.append({'line': line_no, 'raw': line, 'reason': 'ADDRESS_PRIVATE_KEY_MISMATCH'})
            continue

        address_base58 = derived_address

        if address_base58 in seen_input_addresses:
            skipped_count += 1
            continue
        seen_input_addresses.add(address_base58)

        exists = db.scalar(select(Address.id).where(Address.address_base58 == address_base58))
        if exists:
            skipped_count += 1
            continue

        address_hex = to_hex_address(address_base58)
        exists_hex = db.scalar(select(Address.id).where(Address.address_hex == address_hex))
        if exists_hex:
            skipped_count += 1
            continue

        idx = alloc_idx()
        row = Address(
            wallet_id=wallet_uuid,
            addr_index=idx,
            address_base58=address_base58,
            address_hex=address_hex,
            status=AddressStatus.ACTIVE,
            tag=f"{tag_prefix}{idx}" if tag_prefix else None,
        )
        db.add(row)
        db.flush()

        encrypted = encrypt_secret(private_key_hex)
        db.add(
            KeyEncrypted(
                address_id=row.id,
                encrypted_private_key=encrypted['encrypted_private_key'],
                iv=encrypted['iv'],
                auth_tag=encrypted['auth_tag'],
                key_fingerprint=encrypted['key_fingerprint'],
                checksum_sha256=encrypted['checksum_sha256'],
            )
        )
        imported_rows.append(row)

    db.commit()
    return {
        'imported_count': len(imported_rows),
        'skipped_count': skipped_count,
        'error_count': len(errors),
        'errors': errors[:200],
        'sample': [{'addr_index': x.addr_index, 'address_base58': x.address_base58} for x in imported_rows[:10]],
    }
