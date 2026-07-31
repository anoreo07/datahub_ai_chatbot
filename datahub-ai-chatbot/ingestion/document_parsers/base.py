"""Base document parser interface."""
from abc import ABC, abstractmethod


class DocumentParser(ABC):
    @abstractmethod
    async def parse(self, content: bytes, filename: str = "") -> str:
        ...

    @abstractmethod
    def supports(self, filename: str) -> bool:
        ...
