from sqlalchemy import inspect, select, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password, verify_password
from app.models import User, Wallet


def _ensure_addresses_resource_columns(db: Session) -> None:
    bind = db.get_bind()
    inspector = inspect(bind)
    columns = {col['name'] for col in inspector.get_columns('addresses')}

    stmts: list[str] = []
    if 'energy_balance' not in columns:
        stmts.append('ALTER TABLE addresses ADD COLUMN energy_balance INTEGER NOT NULL DEFAULT 0')
    if 'bandwidth_balance' not in columns:
        stmts.append('ALTER TABLE addresses ADD COLUMN bandwidth_balance INTEGER NOT NULL DEFAULT 0')

    for stmt in stmts:
        db.execute(text(stmt))

    if stmts:
        db.commit()


def bootstrap_initial_data(db: Session):
    _ensure_addresses_resource_columns(db)
    settings = get_settings()

    user = db.scalar(select(User).where(User.username == settings.admin_username))
    if not user:
        user = User(
            username=settings.admin_username,
            password_hash=hash_password(settings.admin_password),
        )
        db.add(user)
    elif not verify_password(settings.admin_password, user.password_hash):
        # Keep local single-admin deployments easy to recover when .env password changes.
        user.password_hash = hash_password(settings.admin_password)

    default_wallet = db.scalar(select(Wallet).where(Wallet.is_default.is_(True)))
    if not default_wallet:
        db.add(Wallet(name='Default Wallet', type='MASTER', is_default=True))

    db.commit()
