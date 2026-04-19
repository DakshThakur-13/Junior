"""Judge corpus aggregation and analytics helpers.

This service builds judge profiles from the existing documents corpus and
falls back to live legal search when the corpus does not contain enough data.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from functools import cached_property
from typing import Iterable, Optional
import re
import time

from junior.core import get_logger, settings

logger = get_logger(__name__)


_COURT_TYPE_MAP = {
    "supreme court": "supreme_court",
    "supreme_court": "supreme_court",
    "high court": "high_court",
    "high_court": "high_court",
    "district court": "district_court",
    "district_court": "district_court",
    "tribunal": "tribunal",
}


@dataclass
class JudgeJudgmentRecord:
    title: str
    citation: str
    summary: str
    year: Optional[int]
    court: str
    case_number: str
    case_type: str
    legal_status: str
    source_url: str
    is_landmark: bool = False


@dataclass
class JudgeSourceProvenance:
    title: str
    citation: str
    year: Optional[int]
    court: str
    case_type: str
    legal_status: str
    source_url: str
    origin: str
    summary: str


def _slugify(text: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return value or "judge"


def _normalize_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().lower()


def _safe_year(raw: object) -> Optional[int]:
    if isinstance(raw, int) and 1800 <= raw <= 2100:
        return raw
    if isinstance(raw, datetime):
        return raw.year
    if isinstance(raw, date):
        return raw.year
    if isinstance(raw, str):
        m = re.search(r"\b(19|20)\d{2}\b", raw)
        if m:
            return int(m.group(0))
    return None


def _listify(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str):
        if ";" in value:
            return [part.strip() for part in value.split(";") if part.strip()]
        if "," in value:
            return [part.strip() for part in value.split(",") if part.strip()]
        if value.strip():
            return [value.strip()]
    return []


def _extract_judges(row: dict) -> list[str]:
    judges_raw = row.get("judges")
    judges = _listify(judges_raw)
    if judges:
      return judges

    metadata = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
    return _listify(metadata.get("judges"))


def _matches_judge(candidate: str, judge_name: str) -> bool:
    candidate_norm = _normalize_text(candidate)
    judge_norm = _normalize_text(judge_name)
    if not candidate_norm or not judge_norm:
        return False

    if candidate_norm == judge_norm:
        return True

    candidate_parts = [part for part in re.split(r"\s+", candidate_norm) if part]
    judge_parts = [part for part in re.split(r"\s+", judge_norm) if part]

    if len(judge_parts) >= 2 and len(candidate_parts) >= 2:
        if candidate_parts[-1] == judge_parts[-1] and candidate_parts[0] == judge_parts[0]:
            return True

    return judge_norm in candidate_norm or candidate_norm in judge_norm


def _normalize_court(raw: object) -> str:
    text = _normalize_text(raw)
    return _COURT_TYPE_MAP.get(text, text.replace(" ", "_") if text else "other")


def _estimate_specializations(row: dict) -> list[str]:
    texts = [
        str(row.get("title") or ""),
        str(row.get("summary") or ""),
        str(row.get("case_type") or ""),
        " ".join(_listify(row.get("keywords"))),
        " ".join(_listify(row.get("legal_provisions"))),
    ]
    text = _normalize_text(" ".join(texts))

    mapping = {
        "Criminal Law": ["bail", "criminal", "murder", "robbery", "ipc", "crpc", "theft", "assault"],
        "Constitutional Remedies": ["writ", "habeas corpus", "mandamus", "certiorari", "constitution", "article 32", "article 226"],
        "Civil Procedure": ["injunction", "partition", "property", "suit", "civil", "cpc", "specific performance"],
        "Service Law": ["service", "termination", "appointment", "recruitment", "disciplinary", "promotion"],
        "Family Law": ["maintenance", "divorce", "custody", "domestic violence", "matrimonial"],
        "Labour Law": ["labour", "employee", "employment", "industrial dispute", "wages"],
        "Tax Law": ["income tax", "gst", "tax", "customs", "excise"],
        "Corporate & Commercial": ["company", "insolvency", "merger", "arbitration", "contract", "commercial"],
        "Property & Land": ["land", "property", "revenue", "title", "possession", "tenancy"],
    }

    matches: list[str] = []
    for label, needles in mapping.items():
        if any(needle in text for needle in needles):
            matches.append(label)

    return matches[:5]


def _estimate_case_complexity_days(row: dict) -> int:
    text = _normalize_text(
        " ".join(
            [
                str(row.get("title") or ""),
                str(row.get("summary") or ""),
                str(row.get("case_type") or ""),
                " ".join(_listify(row.get("keywords"))),
            ]
        )
    )

    if any(term in text for term in ["bail", "anticipatory bail", "remand"]):
        return 45
    if any(term in text for term in ["injunction", "stay order", "temporary injunction"]):
        return 120
    if any(term in text for term in ["writ", "constitutional", "article 32", "article 226"]):
        return 180
    if any(term in text for term in ["civil", "partition", "property", "suit"]):
        return 150
    if any(term in text for term in ["criminal", "murder", "robbery", "ipc", "conviction"]):
        return 240
    return 120


def _positive_outcome(text: str) -> bool:
    return any(term in text for term in ["allowed", "granted", "upheld", "affirmed", "accepted", "partly allowed", "sustained"])


def _negative_outcome(text: str) -> bool:
    return any(term in text for term in ["dismissed", "rejected", "refused", "denied", "quashed", "set aside", "overruled"])


class JudgeCorpusService:
    def __init__(self):
        self._free_client = None
        self._cache: dict[tuple[str, ...], tuple[float, object]] = {}
        self._cache_ttl_seconds = 600.0

    @cached_property
    def _supabase_available(self) -> bool:
        try:
            from junior.db.client import get_supabase_client

            return get_supabase_client().is_configured
        except Exception:
            return False

    def _get_free_client(self):
        if self._free_client is None:
            try:
                from junior.services.free_legal_sources import get_free_legal_client

                self._free_client = get_free_legal_client()
            except Exception as exc:
                logger.info(f"Judge corpus free client unavailable: {exc}")
                self._free_client = False
        return self._free_client if self._free_client is not False else None

    def _supabase_rows(self) -> list[dict]:
        if not self._supabase_available:
            return []

        try:
            from junior.db.client import get_supabase_client

            client = get_supabase_client()
            result = (
                client.documents
                .select("id,title,court,case_number,case_type,judgment_date,judges,bench_strength,parties,summary,legal_status,keywords,legal_provisions,source_url,pdf_url,metadata,is_landmark")
                .order("judgment_date", desc=True)
                .limit(1000)
                .execute()
            )
            return [row for row in (result.data or []) if isinstance(row, dict)]
        except Exception as exc:
            logger.warning(f"Judge corpus Supabase query failed: {exc}")
            return []

    def _local_rows(self) -> list[dict]:
        try:
            from pathlib import Path
            import json

            docs_dir = Path("uploads") / "documents"
            if not docs_dir.exists():
                return []

            rows: list[dict] = []
            for fp in docs_dir.glob("*.json"):
                try:
                    payload = json.loads(fp.read_text(encoding="utf-8"))
                    if isinstance(payload, dict):
                        rows.append(payload)
                except Exception:
                    continue
            return rows
        except Exception as exc:
            logger.warning(f"Judge corpus local query failed: {exc}")
            return []

    def _source_rows(self) -> list[dict]:
        rows = self._supabase_rows()
        if rows:
            return rows
        return self._local_rows()

    def _cache_get(self, key: tuple[str, ...]):
        entry = self._cache.get(key)
        if not entry:
            return None
        created_at, value = entry
        if time.monotonic() - created_at > self._cache_ttl_seconds:
            self._cache.pop(key, None)
            return None
        return value

    def _cache_set(self, key: tuple[str, ...], value: object) -> None:
        self._cache[key] = (time.monotonic(), value)

    @staticmethod
    def _record_key(record: JudgeJudgmentRecord) -> str:
        return "|".join([
            _normalize_text(record.citation),
            _normalize_text(record.title),
            _normalize_text(record.source_url),
        ])

    def _row_to_record(self, row: dict) -> JudgeJudgmentRecord:
        metadata = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
        title = str(row.get("title") or metadata.get("title") or "Untitled Judgment")
        court = str(row.get("court") or metadata.get("court") or "")
        case_number = str(row.get("case_number") or metadata.get("case_number") or "")
        case_type = str(row.get("case_type") or metadata.get("case_type") or "")
        summary = str(row.get("summary") or metadata.get("summary") or "")
        legal_status = str(row.get("legal_status") or metadata.get("legal_status") or "")
        year = _safe_year(row.get("judgment_date") or metadata.get("date") or row.get("created_at"))
        source_url = str(row.get("source_url") or row.get("pdf_url") or metadata.get("source_url") or metadata.get("pdf_url") or "")

        citation = case_number or title
        is_landmark = bool(row.get("is_landmark"))
        return JudgeJudgmentRecord(
            title=title,
            citation=citation,
            summary=summary,
            year=year,
            court=court,
            case_number=case_number,
            case_type=case_type,
            legal_status=legal_status,
            source_url=source_url,
            is_landmark=is_landmark,
        )

    def _judge_records_from_rows(
        self,
        rows: Iterable[dict],
        judge_name: str,
        *,
        court: Optional[str] = None,
        case_type: Optional[str] = None,
    ) -> list[JudgeJudgmentRecord]:
        matches: list[JudgeJudgmentRecord] = []
        court_norm = _normalize_text(court)
        case_type_norm = _normalize_text(case_type)
        for row in rows:
            judges = _extract_judges(row)
            if not judges:
                continue

            if not any(_matches_judge(candidate, judge_name) for candidate in judges):
                continue

            row_court = _normalize_text(row.get("court"))
            row_case_type = _normalize_text(row.get("case_type"))
            if court_norm and court_norm not in row_court:
                continue
            if case_type_norm and case_type_norm not in row_case_type and case_type_norm not in _normalize_text(row.get("summary")):
                continue

            matches.append(self._row_to_record(row))

        return matches

    async def _internet_records(
        self,
        *,
        judge_name: str,
        court: Optional[str] = None,
        case_type: Optional[str] = None,
        limit: int = 12,
    ) -> list[JudgeJudgmentRecord]:
        free_client = self._get_free_client()
        if not free_client:
            return []

        query_parts = [f'"{judge_name}"']
        if case_type:
            query_parts.append(case_type)
        if court:
            query_parts.append(court)
        query = " ".join(query_parts)

        try:
            search_results = await free_client.search(query, max_results=limit)
        except Exception as exc:
            logger.warning(f"Judge corpus internet search failed: {exc}")
            return []

        internet_records: list[JudgeJudgmentRecord] = []
        for result in search_results:
            summary = result.headline or ""
            if not summary and getattr(result, "full_text", None):
                summary = str(result.full_text)[:600]
            internet_records.append(
                JudgeJudgmentRecord(
                    title=str(result.title or "Untitled Judgment"),
                    citation=str(result.title or result.doc_id),
                    summary=summary,
                    year=_safe_year(result.date),
                    court=str(result.court or ""),
                    case_number=str(result.doc_id or ""),
                    case_type=case_type or "",
                    legal_status="",
                    source_url=str(result.url or ""),
                    is_landmark=False,
                )
            )

        return internet_records

    def _to_provenance(self, record: JudgeJudgmentRecord, origin: str) -> dict:
        return {
            "title": record.title,
            "citation": record.citation,
            "year": record.year,
            "court": record.court,
            "case_type": record.case_type,
            "legal_status": record.legal_status,
            "source_url": record.source_url,
            "origin": origin,
            "summary": record.summary,
            "is_landmark": record.is_landmark,
        }

    def _build_excerpts_from_records(self, records: list[JudgeJudgmentRecord]) -> list[str]:
        excerpts: list[str] = []
        for record in records:
            pieces = [
                f"Title: {record.title}",
                f"Citation: {record.citation}",
            ]
            if record.year:
                pieces.append(f"Year: {record.year}")
            if record.court:
                pieces.append(f"Court: {record.court}")
            if record.case_type:
                pieces.append(f"Case Type: {record.case_type}")
            if record.legal_status:
                pieces.append(f"Outcome: {record.legal_status}")
            if record.summary:
                pieces.append(f"Summary: {record.summary}")
            if record.source_url:
                pieces.append(f"Source: {record.source_url}")
            excerpts.append("\n".join(pieces))
        return excerpts

    async def collect_judgments_with_provenance(
        self,
        *,
        judge_name: str,
        court: Optional[str] = None,
        case_type: Optional[str] = None,
        limit: int = 12,
    ) -> tuple[list[JudgeJudgmentRecord], list[dict]]:
        cache_key = ("judgments", judge_name.lower().strip(), (court or "").lower().strip(), (case_type or "").lower().strip(), str(limit))
        cached = self._cache_get(cache_key)
        if isinstance(cached, tuple) and len(cached) == 2:
            records, provenance = cached
            return list(records), list(provenance)

        rows = self._source_rows()
        records = self._judge_records_from_rows(rows, judge_name, court=court, case_type=case_type)

        provenance: list[dict] = []
        if records:
            origin = "supabase" if self._supabase_rows() else "local"
            records = self._rank_records(records)[:limit]
            provenance = [self._to_provenance(record, origin) for record in records]

        if len(records) < max(3, limit // 2):
            internet_records = await self._internet_records(
                judge_name=judge_name,
                court=court,
                case_type=case_type,
                limit=limit,
            )

            if not records:
                records = self._rank_records(internet_records)[:limit]
                provenance = [self._to_provenance(record, "internet") for record in records]
            else:
                merged: list[JudgeJudgmentRecord] = []
                provenance_map: dict[str, dict] = {}
                seen: set[str] = set()

                for record in records:
                    key = self._record_key(record)
                    if key in seen:
                        continue
                    seen.add(key)
                    merged.append(record)
                    provenance_map[key] = self._to_provenance(record, provenance[0]["origin"] if provenance else "corpus")

                for record in internet_records:
                    key = self._record_key(record)
                    if key in seen:
                        continue
                    seen.add(key)
                    merged.append(record)
                    provenance_map[key] = self._to_provenance(record, "internet")

                records = self._rank_records(merged)[:limit]
                provenance = [provenance_map[self._record_key(record)] for record in records if self._record_key(record) in provenance_map]

        self._cache_set(cache_key, (tuple(records), tuple(provenance)))
        return records, provenance

    async def collect_judgments(
        self,
        *,
        judge_name: str,
        court: Optional[str] = None,
        case_type: Optional[str] = None,
        limit: int = 12,
    ) -> list[JudgeJudgmentRecord]:
        records, _ = await self.collect_judgments_with_provenance(
            judge_name=judge_name,
            court=court,
            case_type=case_type,
            limit=limit,
        )
        return records

    def _rank_records(self, records: list[JudgeJudgmentRecord]) -> list[JudgeJudgmentRecord]:
        def _score(record: JudgeJudgmentRecord) -> tuple[int, int, int]:
            landmark = 1 if record.is_landmark else 0
            summary_score = 1 if record.summary else 0
            year_score = record.year or 0
            return (landmark, summary_score, year_score)

        return sorted(records, key=_score, reverse=True)

    def _build_tendencies(self, records: list[JudgeJudgmentRecord]) -> dict:
        if not records:
            return {
                "bail_grant_rate": 0.0,
                "conviction_rate": 0.0,
                "injunction_rate": 0.0,
                "settlement_preference": 0.0,
                "avg_disposal_days": 0,
            }

        text_rows = [
            _normalize_text(" ".join([r.title, r.summary, r.case_type, r.legal_status]))
            for r in records
        ]

        bail_cases = [t for t in text_rows if "bail" in t or "anticipatory bail" in t]
        criminal_cases = [t for t in text_rows if any(term in t for term in ["criminal", "ipc", "murder", "robbery", "assault", "conviction", "sentence"])]
        injunction_cases = [t for t in text_rows if "injunction" in t or "stay" in t]
        civil_cases = [t for t in text_rows if any(term in t for term in ["civil", "suit", "partition", "property", "contract", "injunction"])]

        bail_grants = sum(1 for t in bail_cases if _positive_outcome(t))
        convictions = sum(1 for t in criminal_cases if any(term in t for term in ["convicted", "conviction", "sentenced"]))
        injunction_grants = sum(1 for t in injunction_cases if _positive_outcome(t))
        settlements = sum(1 for t in civil_cases if any(term in t for term in ["settled", "compromise", "mediation", "consent"]))

        bail_rate = round((bail_grants / len(bail_cases)) if bail_cases else 0.0, 2)
        conviction_rate = round((convictions / len(criminal_cases)) if criminal_cases else 0.0, 2)
        injunction_rate = round((injunction_grants / len(injunction_cases)) if injunction_cases else 0.0, 2)
        settlement_rate = round((settlements / len(civil_cases)) if civil_cases else 0.0, 2)

        complexity_estimates = [_estimate_case_complexity_days({
            "title": r.title,
            "summary": r.summary,
            "case_type": r.case_type,
        }) for r in records]
        avg_days = int(round(sum(complexity_estimates) / len(complexity_estimates))) if complexity_estimates else 0

        return {
            "bail_grant_rate": bail_rate,
            "conviction_rate": conviction_rate,
            "injunction_rate": injunction_rate,
            "settlement_preference": settlement_rate,
            "avg_disposal_days": avg_days,
        }

    def _build_profile(self, judge_name: str, records: list[JudgeJudgmentRecord]) -> dict:
        tendencies = self._build_tendencies(records)
        specializations = Counter()
        for record in records:
            for spec in _estimate_specializations({
                "title": record.title,
                "summary": record.summary,
                "case_type": record.case_type,
                "keywords": [],
                "legal_provisions": [],
            }):
                specializations[spec] += 1

        notable_judgments = [
            {
                "title": record.title,
                "citation": record.citation,
                "summary": record.summary or f"{record.case_type or 'Judgment'} before {judge_name}",
                "year": record.year,
            }
            for record in records[:8]
        ]

        total_judgments = len(records)
        latest_year = max((r.year or 0) for r in records) if records else 0
        current_year = datetime.utcnow().year
        status = "sitting" if latest_year and latest_year >= current_year - 5 else "retired"

        philosophy = self._build_philosophy(records, tendencies)
        tips = self._build_tips(records, tendencies)

        return {
            "id": _slugify(judge_name),
            "name": judge_name,
            "honorific": "Hon'ble Justice",
            "court": self._best_court(records),
            "court_type": _COURT_TYPE_MAP.get(_normalize_text(self._best_court(records)), "high_court"),
            "status": status,
            "specializations": [label for label, _ in specializations.most_common(6)],
            "total_judgments": total_judgments,
            "tendencies": tendencies,
            "judicial_philosophy": philosophy,
            "litigation_tips": tips,
            "notable_judgments": notable_judgments,
            "career": [],
        }

    def _best_court(self, records: list[JudgeJudgmentRecord]) -> str:
        courts = [r.court for r in records if r.court]
        if not courts:
            return "other"
        counts = Counter(courts)
        return counts.most_common(1)[0][0]

    def _build_philosophy(self, records: list[JudgeJudgmentRecord], tendencies: dict) -> str:
        if not records:
            return "Insufficient public corpus to infer a stable judicial philosophy yet."

        parts = ["Inference from available corpus:"]
        if tendencies["bail_grant_rate"] >= 0.65:
            parts.append("appears relatively liberty-preserving in bail matters")
        elif tendencies["bail_grant_rate"] <= 0.35 and tendencies["bail_grant_rate"] > 0:
            parts.append("appears cautious in bail matters and demands strong factual support")

        if tendencies["settlement_preference"] >= 0.5:
            parts.append("leans toward settlement/composite resolutions in civil disputes")

        if tendencies["injunction_rate"] >= 0.5:
            parts.append("is willing to grant interim protective relief when the record is clear")

        if not parts:
            parts.append("is fact-sensitive and procedural rigor oriented")

        return "; ".join(parts)

    def _build_tips(self, records: list[JudgeJudgmentRecord], tendencies: dict) -> list[str]:
        tips: list[str] = []
        if tendencies["bail_grant_rate"] >= 0.5:
            tips.append("Lead with the strongest liberty and custody facts; avoid over-arguing broad policy.")
        if tendencies["settlement_preference"] >= 0.4:
            tips.append("Keep a settlement fallback ready and identify the narrowest workable relief.")
        if tendencies["injunction_rate"] >= 0.4:
            tips.append("Bring clean documentary proof for urgency, balance of convenience, and irreparable harm.")
        if not tips:
            tips.append("Prepare a document-heavy, procedurally clean submission with short issue framing.")
        return tips[:5]

    async def list_profiles(
        self,
        *,
        page: int = 1,
        page_size: int = 12,
        court_type: Optional[str] = None,
        status: Optional[str] = None,
        specialization: Optional[str] = None,
        search: Optional[str] = None,
    ) -> tuple[list[dict], int]:
        cache_key = (
            "profiles",
            str(page),
            str(page_size),
            (court_type or "").lower().strip(),
            (status or "").lower().strip(),
            (specialization or "").lower().strip(),
            (search or "").lower().strip(),
        )
        cached = self._cache_get(cache_key)
        if isinstance(cached, tuple) and len(cached) == 2:
            profiles, total = cached
            return list(profiles), int(total)

        rows = self._source_rows()
        grouped: dict[str, list[dict]] = defaultdict(list)
        for row in rows:
            for judge in _extract_judges(row):
                grouped[judge].append(row)

        profiles: list[dict] = []
        for judge_name, judge_rows in grouped.items():
            records = [self._row_to_record(row) for row in judge_rows]
            profile = self._build_profile(judge_name, records)
            profiles.append(profile)

        if search:
            search_lower = _normalize_text(search)
            profiles = [p for p in profiles if search_lower in _normalize_text(p["name"]) or search_lower in _normalize_text(p.get("judicial_philosophy", ""))]

        if court_type:
            court_type_norm = _normalize_text(court_type)
            profiles = [p for p in profiles if _normalize_text(p.get("court_type")) == court_type_norm or court_type_norm in _normalize_text(p.get("court", ""))]

        if status:
            status_norm = _normalize_text(status)
            profiles = [p for p in profiles if _normalize_text(p.get("status")) == status_norm]

        if specialization:
            specialization_norm = _normalize_text(specialization)
            profiles = [p for p in profiles if any(specialization_norm in _normalize_text(spec) for spec in p.get("specializations", []))]

        profiles.sort(key=lambda p: (p.get("total_judgments", 0), p.get("name", "").lower()), reverse=True)
        total = len(profiles)
        start = (page - 1) * page_size
        end = start + page_size
        result = (profiles[start:end], total)
        self._cache_set(cache_key, (tuple(result[0]), result[1]))
        return result

    async def get_profile(self, judge_id_or_name: str) -> Optional[dict]:
        cache_key = ("profile", judge_id_or_name.lower().strip())
        cached = self._cache_get(cache_key)
        if isinstance(cached, dict):
            return cached

        profiles, _ = await self.list_profiles(page=1, page_size=1000, search=judge_id_or_name)
        target = _slugify(judge_id_or_name)
        for profile in profiles:
            if profile["id"] == target or _normalize_text(profile["name"]) == _normalize_text(judge_id_or_name):
                if profile.get("total_judgments", 0) >= 3:
                    self._cache_set(cache_key, profile)
                    return profile

                records = await self.collect_judgments(judge_name=profile["name"], limit=12)
                if records:
                    enriched = self._build_profile(profile["name"], records)
                    self._cache_set(cache_key, enriched)
                    return enriched
                self._cache_set(cache_key, profile)
                return profile

        if profiles:
            self._cache_set(cache_key, profiles[0])
            return profiles[0]

        records = await self.collect_judgments(judge_name=judge_id_or_name, limit=12)
        if records:
            enriched = self._build_profile(judge_id_or_name, records)
            self._cache_set(cache_key, enriched)
            return enriched
        return None

    async def get_judgments(
        self,
        *,
        judge_name: str,
        court: Optional[str] = None,
        case_type: Optional[str] = None,
        limit: int = 10,
    ) -> list[dict]:
        records = await self.collect_judgments(judge_name=judge_name, court=court, case_type=case_type, limit=limit)
        return [
            {
                "title": r.title,
                "citation": r.citation,
                "summary": r.summary,
                "year": r.year,
                "court": r.court,
                "case_number": r.case_number,
                "case_type": r.case_type,
                "legal_status": r.legal_status,
                "source_url": r.source_url,
                "is_landmark": r.is_landmark,
            }
            for r in records
        ]

    async def get_judgments_with_provenance(
        self,
        *,
        judge_name: str,
        court: Optional[str] = None,
        case_type: Optional[str] = None,
        limit: int = 12,
    ) -> tuple[list[dict], list[dict]]:
        records, provenance = await self.collect_judgments_with_provenance(
            judge_name=judge_name,
            court=court,
            case_type=case_type,
            limit=limit,
        )
        return [
            {
                "title": r.title,
                "citation": r.citation,
                "summary": r.summary,
                "year": r.year,
                "court": r.court,
                "case_number": r.case_number,
                "case_type": r.case_type,
                "legal_status": r.legal_status,
                "source_url": r.source_url,
                "is_landmark": r.is_landmark,
            }
            for r in records
        ], provenance

    async def build_analysis_excerpts(
        self,
        *,
        judge_name: str,
        court: Optional[str] = None,
        case_type: Optional[str] = None,
        limit: int = 12,
    ) -> list[str]:
        records = await self.collect_judgments(judge_name=judge_name, court=court, case_type=case_type, limit=limit)
        return self._build_excerpts_from_records(records)


_judge_corpus_service: Optional[JudgeCorpusService] = None


def get_judge_corpus_service() -> JudgeCorpusService:
    global _judge_corpus_service
    if _judge_corpus_service is None:
        _judge_corpus_service = JudgeCorpusService()
    return _judge_corpus_service