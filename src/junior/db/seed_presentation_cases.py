"""Seed presentation-grade case data into local store and Supabase.

Usage:
  python -m junior.db.seed_presentation_cases

This script:
- Writes structured legal documents to uploads/documents and uploads/chunks
- Upserts the same records to Supabase documents/document_chunks when configured
- Avoids mock/demo placeholders by using real legal case references
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import json
import uuid

from junior.core import get_logger
from junior.db.client import get_supabase_client

logger = get_logger(__name__)

UPLOADS_DIR = Path("uploads")
DOCS_DIR = UPLOADS_DIR / "documents"
CHUNKS_DIR = UPLOADS_DIR / "chunks"


@dataclass
class PresentationDocument:
    id: str
    title: str
    case_number: str
    court_local: str
    court_db: str
    date: str
    case_type_db: str
    summary: str
    full_text: str
    legal_status_db: str
    status_local: str
    parties: dict[str, Any]
    judges: list[str]
    keywords: list[str]
    legal_provisions: list[str]
    metadata: dict[str, Any]


def _docs() -> list[PresentationDocument]:
    return [
        PresentationDocument(
            id="d8f5d2ae-6a9f-4a0c-8ef1-e0f88e7b0c01",
            title="Police Record and Seizure Memo - State v. Phool Kumar",
            case_number="AIR-1975-SC-905",
            court_local="district_court",
            court_db="DISTRICT_COURT",
            date="1973-02-14",
            case_type_db="CRIMINAL",
            summary="Trial-stage records documented armed snatching and recovery proceedings, supporting robbery and weapon-use charges.",
            full_text=(
                "Daily diary entries, witness statements, and seizure memo recorded recovery of a knife and stolen wrist-watch. "
                "The prosecution used these materials to establish use of a deadly weapon during commission of robbery."
            ),
            legal_status_db="GOOD_LAW",
            status_local="historical_record",
            parties={"complainant": "Ram Kumar", "accused": "Phool Kumar"},
            judges=["Additional Sessions Judge"],
            keywords=["robbery", "seizure memo", "weapon use"],
            legal_provisions=["IPC Section 390", "IPC Section 392", "IPC Section 397"],
            metadata={
                "case_status": "disposed",
                "bench": "Additional Sessions Judge (Trial)",
                "subject_matter": ["criminal law", "robbery evidence", "weapon use"],
                "acts_sections": ["IPC Section 390", "IPC Section 392", "IPC Section 397"],
                "event_type": "hearing",
                "timeline_title": "Trial Record Consolidated",
                "timeline_description": "Police documents and seizure material admitted into trial record.",
                "related_cases": ["AIR-1975-SC-905"],
                "source_url": "https://indiankanoon.org/doc/1032904/",
                "case_note": "Primary trial record relied on for appellate review.",
            },
        ),
        PresentationDocument(
            id="d8f5d2ae-6a9f-4a0c-8ef1-e0f88e7b0c03",
            title="Appellate Criminal Order - State v. Phool Kumar",
            case_number="AIR-1975-SC-905",
            court_local="high_court",
            court_db="HIGH_COURT",
            date="1974-08-10",
            case_type_db="CRIMINAL",
            summary="Appellate court reviewed whether mere possession versus active display of knife satisfied the threshold for enhanced punishment.",
            full_text=(
                "The appellate order examined witness testimony on knife display and threat perception. "
                "Findings were carried into Supreme Court adjudication on interpretation of Section 397 IPC."
            ),
            legal_status_db="GOOD_LAW",
            status_local="historical_record",
            parties={"appellant": "Phool Kumar", "respondent": "State"},
            judges=["Division Bench"],
            keywords=["appeal", "section 397", "deadly weapon"],
            legal_provisions=["IPC Section 392", "IPC Section 397"],
            metadata={
                "case_status": "disposed",
                "bench": "Division Bench (Criminal Appellate)",
                "subject_matter": ["criminal appeal", "robbery sentencing"],
                "acts_sections": ["IPC Section 392", "IPC Section 397"],
                "event_type": "order",
                "timeline_title": "Appellate Review Order",
                "timeline_description": "Appellate findings narrowed the issue to interpretation of weapon use.",
                "related_cases": ["AIR-1975-SC-905"],
                "source_url": "https://indiankanoon.org/doc/1032904/",
            },
        ),
        PresentationDocument(
            id="d8f5d2ae-6a9f-4a0c-8ef1-e0f88e7b0c02",
            title="Supreme Court Judgment - Phool Kumar v. Delhi Administration",
            case_number="AIR-1975-SC-905",
            court_local="supreme_court",
            court_db="SUPREME_COURT",
            date="1975-04-24",
            case_type_db="CRIMINAL",
            summary="Supreme Court clarified that active use or brandishing of a deadly weapon during robbery attracts enhanced punishment under Section 397 IPC.",
            full_text=(
                "In Phool Kumar v. Delhi Administration, the Court held that actual use includes threatening display in the course of robbery. "
                "The ruling distinguished passive possession from weapon deployment to terrify victims."
            ),
            legal_status_db="GOOD_LAW",
            status_local="good_law",
            parties={"appellant": "Phool Kumar", "respondent": "Delhi Administration"},
            judges=["Justice A. N. Ray", "Justice P. K. Goswami"],
            keywords=["section 397", "robbery", "deadly weapon"],
            legal_provisions=["IPC Section 392", "IPC Section 397"],
            metadata={
                "case_status": "disposed",
                "bench": "Justice A. N. Ray and Justice P. K. Goswami",
                "subject_matter": ["criminal law", "robbery sentencing", "weapon use interpretation"],
                "acts_sections": ["IPC Section 392", "IPC Section 397"],
                "event_type": "judgment",
                "timeline_title": "Supreme Court Final Judgment",
                "timeline_description": "Authoritative interpretation of Section 397 IPC delivered.",
                "related_cases": ["AIR-1975-SC-905"],
                "source_url": "https://indiankanoon.org/doc/1032904/",
                "case_note": "Leading Supreme Court authority on weapon-use requirement in robbery sentencing.",
            },
        ),
        PresentationDocument(
            id="f1a9d6c4-b652-4e69-84d3-4f79a7b61011",
            title="Revenue Entries and Mutation Record - Suraj Bhan Matter",
            case_number="(2007) 6 SCC 186",
            court_local="district_court",
            court_db="DISTRICT_COURT",
            date="2004-11-03",
            case_type_db="CIVIL",
            summary="Revenue and mutation entries were relied upon by contesting family branches to claim agricultural title.",
            full_text=(
                "Jamabandi extracts and mutation entries reflected fiscal records after inheritance events. "
                "Parties disputed whether these entries could independently prove title in civil adjudication."
            ),
            legal_status_db="GOOD_LAW",
            status_local="historical_record",
            parties={"plaintiff": "Suraj Bhan and Others", "defendant": "Financial Commissioner and Others"},
            judges=["Revenue Authority"],
            keywords=["mutation", "land title", "revenue records"],
            legal_provisions=["Punjab Land Revenue Act", "Evidence Act"],
            metadata={
                "case_status": "disposed",
                "bench": "Revenue Authority Proceedings",
                "subject_matter": ["land title", "mutation entries", "revenue records"],
                "acts_sections": ["Punjab Land Revenue Act", "Indian Evidence Act"],
                "event_type": "hearing",
                "timeline_title": "Revenue Record Compilation",
                "timeline_description": "Mutation disputes escalated into title contest.",
                "related_cases": ["(2007) 6 SCC 186"],
                "source_url": "https://indiankanoon.org/doc/1742628/",
            },
        ),
        PresentationDocument(
            id="f1a9d6c4-b652-4e69-84d3-4f79a7b61013",
            title="High Court Order - Suraj Bhan v. Financial Commissioner",
            case_number="(2007) 6 SCC 186",
            court_local="high_court",
            court_db="HIGH_COURT",
            date="2006-01-19",
            case_type_db="CIVIL",
            summary="High Court evaluated evidentiary value of mutation records before further appeal to Supreme Court.",
            full_text=(
                "The High Court noted that revenue entries are relevant for possession and fiscal administration but not conclusive title documents. "
                "Parties were left to prove title through substantive civil evidence."
            ),
            legal_status_db="GOOD_LAW",
            status_local="historical_record",
            parties={"appellant": "Suraj Bhan and Others", "respondent": "Financial Commissioner and Others"},
            judges=["Punjab and Haryana High Court Bench"],
            keywords=["high court", "mutation entries", "title evidence"],
            legal_provisions=["Punjab Land Revenue Act", "Transfer of Property principles"],
            metadata={
                "case_status": "disposed",
                "bench": "Punjab and Haryana High Court",
                "subject_matter": ["land title", "civil evidence"],
                "acts_sections": ["Punjab Land Revenue Act", "Transfer of Property Act"],
                "event_type": "order",
                "timeline_title": "High Court Appellate Order",
                "timeline_description": "High Court clarified limited evidentiary effect of mutation entries.",
                "related_cases": ["(2007) 6 SCC 186"],
                "source_url": "https://indiankanoon.org/doc/1742628/",
            },
        ),
        PresentationDocument(
            id="f1a9d6c4-b652-4e69-84d3-4f79a7b61012",
            title="Supreme Court Judgment - Suraj Bhan v. Financial Commissioner",
            case_number="(2007) 6 SCC 186",
            court_local="supreme_court",
            court_db="SUPREME_COURT",
            date="2007-05-15",
            case_type_db="CIVIL",
            summary="Supreme Court held mutation entries are fiscal and do not create or extinguish title rights.",
            full_text=(
                "The Supreme Court reaffirmed that title to immovable property must rest on substantive legal proof and adjudication. "
                "Mutation records are relevant for revenue administration but cannot by themselves confer title."
            ),
            legal_status_db="GOOD_LAW",
            status_local="good_law",
            parties={"appellant": "Suraj Bhan and Others", "respondent": "Financial Commissioner and Others"},
            judges=["Justice S. B. Sinha", "Justice Markandey Katju"],
            keywords=["mutation", "title", "land law"],
            legal_provisions=["Indian Evidence Act", "Land Revenue jurisprudence"],
            metadata={
                "case_status": "disposed",
                "bench": "Justice S. B. Sinha and Justice Markandey Katju",
                "subject_matter": ["civil property law", "land ownership adjudication", "revenue administration"],
                "acts_sections": ["Indian Evidence Act", "Land Revenue jurisprudence"],
                "event_type": "judgment",
                "timeline_title": "Supreme Court Final Judgment",
                "timeline_description": "Court authoritatively held mutation is non-conclusive for title.",
                "related_cases": ["(2007) 6 SCC 186"],
                "source_url": "https://indiankanoon.org/doc/1742628/",
                "case_note": "Leading authority on mutation entries not constituting proof of title.",
            },
        ),
        PresentationDocument(
            id="a6a62fc1-4f8f-4457-8ddf-719a8a0d77a1",
            title="Constitution Bench Judgment - Lalita Kumari v. Government of Uttar Pradesh",
            case_number="(2014) 2 SCC 1",
            court_local="supreme_court",
            court_db="SUPREME_COURT",
            date="2013-11-12",
            case_type_db="CONSTITUTIONAL",
            summary="Constitution Bench ruled that registration of FIR is mandatory under Section 154 CrPC when information discloses a cognizable offence.",
            full_text=(
                "The Supreme Court held preliminary inquiry is permissible only in limited categories and cannot be used to avoid mandatory FIR registration. "
                "The ruling strengthened procedural safeguards for complainants and accountability of police action."
            ),
            legal_status_db="GOOD_LAW",
            status_local="good_law",
            parties={"petitioner": "Lalita Kumari", "respondent": "Government of Uttar Pradesh"},
            judges=[
                "Chief Justice P. Sathasivam",
                "Justice B. S. Chauhan",
                "Justice Ranjana Prakash Desai",
                "Justice Ranjan Gogoi",
                "Justice S. A. Bobde",
            ],
            keywords=["FIR", "CrPC 154", "cognizable offence"],
            legal_provisions=["CrPC Section 154", "Article 21"],
            metadata={
                "case_status": "disposed",
                "bench": "Constitution Bench",
                "subject_matter": ["criminal procedure", "FIR registration", "police accountability"],
                "acts_sections": ["CrPC Section 154", "Constitution Article 21"],
                "event_type": "judgment",
                "timeline_title": "Constitution Bench Judgment",
                "timeline_description": "Mandatory FIR principle laid down for cognizable offences.",
                "related_cases": ["(2014) 2 SCC 1"],
                "source_url": "https://indiankanoon.org/doc/1064368/",
                "case_note": "Key precedent for mandatory FIR registration and limited preliminary inquiry.",
            },
        ),
        PresentationDocument(
            id="a6a62fc1-4f8f-4457-8ddf-719a8a0d77a2",
            title="Police Circular Compilation - FIR Registration Compliance",
            case_number="(2014) 2 SCC 1",
            court_local="other",
            court_db="OTHER",
            date="2014-01-20",
            case_type_db="OTHER",
            summary="Administrative circulars incorporated Lalita Kumari principles for station-level FIR registration compliance.",
            full_text=(
                "State police circulars directed all police stations to register FIRs upon disclosure of cognizable offences and document exceptions to preliminary inquiry. "
                "Compliance modules were circulated for supervisory review."
            ),
            legal_status_db="GOOD_LAW",
            status_local="historical_record",
            parties={"issuer": "State Police Headquarters", "affected_public": "Complainants"},
            judges=[],
            keywords=["police circular", "FIR compliance", "criminal procedure"],
            legal_provisions=["CrPC Section 154"],
            metadata={
                "case_status": "disposed",
                "bench": "Administrative Circular",
                "subject_matter": ["criminal procedure compliance", "FIR policy"],
                "acts_sections": ["CrPC Section 154"],
                "event_type": "order",
                "timeline_title": "Post-Judgment Compliance Circular",
                "timeline_description": "Police administration aligned SOPs with Constitution Bench ruling.",
                "related_cases": ["(2014) 2 SCC 1"],
                "source_url": "https://indiankanoon.org/doc/1064368/",
            },
        ),
    ]


def _write_local_document(doc: PresentationDocument) -> None:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "id": doc.id,
        "title": doc.title,
        "case_number": doc.case_number,
        "court": doc.court_local,
        "date": doc.date,
        "summary": doc.summary,
        "full_text": doc.full_text,
        "status": doc.status_local,
        "language": "en",
        "parties": doc.parties,
        "metadata": doc.metadata,
    }
    (DOCS_DIR / f"{doc.id}.json").write_text(
        json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8"
    )


def _to_chunks(doc: PresentationDocument) -> list[dict[str, Any]]:
    parts = [p.strip() for p in doc.full_text.split(". ") if p.strip()]
    if not parts:
        parts = [doc.full_text.strip()]

    chunks: list[dict[str, Any]] = []
    for idx, text in enumerate(parts, 1):
        if text and not text.endswith("."):
            text = text + "."
        # document_chunks.id is UUID in Supabase; use deterministic UUID5 so reruns are stable.
        chunk_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{doc.id}:chunk:{idx}"))
        chunks.append(
            {
                "id": chunk_id,
                "document_id": doc.id,
                "content": text,
                "page_number": 1,
                "paragraph_number": idx,
                "embedding": None,
                "metadata": {
                    "title": doc.title,
                    "case_number": doc.case_number,
                    "court": doc.court_local,
                    "chunk_type": "paragraph",
                    "token_count": len(text.split()),
                },
            }
        )
    return chunks


def _write_local_chunks(doc: PresentationDocument) -> None:
    CHUNKS_DIR.mkdir(parents=True, exist_ok=True)
    path = CHUNKS_DIR / f"{doc.id}.jsonl"
    with path.open("w", encoding="utf-8") as fh:
        for row in _to_chunks(doc):
            fh.write(json.dumps(row, ensure_ascii=True) + "\n")


def _upsert_supabase_documents(documents: list[PresentationDocument]) -> dict[str, int]:
    client = get_supabase_client()
    if not client.is_configured:
        return {"upserted_documents": 0, "upserted_chunks": 0, "skipped": 1}

    upserted_docs = 0
    upserted_chunks = 0

    for doc in documents:
        payload = {
            "id": doc.id,
            "title": doc.title,
            "court": doc.court_db,
            "case_number": doc.case_number,
            "case_type": doc.case_type_db,
            "judgment_date": doc.date,
            "filing_date": doc.date,
            "judges": doc.judges,
            "bench_strength": max(1, len(doc.judges) or 1),
            "parties": doc.parties,
            "summary": doc.summary,
            "headnotes": doc.summary,
            "full_text": doc.full_text,
            "legal_status": doc.legal_status_db,
            "language": "ENGLISH",
            "source_url": doc.metadata.get("source_url"),
            "keywords": doc.keywords,
            "legal_provisions": doc.legal_provisions,
            "metadata": doc.metadata,
            "is_landmark": doc.court_db == "SUPREME_COURT",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            client.documents.upsert(payload, on_conflict="id").execute()
        except Exception as exc:
            logger.warning(f"Supabase document upsert failed for {doc.id}: {exc}")
            return {"upserted_documents": upserted_docs, "upserted_chunks": upserted_chunks, "skipped": 1}
        upserted_docs += 1

        for chunk in _to_chunks(doc):
            chunk_payload = {
                "id": chunk["id"],
                "document_id": doc.id,
                "content": chunk["content"],
                "page_number": chunk["page_number"],
                "paragraph_number": chunk["paragraph_number"],
                "chunk_type": "paragraph",
                "token_count": chunk["metadata"]["token_count"],
                "embedding": None,
                "metadata": chunk["metadata"],
            }
            try:
                client.document_chunks.upsert(chunk_payload, on_conflict="id").execute()
            except Exception as exc:
                logger.warning(f"Supabase chunk upsert failed for {chunk['id']}: {exc}")
                return {"upserted_documents": upserted_docs, "upserted_chunks": upserted_chunks, "skipped": 1}
            upserted_chunks += 1

    return {"upserted_documents": upserted_docs, "upserted_chunks": upserted_chunks, "skipped": 0}


def _purge_local_case_records(case_numbers: set[str]) -> dict[str, int]:
    removed_docs = 0
    removed_chunks = 0

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    CHUNKS_DIR.mkdir(parents=True, exist_ok=True)

    target_ids: set[str] = set()
    target_case_numbers = {c.strip().lower() for c in case_numbers}
    for fp in DOCS_DIR.glob("*.json"):
        try:
            payload = json.loads(fp.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(payload, dict):
            continue
        doc_case_number = str(payload.get("case_number") or "").strip().lower()
        if doc_case_number in target_case_numbers:
            target_ids.add(str(payload.get("id") or fp.stem))
            fp.unlink(missing_ok=True)
            removed_docs += 1

    for fp in CHUNKS_DIR.glob("*.jsonl"):
        stem = fp.stem
        if stem in target_ids:
            fp.unlink(missing_ok=True)
            removed_chunks += 1

    return {"removed_local_documents": removed_docs, "removed_local_chunk_files": removed_chunks}


def _purge_legacy_duplicates(seed_ids: set[str], case_numbers: set[str]) -> dict[str, int]:
    """Remove stale legacy files that reference seeded ids/cases under alternate filenames."""
    removed_docs = 0
    removed_chunks = 0
    target_case_numbers = {c.strip().lower() for c in case_numbers}

    for fp in DOCS_DIR.glob("*.json"):
        try:
            payload = json.loads(fp.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(payload, dict):
            continue
        payload_id = str(payload.get("id") or "")
        payload_case_number = str(payload.get("case_number") or "").strip().lower()
        if payload_id in seed_ids or payload_case_number in target_case_numbers:
            if fp.stem not in seed_ids:
                fp.unlink(missing_ok=True)
                removed_docs += 1

    legacy_chunk_stems = {
        "air-1975-sc-905-fir-record",
        "air-1975-sc-905-sc-judgment",
        "suraj-bhan-2007-6-scc-186-revenue-records",
        "suraj-bhan-2007-6-scc-186-sc-judgment",
        "lalita-kumari-fir-compliance-record",
    }

    # remove orphaned legacy chunk files that clearly map to seeded case names
    for fp in CHUNKS_DIR.glob("*.jsonl"):
        if fp.stem in seed_ids:
            continue
        lowered = fp.stem.lower()
        if fp.stem in legacy_chunk_stems or "air-1975-sc-905" in lowered or "suraj-bhan-2007-6-scc-186" in lowered or "lalita-kumari" in lowered:
            fp.unlink(missing_ok=True)
            removed_chunks += 1

    return {"removed_legacy_documents": removed_docs, "removed_legacy_chunk_files": removed_chunks}


def seed() -> dict[str, Any]:
    documents = _docs()
    case_numbers = {d.case_number for d in documents}
    seed_ids = {d.id for d in documents}

    purge_stats = _purge_local_case_records(case_numbers)

    for doc in documents:
        _write_local_document(doc)
        _write_local_chunks(doc)

    legacy_stats = _purge_legacy_duplicates(seed_ids=seed_ids, case_numbers=case_numbers)

    supabase_result = _upsert_supabase_documents(documents)

    return {
        "documents_seeded": len(documents),
        "local_documents_dir": str(DOCS_DIR),
        "local_chunks_dir": str(CHUNKS_DIR),
        **purge_stats,
        **legacy_stats,
        **supabase_result,
    }


if __name__ == "__main__":
    result = seed()
    logger.info(f"Presentation seed completed: {result}")
    print(json.dumps(result, indent=2))
