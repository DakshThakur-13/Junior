"""
PDF Processor Service
Handles PDF parsing, OCR, and chunk extraction
"""

import re
from pathlib import Path
from typing import Optional, Generator
from dataclasses import dataclass
from uuid import uuid4

from pypdf import PdfReader

from junior.core import get_logger
from junior.core.types import DocumentChunk, LegalDocument, Court, Language

logger = get_logger(__name__)

@dataclass
class PDFPage:
    """Represents a single page from a PDF"""
    page_number: int
    text: str
    paragraphs: list[str]

class PDFProcessor:
    """
    PDF Processing Service for legal documents

    Handles:
    - Text extraction from PDFs
    - Paragraph detection and numbering
    - Chunk creation for embeddings
    - Metadata extraction (case number, court, date, etc.)
    """

    # Common patterns in Indian legal documents
    PARAGRAPH_PATTERN = re.compile(r'^\s*(\d+)\.\s+', re.MULTILINE)

    # Section headings that mark semantic boundaries in Indian judgments
    # These act as natural chunk delimiters regardless of sliding-window size
    SECTION_HEADING_PATTERN = re.compile(
        r'^\s*(?:'
        r'JUDGMENT|JUDGEMENT|ORDER|HELD|FACTS|BACKGROUND|ISSUES?|QUESTIONS? OF LAW|'
        r'ARGUMENTS?|SUBMISSIONS?|CONTENTIONS?|ANALYSIS|REASONING|CONCLUSION|'
        r'RATIO|PRAYER|RELIEF|OPERATIVE PART|ACCORDINGLY|RESULT)'
        r'[:\s]*$',
        re.IGNORECASE | re.MULTILINE,
    )

    CASE_NUMBER_PATTERN = re.compile(
        r'(?:W\.P\.|Writ Petition|Criminal Appeal|Civil Appeal|SLP|'
        r'Criminal Misc\.|Bail Application|O\.A\.|Review Petition)'
        r'\s*(?:\(C\)|\(Crl\)|\(Civil\))?\s*No\.\s*\d+(?:/\d+)?(?:\s+of\s+\d{4})?',
        re.IGNORECASE
    )
    DATE_PATTERN = re.compile(
        r'(?:dated|decided on|pronounced on|judgment dated)\s*[:\s]*'
        r'(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4}|\d{1,2}\s+\w+,?\s+\d{4})',
        re.IGNORECASE
    )

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def extract_text(self, pdf_path: str | Path) -> list[PDFPage]:
        """
        Extract text from PDF file using Hybrid Pipeline (pypdf + OCR)
        """
        pdf_path = Path(pdf_path)

        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        logger.info(f"Extracting text from: {pdf_path.name}")

        pages = []
        reader = PdfReader(pdf_path)

        for i, page in enumerate(reader.pages, 1):
            # 1. Try standard extraction
            text = page.extract_text() or ""

            # 2. If text is sparse (likely scanned), try OCR
            if len(text.strip()) < 50:
                logger.info(f"Page {i} seems scanned (text len={len(text)}). Attempting OCR...")
                ocr_text = self._perform_ocr(pdf_path, page_number=i)
                if ocr_text:
                    text = ocr_text

            paragraphs = self._extract_paragraphs(text)

            pages.append(PDFPage(
                page_number=i,
                text=text,
                paragraphs=paragraphs,
            ))

        logger.info(f"Extracted {len(pages)} pages from PDF")
        return pages

    def _perform_ocr(self, pdf_path: Path, page_number: int) -> str:
        """
        Perform OCR on a specific page using available engines
        Priority: PaddleOCR (Best for Indic) > Tesseract (Standard)
        """
        try:
            from pdf2image import convert_from_path
            # Convert specific page to image
            images = convert_from_path(str(pdf_path), first_page=page_number, last_page=page_number)
            if not images:
                return ""
            image = images[0]

            # Try PaddleOCR (Best for Indian Legal Docs)
            try:
                from paddleocr import PaddleOCR
                # Initialize only once in production
                ocr = PaddleOCR(use_angle_cls=True, lang='en')
                import numpy as np
                result = ocr.ocr(np.array(image), cls=True)
                # Paddle returns list of lines
                text = "\n".join([line[1][0] for line in result[0]])
                return text
            except ImportError:
                pass
            except Exception as e:
                logger.warning(f"PaddleOCR failed: {e}")

            # Fallback to Tesseract
            try:
                import pytesseract
                return pytesseract.image_to_string(image)
            except ImportError:
                logger.warning("pytesseract not installed")
            except Exception as e:
                logger.warning(f"Tesseract OCR failed: {e}")

            return ""

        except ImportError:
            logger.warning("pdf2image not installed, cannot perform OCR")
            return ""
        except Exception as e:
            logger.error(f"OCR pipeline error: {e}")
            return ""

    def _extract_paragraphs(self, text: str) -> list[str]:
        """
        Extract numbered paragraphs from text

        Args:
            text: Page text

        Returns:
            List of paragraph texts
        """
        # Split by paragraph numbers
        parts = self.PARAGRAPH_PATTERN.split(text)

        paragraphs = []
        for i in range(1, len(parts), 2):
            if i + 1 < len(parts):
                para_num = parts[i]
                para_text = parts[i + 1].strip()
                paragraphs.append(f"{para_num}. {para_text}")

        return paragraphs if paragraphs else [text]

    def _split_into_sections(self, text: str) -> list[tuple[str, str]]:
        """Split text on legal section headings.

        Returns a list of (heading, body) tuples where *heading* is the
        matched heading line (or "" for text before the first heading) and
        *body* is the text that follows it.
        """
        # Find all heading positions
        positions: list[tuple[int, str]] = []
        for m in self.SECTION_HEADING_PATTERN.finditer(text):
            positions.append((m.start(), m.group(0).strip()))

        if not positions:
            return [("" , text)]

        sections: list[tuple[str, str]] = []
        # Text before first heading
        if positions[0][0] > 0:
            preamble = text[:positions[0][0]].strip()
            if preamble:
                sections.append(("", preamble))

        for idx, (start, heading) in enumerate(positions):
            end = positions[idx + 1][0] if idx + 1 < len(positions) else len(text)
            # Skip heading line itself
            body_start = text.find("\n", start)
            body = text[body_start:end].strip() if body_start != -1 else ""
            if body:
                sections.append((heading, body))

        return sections if sections else [("", text)]

    def create_chunks(
        self,
        pages: list[PDFPage],
        document_id: str,
    ) -> Generator[DocumentChunk, None, None]:
        """
        Create chunks from PDF pages using a three-tier strategy:
          1. Numbered paragraphs  (natural legal boundaries)
          2. Section headings     (HELD / FACTS / JUDGMENT etc.)
          3. Sliding window       (fallback for unstructured text)

        Each chunk carries a ``chunk_type`` metadata tag so downstream
        retrieval can boost or filter by section type.
        """
        for page in pages:
            # --- Tier 1: Numbered paragraphs (most reliable in Indian judgments) ---
            if len(page.paragraphs) > 1:
                for i, para in enumerate(page.paragraphs, 1):
                    yield DocumentChunk(
                        id=str(uuid4()),
                        document_id=document_id,
                        content=para,
                        page_number=page.page_number,
                        paragraph_number=i,
                        metadata={"source": "paragraph", "chunk_type": "paragraph"},
                    )
                continue

            # --- Tier 2: Section-heading split ---
            sections = self._split_into_sections(page.text)
            if len(sections) > 1:
                para_counter = 1
                for heading, body in sections:
                    # A section may still be large; slide within it
                    chunk_type = "heading" if heading else "paragraph"
                    start = 0
                    while start < len(body):
                        end = start + self.chunk_size
                        chunk_text = body[start:end]
                        if end < len(body):
                            last_period = chunk_text.rfind('.')
                            if last_period > self.chunk_size // 2:
                                end = start + last_period + 1
                                chunk_text = body[start:end]
                        content = f"{heading}\n{chunk_text}".strip() if heading else chunk_text.strip()
                        if content:
                            yield DocumentChunk(
                                id=str(uuid4()),
                                document_id=document_id,
                                content=content,
                                page_number=page.page_number,
                                paragraph_number=para_counter,
                                metadata={"source": "section", "section_heading": heading, "chunk_type": chunk_type},
                            )
                            para_counter += 1
                        start = end - self.chunk_overlap
                continue

            # --- Tier 3: Sliding window (fallback) ---
            text = page.text
            start = 0
            para_counter = 1

            while start < len(text):
                end = start + self.chunk_size
                chunk_text = text[start:end]

                # Try to end at sentence boundary
                if end < len(text):
                    last_period = chunk_text.rfind('.')
                    if last_period > self.chunk_size // 2:
                        end = start + last_period + 1
                        chunk_text = text[start:end]

                yield DocumentChunk(
                    id=str(uuid4()),
                    document_id=document_id,
                    content=chunk_text.strip(),
                    page_number=page.page_number,
                    paragraph_number=para_counter,
                    metadata={"source": "sliding_window", "chunk_type": "paragraph"},
                )

                para_counter += 1
                start = end - self.chunk_overlap

    def extract_metadata(self, pages: list[PDFPage]) -> dict:
        """
        Extract metadata from legal document

        Args:
            pages: List of PDFPage objects

        Returns:
            Dictionary with extracted metadata
        """
        # Combine first few pages for metadata extraction
        header_text = " ".join(p.text for p in pages[:3])

        metadata = {
            "case_number": None,
            "date": None,
            "court": None,
            "judges": [],
            "parties": {},
        }

        # Extract case number
        case_match = self.CASE_NUMBER_PATTERN.search(header_text)
        if case_match:
            metadata["case_number"] = case_match.group()

        # Extract date
        date_match = self.DATE_PATTERN.search(header_text)
        if date_match:
            metadata["date"] = date_match.group(1)

        # Detect court
        header_lower = header_text.lower()
        if "supreme court" in header_lower:
            metadata["court"] = Court.SUPREME_COURT
        elif "high court" in header_lower:
            metadata["court"] = Court.HIGH_COURT
            # Try to identify which High Court
            hc_patterns = [
                (r'bombay high court', 'Bombay'),
                (r'delhi high court', 'Delhi'),
                (r'madras high court', 'Madras'),
                (r'calcutta high court', 'Calcutta'),
                (r'karnataka high court', 'Karnataka'),
            ]
            for pattern, name in hc_patterns:
                if re.search(pattern, header_lower):
                    metadata["high_court_name"] = name
                    break
        elif "district court" in header_lower:
            metadata["court"] = Court.DISTRICT_COURT
        elif "tribunal" in header_lower:
            metadata["court"] = Court.TRIBUNAL

        # Extract judges (look for patterns like "Hon'ble Justice" or "J.")
        judge_pattern = re.compile(
            r"(?:Hon'ble\s+)?(?:Mr\.\s+)?Justice\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
            re.IGNORECASE
        )
        judges = judge_pattern.findall(header_text)
        metadata["judges"] = list(set(judges))

        return metadata

    def process_pdf(
        self,
        pdf_path: str | Path,
        document_id: Optional[str] = None,
    ) -> tuple[LegalDocument, list[DocumentChunk]]:
        """
        Complete PDF processing pipeline

        Args:
            pdf_path: Path to PDF file
            document_id: Optional document ID (generated if not provided)

        Returns:
            Tuple of (LegalDocument, list of DocumentChunks)
        """
        pdf_path = Path(pdf_path)
        document_id = document_id or str(uuid4())

        # Extract text
        pages = self.extract_text(pdf_path)

        # Extract metadata
        metadata = self.extract_metadata(pages)

        # Create chunks
        chunks = list(self.create_chunks(pages, document_id))

        # Build full text
        full_text = "\n\n".join(page.text for page in pages)

        # Create document
        from datetime import datetime
        document = LegalDocument(
            id=document_id,
            title=pdf_path.stem.replace("_", " ").title(),
            court=metadata.get("court", Court.OTHER),
            case_number=(metadata.get("case_number") or "Unknown"),
            date=datetime.now(),  # Would parse from metadata["date"] in production
            judges=metadata.get("judges", []),
            parties=metadata.get("parties", {}),
            full_text=full_text,
            chunks=chunks,
            language=Language.ENGLISH,
            metadata=metadata,
        )

        logger.info(
            f"Processed PDF: {pdf_path.name}, "
            f"Pages: {len(pages)}, Chunks: {len(chunks)}"
        )

        return document, chunks
