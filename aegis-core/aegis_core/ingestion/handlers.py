import abc
import csv
import io
from pathlib import Path
from typing import Any, Dict, List
from pypdf import PdfReader

class BaseIngestor(abc.ABC):
    """Abstract base class for data ingestors."""
    
    @abc.abstractmethod
    def can_handle(self, file_path: Path) -> bool:
        """Returns True if this ingestor can handle the file type."""
        pass

    @abc.abstractmethod
    def ingest(self, file_path: Path) -> Dict[str, Any]:
        """
        Reads the file and returns a dictionary with:
        - content: The raw text or structured data
        - metadata: Extracted metadata (e.g., page count, headers)
        """
        pass

class TextIngestor(BaseIngestor):
    def can_handle(self, file_path: Path) -> bool:
        return file_path.suffix.lower() == ".txt"

    def ingest(self, file_path: Path) -> Dict[str, Any]:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return {
            "content": content,
            "metadata": {"type": "text", "size": len(content)}
        }

class CSVIngestor(BaseIngestor):
    def can_handle(self, file_path: Path) -> bool:
        return file_path.suffix.lower() == ".csv"

    def ingest(self, file_path: Path) -> Dict[str, Any]:
        rows = []
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames or []
            for row in reader:
                rows.append(row)
        
        return {
            "content": rows, # List of dicts
            "metadata": {
                "type": "csv",
                "row_count": len(rows),
                "columns": fieldnames
            }
        }

class PDFIngestor(BaseIngestor):
    def can_handle(self, file_path: Path) -> bool:
        return file_path.suffix.lower() == ".pdf"

    def ingest(self, file_path: Path) -> Dict[str, Any]:
        reader = PdfReader(str(file_path))
        text_content = []
        for page in reader.pages:
            text_content.append(page.extract_text())
        
        full_text = "\n".join(text_content)
        return {
            "content": full_text,
            "metadata": {
                "type": "pdf",
                "page_count": len(reader.pages)
            }
        }

class IngestionManager:
    """Factory to select the right ingestor."""
    def __init__(self):
        self.ingestors = [TextIngestor(), CSVIngestor(), PDFIngestor()]

    def ingest_file(self, file_path: Path) -> Dict[str, Any]:
        for ingestor in self.ingestors:
            if ingestor.can_handle(file_path):
                return ingestor.ingest(file_path)
        
        raise ValueError(f"No ingestor found for file: {file_path.name}")
