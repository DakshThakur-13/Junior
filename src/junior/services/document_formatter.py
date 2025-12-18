"""
Document Formatter Service
Converts drafts to court-compliant documents
"""

from typing import Optional
from datetime import datetime
from dataclasses import dataclass

from junior.core import settings, get_logger
from junior.core.types import Court

logger = get_logger(__name__)

@dataclass
class FormattingRules:
    """Formatting rules for a specific court"""
    court: Court
    font_family: str
    font_size: int
    line_spacing: float
    margin_top: float
    margin_bottom: float
    margin_left: float
    margin_right: float
    paragraph_indent: float
    page_numbering: str
    watermark: Optional[str]

# Court-specific formatting rules (in points/inches)
COURT_RULES = {
    Court.SUPREME_COURT: FormattingRules(
        court=Court.SUPREME_COURT,
        font_family="Times New Roman",
        font_size=14,
        line_spacing=1.5,
        margin_top=1.5,
        margin_bottom=1.0,
        margin_left=1.5,
        margin_right=1.0,
        paragraph_indent=0.5,
        page_numbering="bottom-center",
        watermark=None,
    ),
    Court.HIGH_COURT: FormattingRules(
        court=Court.HIGH_COURT,
        font_family="Times New Roman",
        font_size=14,
        line_spacing=1.5,
        margin_top=1.0,
        margin_bottom=1.0,
        margin_left=1.5,
        margin_right=1.0,
        paragraph_indent=0.5,
        page_numbering="bottom-right",
        watermark=None,
    ),
    Court.DISTRICT_COURT: FormattingRules(
        court=Court.DISTRICT_COURT,
        font_family="Times New Roman",
        font_size=12,
        line_spacing=1.5,
        margin_top=1.0,
        margin_bottom=1.0,
        margin_left=1.0,
        margin_right=1.0,
        paragraph_indent=0.5,
        page_numbering="bottom-center",
        watermark=None,
    ),
}

