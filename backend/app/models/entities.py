import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class UserRole(str, enum.Enum):
    ADMIN = 'ADMIN'


class AddressStatus(str, enum.Enum):
    ACTIVE = 'ACTIVE'
    FROZEN = 'FROZEN'
    ARCHIVED = 'ARCHIVED'


class AssetType(str, enum.Enum):
    TRX = 'TRX'
    USDT_TRC20 = 'USDT_TRC20'


class JobStatus(str, enum.Enum):
    CREATED = 'CREATED'
    SCANNING = 'SCANNING'
    PLANNED = 'PLANNED'
    FUNDING_TRX = 'FUNDING_TRX'
    SWEEPING_USDT = 'SWEEPING_USDT'
    SWEEPING_TRX = 'SWEEPING_TRX'
    RECONCILING = 'RECONCILING'
    SUCCESS = 'SUCCESS'
    PARTIAL_FAILED = 'PARTIAL_FAILED'
    FAILED = 'FAILED'
    CANCELED = 'CANCELED'


class ItemStatus(str, enum.Enum):
    PENDING = 'PENDING'
    SKIPPED = 'SKIPPED'
    PROCESSING = 'PROCESSING'
    SUCCESS = 'SUCCESS'
    FAILED = 'FAILED'


class TxStatus(str, enum.Enum):
    PENDING = 'PENDING'
    CONFIRMED = 'CONFIRMED'
    FAILED = 'FAILED'


class Wallet(Base):
    __tablename__ = 'wallets'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    target_address_base58: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    remark: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    addresses: Mapped[list['Address']] = relationship('Address', back_populates='wallet')


class User(Base):
    __tablename__ = 'users'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False, default=UserRole.ADMIN)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class Address(Base):
    __tablename__ = 'addresses'
    __table_args__ = (UniqueConstraint('wallet_id', 'addr_index', name='uq_wallet_index'),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    wallet_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('wallets.id'), nullable=False)
    addr_index: Mapped[int] = mapped_column(Integer, nullable=False)
    address_base58: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    address_hex: Mapped[str] = mapped_column(String(42), nullable=False, unique=True)
    status: Mapped[AddressStatus] = mapped_column(Enum(AddressStatus), nullable=False, default=AddressStatus.ACTIVE)
    tag: Mapped[str | None] = mapped_column(String(64), nullable=True)
    remark: Mapped[str | None] = mapped_column(String(255), nullable=True)
    energy_balance: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    bandwidth_balance: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_scanned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    wallet: Mapped['Wallet'] = relationship('Wallet', back_populates='addresses')
    key_encrypted: Mapped['KeyEncrypted'] = relationship('KeyEncrypted', back_populates='address', uselist=False)


class KeyEncrypted(Base):
    __tablename__ = 'keys_encrypted'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    address_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('addresses.id'), nullable=False, unique=True)
    encrypted_private_key: Mapped[str] = mapped_column(Text, nullable=False)
    iv: Mapped[str] = mapped_column(String(64), nullable=False)
    auth_tag: Mapped[str] = mapped_column(String(64), nullable=False)
    algorithm: Mapped[str] = mapped_column(String(32), nullable=False, default='AES-256-GCM')
    key_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    key_fingerprint: Mapped[str | None] = mapped_column(String(128), nullable=True)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    address: Mapped['Address'] = relationship('Address', back_populates='key_encrypted')


class AssetSnapshot(Base):
    __tablename__ = 'assets_snapshot'
    __table_args__ = (UniqueConstraint('address_id', 'asset', name='uq_asset_snapshot'),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    address_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('addresses.id'), nullable=False)
    asset: Mapped[AssetType] = mapped_column(Enum(AssetType), nullable=False)
    balance_raw: Mapped[int] = mapped_column(Numeric(38, 0), nullable=False, default=0)
    balance_dec: Mapped[float] = mapped_column(Numeric(38, 6), nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class SweepJob(Base):
    __tablename__ = 'sweep_jobs'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_no: Mapped[int | None] = mapped_column(Integer, nullable=True, unique=True)
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus), nullable=False, default=JobStatus.CREATED)
    target_address_base58: Mapped[str] = mapped_column(String(64), nullable=False)
    asset_list: Mapped[str] = mapped_column(Text, nullable=False)
    min_trx_raw: Mapped[int] = mapped_column(Numeric(38, 0), nullable=False, default=0)
    min_usdt_raw: Mapped[int] = mapped_column(Numeric(38, 0), nullable=False, default=0)
    reserve_trx_raw: Mapped[int] = mapped_column(Numeric(38, 0), nullable=False, default=0)
    planned_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    success_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skipped_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    idem_key: Mapped[str | None] = mapped_column(String(128), nullable=True, unique=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class SweepJobItem(Base):
    __tablename__ = 'sweep_job_items'
    __table_args__ = (UniqueConstraint('job_id', 'address_id', 'asset', name='uq_job_item'),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('sweep_jobs.id'), nullable=False)
    address_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('addresses.id'), nullable=False)
    asset: Mapped[AssetType] = mapped_column(Enum(AssetType), nullable=False)
    status: Mapped[ItemStatus] = mapped_column(Enum(ItemStatus), nullable=False, default=ItemStatus.PENDING)
    plan_amount_raw: Mapped[int] = mapped_column(Numeric(38, 0), nullable=False, default=0)
    actual_amount_raw: Mapped[int] = mapped_column(Numeric(38, 0), nullable=False, default=0)
    fee_trx_raw: Mapped[int] = mapped_column(Numeric(38, 0), nullable=False, default=0)
    topup_trx_raw: Mapped[int] = mapped_column(Numeric(38, 0), nullable=False, default=0)
    topup_txid: Mapped[str | None] = mapped_column(String(128), nullable=True)
    sweep_txid: Mapped[str | None] = mapped_column(String(128), nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fail_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class TxRecord(Base):
    __tablename__ = 'tx_records'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    txid: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    asset: Mapped[AssetType] = mapped_column(Enum(AssetType), nullable=False)
    from_address_base58: Mapped[str] = mapped_column(String(64), nullable=False)
    to_address_base58: Mapped[str] = mapped_column(String(64), nullable=False)
    amount_raw: Mapped[int] = mapped_column(Numeric(38, 0), nullable=False)
    fee_trx_raw: Mapped[int] = mapped_column(Numeric(38, 0), nullable=False, default=0)
    block_num: Mapped[int | None] = mapped_column(Integer, nullable=True)
    confirmations: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[TxStatus] = mapped_column(Enum(TxStatus), nullable=False, default=TxStatus.PENDING)
    raw_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    related_job_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('sweep_jobs.id'), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class AuditLog(Base):
    __tablename__ = 'audit_logs'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    target_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    detail: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class SystemSetting(Base):
    __tablename__ = 'system_settings'

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


Index('idx_addresses_wallet_id', Address.wallet_id)
Index('idx_addresses_status', Address.status)
Index('idx_assets_snapshot_asset', AssetSnapshot.asset)
Index('idx_assets_snapshot_updated_at', AssetSnapshot.updated_at)
Index('idx_sweep_jobs_status', SweepJob.status)
Index('idx_sweep_jobs_created_at', SweepJob.created_at)
Index('idx_sweep_job_items_job_id', SweepJobItem.job_id)
Index('idx_sweep_job_items_status', SweepJobItem.status)
Index('idx_tx_records_status', TxRecord.status)
Index('idx_tx_records_created_at', TxRecord.created_at)
Index('idx_audit_logs_actor_time', AuditLog.actor_user_id, AuditLog.created_at)
Index('idx_audit_logs_action_time', AuditLog.action, AuditLog.created_at)
