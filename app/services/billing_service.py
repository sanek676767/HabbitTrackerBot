from abc import ABC, abstractmethod
from decimal import Decimal


class PaymentProvider(ABC):
    @abstractmethod
    async def create_payment(self, user_id: int, amount: Decimal, currency: str) -> str:
        raise NotImplementedError

    @abstractmethod
    async def get_payment_status(self, provider_payment_id: str) -> str:
        raise NotImplementedError


class BillingService:
    def __init__(self, provider: PaymentProvider) -> None:
        self._provider = provider

    async def create_payment(self, user_id: int, amount: Decimal, currency: str) -> str:
        return await self._provider.create_payment(user_id, amount, currency)

    async def get_payment_status(self, provider_payment_id: str) -> str:
        return await self._provider.get_payment_status(provider_payment_id)
