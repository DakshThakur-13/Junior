"""
Document formatting endpoints
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

from junior.core import get_logger
from junior.core.types import Court
from junior.services import DocumentFormatter
from junior.api.schemas import FormatDocumentRequest, FormatDocumentResponse

router = APIRouter()
logger = get_logger(__name__)

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
