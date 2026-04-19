"""
Document formatting endpoints
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
import re

from junior.core import get_logger
from junior.core.types import Court
from junior.services import DocumentFormatter
from junior.api.schemas import FormatDocumentRequest, FormatDocumentResponse
from junior.services.audit_log import AuditEvent, append_audit_event

router = APIRouter()
logger = get_logger(__name__)


class DraftIssue(BaseModel):
    code: str
    severity: str
    message: str
    recommendation: str


class DraftQualityCheckResponse(BaseModel):
    score: int = Field(..., ge=0, le=100)
    confidence: str
    issues: list[DraftIssue] = Field(default_factory=list)
    checklist: dict[str, bool]
    ai_disclaimer: str = "AI-assisted quality screen. Advocate review required before filing."


def _quality_check(content: str, case_number: str, petitioner: str, respondent: str) -> DraftQualityCheckResponse:
    text = (content or "").strip()
    upper = text.upper()
    issues: list[DraftIssue] = []

    has_case_number = bool(case_number and case_number.strip() and case_number.strip().lower() in text.lower())
    has_prayer = "PRAYER" in upper or "RELIEF" in upper
    has_grounds = "GROUNDS" in upper or "ARGUMENT" in upper
    has_verification = "VERIFICATION" in upper or "AFFIRM" in upper
    has_date = bool(re.search(r"\b(\d{1,2}[./-]\d{1,2}[./-]\d{2,4}|\d{4}-\d{2}-\d{2})\b", text))
    has_parties = bool(
        petitioner and petitioner.strip() and petitioner.strip().lower() in text.lower()
    ) and bool(
        respondent and respondent.strip() and respondent.strip().lower() in text.lower()
    )

    checklist = {
        "case_number_present": has_case_number,
        "parties_present": has_parties,
        "grounds_present": has_grounds,
        "prayer_present": has_prayer,
        "verification_present": has_verification,
        "date_present": has_date,
    }

    if not has_case_number:
        issues.append(DraftIssue(
            code="missing_case_number",
            severity="high",
            message="Case number not detected in draft body.",
            recommendation="Include full case number in heading and cause title.",
        ))
    if not has_parties:
        issues.append(DraftIssue(
            code="missing_party_details",
            severity="high",
            message="Petitioner/respondent names not clearly present.",
            recommendation="Add complete party details in cause title and party array.",
        ))
    if not has_grounds:
        issues.append(DraftIssue(
            code="missing_grounds",
            severity="medium",
            message="No explicit grounds/arguments section detected.",
            recommendation="Add a dedicated GROUNDS or ARGUMENTS section.",
        ))
    if not has_prayer:
        issues.append(DraftIssue(
            code="missing_prayer",
            severity="high",
            message="Prayer/relief clause missing or unclear.",
            recommendation="Add a PRAYER section with clear reliefs.",
        ))
    if not has_verification:
        issues.append(DraftIssue(
            code="missing_verification",
            severity="medium",
            message="Verification statement not detected.",
            recommendation="Include final verification/affirmation paragraph.",
        ))
    if not has_date:
        issues.append(DraftIssue(
            code="missing_dates",
            severity="low",
            message="No explicit date pattern detected in draft.",
            recommendation="Mention relevant filing/event dates where required.",
        ))

    score = max(0, 100 - len([i for i in issues if i.severity == "high"]) * 20 - len([i for i in issues if i.severity == "medium"]) * 10 - len([i for i in issues if i.severity == "low"]) * 5)
    confidence = "high" if score >= 80 else "medium" if score >= 55 else "low"
    return DraftQualityCheckResponse(score=score, confidence=confidence, issues=issues, checklist=checklist)

@router.post("/document", response_model=FormatDocumentResponse)
async def format_document(request: FormatDocumentRequest):
    """
    Format a document for court submission

    Applies court-specific formatting rules:
    - Margins and fonts
    - Cause title format
    - Paragraph numbering
    - Verification section
    - AI draft watermark
    """
    logger.info(f"Formatting {request.document_type} for {request.court.value}")

    try:
        formatter = DocumentFormatter()

        # Format the document
        formatted_text = formatter.format_document(
            content=request.content,
            document_type=request.document_type,
            court=request.court,
            case_number=request.case_number,
            petitioner=request.petitioner,
            respondent=request.respondent,
        )

        # Generate HTML version
        html = formatter.generate_html(formatted_text, request.court)

        append_audit_event(
            AuditEvent(
                event_type="draft.format",
                actor="advocate",
                target="format.document",
                details={
                    "document_type": request.document_type,
                    "court": request.court.value,
                    "case_number": request.case_number,
                    "content_length": len(request.content or ""),
                },
            )
        )

        return FormatDocumentResponse(
            formatted_text=formatted_text,
            html=html,
            court=request.court.value,
            document_type=request.document_type,
        )

    except Exception as e:
        logger.error(f"Formatting error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/rules/{court}")
async def get_formatting_rules(court: str):
    """
    Get formatting rules for a specific court
    """
    try:
        court_enum = Court(court)
        formatter = DocumentFormatter()
        rules = formatter.get_formatting_rules(court_enum)

        return {
            "court": court,
            "font_family": rules.font_family,
            "font_size": rules.font_size,
            "line_spacing": rules.line_spacing,
            "margins": {
                "top": rules.margin_top,
                "bottom": rules.margin_bottom,
                "left": rules.margin_left,
                "right": rules.margin_right,
            },
            "paragraph_indent": rules.paragraph_indent,
            "page_numbering": rules.page_numbering,
        }

    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid court type. Valid: {[c.value for c in Court]}"
        )

@router.post("/preview", response_class=HTMLResponse)
async def preview_formatted_document(request: FormatDocumentRequest):
    """
    Preview formatted document as HTML

    Returns a styled HTML page that can be printed to PDF.
    """
    formatter = DocumentFormatter()

    formatted_text = formatter.format_document(
        content=request.content,
        document_type=request.document_type,
        court=request.court,
        case_number=request.case_number,
        petitioner=request.petitioner,
        respondent=request.respondent,
    )

    html = formatter.generate_html(formatted_text, request.court)

    return HTMLResponse(content=html)

@router.get("/templates")
async def list_document_templates():
    """
    List available document templates
    """
    return {
        "templates": [
            {
                "id": "writ_petition",
                "name": "Writ Petition",
                "description": "Writ Petition under Article 226/227",
            },
            {
                "id": "written_statement",
                "name": "Written Statement",
                "description": "Written Statement on behalf of Defendant",
            },
            {
                "id": "counter_affidavit",
                "name": "Counter Affidavit",
                "description": "Counter Affidavit on behalf of Respondent",
            },
            {
                "id": "rejoinder",
                "name": "Rejoinder",
                "description": "Rejoinder Affidavit on behalf of Petitioner",
            },
            {
                "id": "application",
                "name": "Application",
                "description": "Miscellaneous Application",
            },
            {
                "id": "memo",
                "name": "Memorandum of Appeal",
                "description": "Appeal Memorandum",
            },
        ]
    }


@router.post("/quality-check", response_model=DraftQualityCheckResponse)
async def quality_check_document(request: FormatDocumentRequest):
    """Run structural quality checks before filing/export."""
    result = _quality_check(
        content=request.content,
        case_number=request.case_number,
        petitioner=request.petitioner,
        respondent=request.respondent,
    )

    append_audit_event(
        AuditEvent(
            event_type="draft.quality_check",
            actor="advocate",
            target="format.quality_check",
            details={
                "document_type": request.document_type,
                "court": request.court.value,
                "case_number": request.case_number,
                "score": result.score,
                "issues": len(result.issues),
            },
        )
    )

    return result
