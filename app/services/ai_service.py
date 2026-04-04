from abc import ABC, abstractmethod
from typing import Any


class AIProvider(ABC):
    @abstractmethod
    async def generate_text(self, prompt: str, **kwargs: Any) -> str:
        raise NotImplementedError


class AIService:
    def __init__(self, provider: AIProvider) -> None:
        self._provider = provider

    async def generate_text(self, prompt: str, **kwargs: Any) -> str:
        return await self._provider.generate_text(prompt, **kwargs)