class DocumentFormatter:
    """
    Document Formatter Service

    Converts raw text drafts into court-compliant formatted documents.
    Handles:
    - Court-specific formatting rules
    - Page margins and fonts
    - Paragraph numbering
    - Cause title formatting
    - AI draft watermarking
    """

    def __init__(self):
        self.watermark_enabled = settings.watermark_drafts

    def get_formatting_rules(self, court: Court) -> FormattingRules:
        """Get formatting rules for a specific court"""
        return COURT_RULES.get(court, COURT_RULES[Court.DISTRICT_COURT])

    def format_cause_title(
        self,
        case_number: str,
        petitioner: str,
        respondent: str,
        court: Court,
        judges: Optional[list[str]] = None,
    ) -> str:
        """
        Format the cause title/header of a legal document

        Args:
            case_number: Case number
            petitioner: Petitioner name(s)
            respondent: Respondent name(s)
            court: Court type
            judges: List of judge names

        Returns:
            Formatted cause title string
        """
        court_name = {
            Court.SUPREME_COURT: "IN THE SUPREME COURT OF INDIA",
            Court.HIGH_COURT: "IN THE HIGH COURT OF JUDICATURE",
            Court.DISTRICT_COURT: "IN THE DISTRICT COURT",
            Court.TRIBUNAL: "BEFORE THE TRIBUNAL",
        }.get(court, "IN THE COURT OF")

        lines = [
            court_name,
            "",
            case_number.upper(),
            "",
            "IN THE MATTER OF:",
            "",
            petitioner.upper(),
            "... PETITIONER(S)",
            "",
            "VERSUS",
            "",
            respondent.upper(),
            "... RESPONDENT(S)",
            "",
        ]

        if judges:
            lines.insert(1, f"CORAM: {', '.join(judges)}")
            lines.insert(2, "")

        return "\n".join(lines)

    def format_document(
        self,
        content: str,
        document_type: str,
        court: Court,
        case_number: str,
        petitioner: str = "Petitioner",
        respondent: str = "Respondent",
    ) -> str:
        """
        Format a complete legal document

        Args:
            content: Main content/body of the document
            document_type: Type of document (writ_petition, written_statement, etc.)
            court: Target court
            case_number: Case number
            petitioner: Petitioner name
            respondent: Respondent name

        Returns:
            Fully formatted document
        """
        rules = self.get_formatting_rules(court)

        # Document type header
        doc_type_headers = {
            "writ_petition": "WRIT PETITION UNDER ARTICLE 226/227 OF THE CONSTITUTION OF INDIA",
            "written_statement": "WRITTEN STATEMENT ON BEHALF OF THE DEFENDANT",
            "reply": "REPLY ON BEHALF OF THE PETITIONER",
            "counter_affidavit": "COUNTER AFFIDAVIT ON BEHALF OF THE RESPONDENT",
            "rejoinder": "REJOINDER AFFIDAVIT ON BEHALF OF THE PETITIONER",
            "application": "APPLICATION UNDER...",
            "memo": "MEMORANDUM OF APPEAL",
        }

        doc_header = doc_type_headers.get(
            document_type.lower(),
            document_type.upper().replace("_", " ")
        )

        # Build document
        parts = []

        # Cause title
        parts.append(self.format_cause_title(
            case_number, petitioner, respondent, court
        ))

        # Document type
        parts.append(doc_header)
        parts.append("=" * len(doc_header))
        parts.append("")

        # Main content with paragraph numbering if not already numbered
        formatted_content = self._ensure_paragraph_numbering(content)
        parts.append(formatted_content)

        # Add verification if needed
        if document_type.lower() in ["writ_petition", "counter_affidavit", "rejoinder"]:
            parts.append("")
            parts.append(self._get_verification_text())

        # Prayer section placeholder
        parts.append("")
        parts.append("PRAYER")
        parts.append("-" * 6)
        parts.append("")
        parts.append("In the facts and circumstances of the case, it is most respectfully prayed that this Hon'ble Court may be pleased to:")
        parts.append("")
        parts.append("a) [Prayer clause 1]")
        parts.append("b) [Prayer clause 2]")
        parts.append("c) Pass any other order(s) as this Hon'ble Court may deem fit and proper in the interest of justice.")

        # Footer
        parts.append("")
        parts.append("")
        parts.append(f"Place: ___________")
        parts.append(f"Dated: {datetime.now().strftime('%d.%m.%Y')}")
        parts.append("")
        parts.append("PETITIONER/APPLICANT")
        parts.append("Through: _______________")
        parts.append("Advocate for the Petitioner")

        document = "\n".join(parts)

        # Add watermark if enabled
        if self.watermark_enabled:
            document = self._add_watermark(document)

        return document

    def _ensure_paragraph_numbering(self, content: str) -> str:
        """
        Ensure content has proper paragraph numbering

        Args:
            content: Content to check/number

        Returns:
            Content with paragraph numbers
        """
        import re

        # Check if already numbered
        if re.search(r'^\s*\d+\.', content, re.MULTILINE):
            return content

        # Split into paragraphs and number them
        paragraphs = content.split("\n\n")
        numbered = []
        para_num = 1

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # Skip headers and short lines
            if len(para) < 50 or para.isupper():
                numbered.append(para)
            else:
                numbered.append(f"{para_num}.\t{para}")
                para_num += 1

        return "\n\n".join(numbered)

    def _get_verification_text(self) -> str:
        """Get standard verification text"""
        return """
VERIFICATION

I, _______________, the above-named Petitioner, do hereby verify that the contents of the above petition are true and correct to my personal knowledge and belief, and nothing material has been concealed therefrom.

Verified at _______________ on this ___ day of _______________, 2024.

DEPONENT
"""

    def _add_watermark(self, document: str) -> str:
        """Add AI draft watermark to document"""
        watermark_header = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                         ⚠️  AI GENERATED DRAFT  ⚠️                            ║
║          This document was generated by Junior AI Legal Assistant.          ║
║         All citations and content must be independently verified.            ║
║                    NOT FOR FILING - INTERNAL USE ONLY                        ║
╚══════════════════════════════════════════════════════════════════════════════╝

"""

        watermark_footer = """

════════════════════════════════════════════════════════════════════════════════
                            DRAFT GENERATED BY JUNIOR
                    Verify all citations before court submission
════════════════════════════════════════════════════════════════════════════════
"""

        return watermark_header + document + watermark_footer

    def generate_html(
        self,
        document: str,
        court: Court,
    ) -> str:
        """
        Generate HTML version of document with proper styling

        Args:
            document: Formatted document text
            court: Target court for styling

        Returns:
            HTML string
        """
        rules = self.get_formatting_rules(court)

        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Legal Document - Junior</title>
    <style>
        @page {{
            margin-top: {rules.margin_top}in;
            margin-bottom: {rules.margin_bottom}in;
            margin-left: {rules.margin_left}in;
            margin-right: {rules.margin_right}in;
        }}
        body {{
            font-family: '{rules.font_family}', serif;
            font-size: {rules.font_size}pt;
            line-height: {rules.line_spacing};
            text-align: justify;
        }}
        .header {{
            text-align: center;
            font-weight: bold;
            margin-bottom: 2em;
        }}
        .paragraph {{
            text-indent: {rules.paragraph_indent}in;
            margin-bottom: 1em;
        }}
        .watermark {{
            background-color: #fff3cd;
            border: 2px solid #ffc107;
            padding: 1em;
            margin-bottom: 2em;
            text-align: center;
        }}
    </style>
</head>
<body>
    <div class="content">
        <pre style="white-space: pre-wrap; font-family: '{rules.font_family}', serif;">
{document}
        </pre>
    </div>
</body>
</html>
"""
        return html
