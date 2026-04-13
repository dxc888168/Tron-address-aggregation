from __future__ import annotations

from dataclasses import dataclass

from tronpy import Tron
from tronpy.keys import PrivateKey, to_hex_address
from tronpy.providers import HTTPProvider

from app.core.config import get_settings


@dataclass
class TransferResult:
    txid: str
    raw: dict | None = None


class TronService:
    def __init__(self):
        settings = get_settings()
        if settings.trongrid_api_key:
            provider = HTTPProvider(endpoint_uri='https://api.trongrid.io', api_key=settings.trongrid_api_key)
            self.client = Tron(provider=provider)
        else:
            self.client = Tron(network=settings.tron_network)

        self.settings = settings

    def generate_account(self) -> dict:
        pk = PrivateKey.random()
        base58 = pk.public_key.to_base58check_address()
        return {
            'address_base58': base58,
            'address_hex': to_hex_address(base58),
            'private_key_hex': pk.hex(),
        }

    @staticmethod
    def load_private_key(private_key_hex: str) -> PrivateKey:
        return PrivateKey(bytes.fromhex(private_key_hex))

    def get_trx_balance_sun(self, address: str) -> int:
        trx = self.client.get_account_balance(address)
        return int(trx * 1_000_000)

    def get_usdt_balance_raw(self, address: str) -> int:
        contract = self.client.get_contract(self.settings.usdt_contract)
        value = contract.functions.balanceOf(address)
        return int(value)

    def get_account_resources(self, address: str) -> dict[str, int]:
        resource = self.client.get_account_resource(address) or {}

        free_net_limit = int(resource.get('freeNetLimit') or 0)
        free_net_used = int(resource.get('freeNetUsed') or 0)
        net_limit = int(resource.get('NetLimit') or resource.get('netLimit') or 0)
        net_used = int(resource.get('NetUsed') or resource.get('netUsed') or 0)
        bandwidth_balance = max(0, (free_net_limit - free_net_used) + (net_limit - net_used))

        energy_limit = int(resource.get('EnergyLimit') or resource.get('energyLimit') or 0)
        energy_used = int(resource.get('EnergyUsed') or resource.get('energyUsed') or 0)
        energy_balance = max(0, energy_limit - energy_used)

        return {
            'energy_balance': energy_balance,
            'bandwidth_balance': bandwidth_balance,
        }

    def transfer_trx(self, from_address: str, to_address: str, amount_sun: int, private_key_hex: str) -> TransferResult:
        private_key = self.load_private_key(private_key_hex)
        txn = self.client.trx.transfer(from_address, to_address, int(amount_sun)).build()
        signed = txn.sign(private_key)
        ret = signed.broadcast()
        raw = None
        try:
            raw = ret.wait()
        except Exception:
            raw = None
        return TransferResult(txid=ret.txid, raw=raw)

    def transfer_usdt(
        self,
        from_address: str,
        to_address: str,
        amount_raw: int,
        private_key_hex: str,
        fee_limit_sun: int | None = None,
    ) -> TransferResult:
        private_key = self.load_private_key(private_key_hex)
        fee_limit = fee_limit_sun or self.settings.default_usdt_fee_limit_sun
        contract = self.client.get_contract(self.settings.usdt_contract)
        txn = (
            contract.functions.transfer(to_address, int(amount_raw))
            .with_owner(from_address)
            .fee_limit(int(fee_limit))
            .build()
        )
        signed = txn.sign(private_key)
        ret = signed.broadcast()
        raw = None
        try:
            raw = ret.wait()
        except Exception:
            raw = None
        return TransferResult(txid=ret.txid, raw=raw)

    def get_tx_info(self, txid: str) -> dict:
        return self.client.get_transaction_info(txid)
