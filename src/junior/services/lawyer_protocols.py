"""Lawyer-grade protocols (Criminal + Civil) for Indian judiciary workflows.

Goal: make the assistant behave like a careful junior advocate:
- ask the right intake questions
- follow procedure-aware checklists
- avoid legal conclusions without evidence/citations

This module is intentionally static and lightweight (no network).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class LawyerProtocol:
    id: str
    title: str
    domain: str  # "criminal" | "civil" | "mixed"
    purpose: str
    intake_questions: tuple[str, ...]
    output_sections: tuple[str, ...]
    procedural_checklist: tuple[str, ...]
    common_attack_vectors: tuple[str, ...]

PROTOCOLS: tuple[LawyerProtocol, ...] = (
    LawyerProtocol(
        id="criminal_anticipatory_bail_438",
        title="Anticipatory Bail (CrPC s.438) — Court-ready analysis",
        domain="criminal",
        purpose="Prepare a cautious anticipatory bail strategy: facts, offences, custody risk, cooperation, and conditions.",
        intake_questions=(
            "Which State and which court is the matter in (Sessions/High Court)?",
            "FIR number, police station, sections invoked, and date of FIR?",
            "Has any notice under CrPC s.41A been issued or any arrest attempt made?",
            "Applicant’s role (named/unknown), prior criminal antecedents, and any pending cases?",
            "What is the prosecution’s main allegation and what are the key documents/witnesses?",
            "Any recovery pending (weapon/property) or custodial interrogation claimed?",
            "Any threats/flight risk allegations; can we propose conditions (passport deposit, appearance)?",
        ),
        output_sections=(
            "Facts (verified)",
            "Issues for Court",
            "Applicable Law (with citations)",
            "Application to Facts (with citations)",
            "Proposed Conditions",
            "Risks / Weak Points",
            "Next Steps (documents to collect)",
        ),
        procedural_checklist=(
            "Confirm maintainability and forum (Sessions vs High Court) and any local rules.",
            "Identify bar/limitations (e.g., specific offences, special statutes) if applicable.",
            "Prepare annexures: FIR, 41A notice, prior bail orders, medical records, etc.",
            "Draft undertaking for cooperation and availability.",
        ),
        common_attack_vectors=(
            "Custodial interrogation required / recovery pending",
            "Applicant is absconding / not cooperating",
            "Threat to witnesses / tampering",
            "Seriousness of offence / public interest",
        ),
    ),
    LawyerProtocol(
        id="criminal_regular_bail_437_439",
        title="Regular Bail (CrPC s.437/439) — Court-ready analysis",
        domain="criminal",
        purpose="Assess bail chances and craft a strategy with evidentiary gaps, custody duration, and conditions.",
        intake_questions=(
            "Custody date and current stage (investigation/charge-sheet/trial)?",
            "Sections invoked; is it bailable/non-bailable; any special statute?",
            "What is the prosecution’s key evidence (CCTV, CDR, recovery, witnesses)?",
            "Any previous bail orders / rejections and what changed since then?",
            "Medical grounds / age / dependents / local roots?",
            "Likelihood of witness tampering; can stringent conditions address it?",
        ),
        output_sections=(
            "Facts (verified)",
            "Custody & Stage",
            "Evidence Summary (with citations)",
            "Bail Grounds (with citations)",
            "Counter-arguments & Rebuttals",
            "Conditions to Offer",
        ),
        procedural_checklist=(
            "Confirm the correct forum for bail (Magistrate/Sessions/High Court).",
            "Collect: remand orders, charge-sheet, FSL reports, witness statements (if available).",
            "Prepare surety details and compliance plan.",
        ),
        common_attack_vectors=(
            "Serious offence / victim impact",
            "Repeat offender / antecedents",
            "Risk of absconding",
            "Influencing witnesses",
        ),
    ),
    LawyerProtocol(
        id="criminal_quash_482",
        title="Quashing (CrPC s.482) — Maintainability + merits",
        domain="criminal",
        purpose="Structure a cautious quashing strategy: jurisdiction, categories, and annexures.",
        intake_questions=(
            "Which High Court has territorial jurisdiction and why?",
            "FIR/complaint details and exact sections invoked?",
            "What is the gravamen of allegations and what documents contradict them?",
            "Any civil dispute angle / settlement / compromise?",
            "Stage: FIR only, charge-sheet filed, or trial underway?",
        ),
        output_sections=(
            "Maintainability / Jurisdiction",
            "Facts (verified)",
            "Grounds for Quashing (with citations)",
            "Annexures & Evidence",
            "Risks (why court may refuse)",
        ),
        procedural_checklist=(
            "Annex FIR/complaint, charge-sheet (if any), key documents relied upon.",
            "Check if alternative remedies exist (discharge, revision) and address maintainability.",
        ),
        common_attack_vectors=(
            "Disputed questions of fact (needs trial)",
            "Suppression / disputed documents",
            "Maintainability (alternate remedy)",
        ),
    ),
    LawyerProtocol(
        id="civil_temporary_injunction_o39",
        title="Temporary Injunction (CPC O.39) — 3-prong test",
        domain="civil",
        purpose="Prepare injunction arguments with prima facie case, balance of convenience, and irreparable injury.",
        intake_questions=(
            "Cause of action date(s) and limitation concerns?",
            "What exact relief is sought (status quo, restraint, mandatory)?",
            "Title/possession documents available?",
            "What is the immediate urgency and what irreparable harm will occur?",
            "Any prior litigation, undertakings, or parallel proceedings?",
        ),
        output_sections=(
            "Facts (verified)",
            "Relief Sought",
            "Prima Facie Case (with citations)",
            "Balance of Convenience",
            "Irreparable Injury",
            "Undertakings / Conditions",
            "Risks / Defences",
        ),
        procedural_checklist=(
            "Confirm jurisdiction and court-fee / valuation aspects.",
            "Prepare affidavit, annexures, photographs, and site plan if relevant.",
            "Address delay/laches and clean hands.",
        ),
        common_attack_vectors=(
            "Delay / laches / suppression",
            "No prima facie right",
            "Compensable damages (no irreparable injury)",
            "Balance of convenience against plaintiff",
        ),
    ),
    LawyerProtocol(
        id="civil_written_statement",
        title="Written Statement (CPC) — Defence structuring",
        domain="civil",
        purpose="Structure a written statement with admissions/denials, jurisdictional objections, and counter-claims.",
        intake_questions=(
            "Date of service and WS deadline status?",
            "Key documents relied by plaintiff and what we dispute?",
            "Any jurisdiction objections (territorial/pecuniary/subject-matter/arbitration clause)?",
            "Any limitation objections or waiver/acquiescence?",
            "Any set-off/counter-claim contemplated?",
        ),
        output_sections=(
            "Preliminary Objections",
            "Para-wise Reply (admit/deny)",
            "Defence Story (with exhibits)",
            "Legal Grounds (with citations)",
            "Set-off / Counter-claim (if any)",
            "Prayer",
        ),
        procedural_checklist=(
            "Confirm WS timeline and seek condonation if delayed.",
            "Compile exhibits and mark them.",
            "Check verification and affidavit requirements.",
        ),
        common_attack_vectors=(
            "Admissions in pleadings",
            "Inconsistent defences",
            "Lack of documents",
            "Delay in filing",
        ),
    ),
)

def list_protocols() -> list[LawyerProtocol]:
    return list(PROTOCOLS)

def get_protocol(protocol_id: str) -> Optional[LawyerProtocol]:
    pid = (protocol_id or "").strip()
    if not pid:
        return None
    for p in PROTOCOLS:
        if p.id == pid:
            return p
    return None

def suggest_protocol_id(query: str) -> Optional[str]:
    """Heuristic protocol picker from query text."""
    q = (query or "").lower()

    if any(k in q for k in ("anticipatory bail", "438", "pre-arrest")):
        return "criminal_anticipatory_bail_438"
    if any(k in q for k in ("regular bail", "439", "437", "bail application")):
        return "criminal_regular_bail_437_439"
    if any(k in q for k in ("482", "quash", "quashing", "inherent powers")):
        return "criminal_quash_482"
    if any(k in q for k in ("injunction", "order 39", "o.39", "status quo")):
        return "civil_temporary_injunction_o39"
    if any(k in q for k in ("written statement", "ws", "cpc")):
        return "civil_written_statement"

    return None

def protocol_brief(protocol_id: Optional[str]) -> str:
    p = get_protocol(protocol_id or "")
    if not p:
        return ""

    qs = "\n".join(f"- {q}" for q in p.intake_questions)
    checklist = "\n".join(f"- {c}" for c in p.procedural_checklist)
    attacks = "\n".join(f"- {a}" for a in p.common_attack_vectors)
    sections = "\n".join(f"- {s}" for s in p.output_sections)

    return (
        f"PROTOCOL: {p.title}\n"
        f"Purpose: {p.purpose}\n\n"
        f"Intake Questions:\n{qs}\n\n"
        f"Procedural Checklist:\n{checklist}\n\n"
        f"Common Opponent Attack Vectors:\n{attacks}\n\n"
        f"Preferred Output Sections:\n{sections}\n"
    )
