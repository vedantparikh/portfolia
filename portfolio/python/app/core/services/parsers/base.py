from abc import ABC, abstractmethod

from core.schemas.account_statements import ParsedData


class PDFParser(ABC):
    """Abstract base class for PDF parsers."""

    @abstractmethod
    def parse(self, pdf_content: bytes) -> ParsedData:
        """Parse PDF content and return structured data."""

