"""Detective Wall Agent

Analyzes a set of evidence/precedent/statement nodes and their relationships
(contradicts, supports, timeline, etc.) and returns structured insights.

This agent is intentionally strict: it must only reason over the nodes/edges
provided by the client and must not invent new evidence.
"""

from __future__ import annotations

import json
import re
from typing import Any, cast

from junior.core.types import AgentRole
from .base import BaseAgent, AgentState

class DetectiveWallAgent(BaseAgent):
    role = AgentRole.CRITIC  # closest role; this is an analysis agent

    @property
    def system_prompt(self) -> str:
        return (
            "You are an investigative legal analyst working on a detective wall. "
            "You must only use the provided nodes/edges. Do NOT invent evidence. "
            "Return ONLY valid JSON matching the requested schema."
        )

    async def analyze(self, *, case_context: str, nodes: list[dict], edges: list[dict]) -> dict:
        prompt = self._build_prompt(case_context=case_context, nodes=nodes, edges=edges)
        raw = await self.invoke_llm(prompt)
        parsed = self._parse_json(raw)
        return self._coerce_response(parsed)

    async def process(self, state: AgentState) -> AgentState:
        # Not used in the LangGraph pipeline today. Kept to satisfy BaseAgent.
        return state

    def _build_prompt(self, *, case_context: str, nodes: list[dict], edges: list[dict]) -> str:
        return (
            "DETECTIVE WALL ANALYSIS\n\n"
            "CASE CONTEXT (may be empty):\n"
            f"{case_context or ''}\n\n"
            "NODES (the only facts you may use):\n"
            f"{json.dumps(nodes, ensure_ascii=False)}\n\n"
            "EDGES (relationships between nodes; the only relationships you may use):\n"
            f"{json.dumps(edges, ensure_ascii=False)}\n\n"
            "TASK:\n"
            "1) Identify contradictions, missing links, and key pivots.\n"
            "2) Produce a short, actionable plan for what to do next (drafts to prepare, questions to ask, evidence to obtain).\n"
            "3) If you suggest a link, it must reference existing node ids.\n\n"
            "OUTPUT JSON SCHEMA (return only JSON):\n"
            "{\n"
            '  "summary": string,\n'
            '  "insights": [{"title": string, "detail": string, "severity": "low"|"medium"|"high", "node_ids": [string]}],\n'
            '  "suggested_links": [{"source": string, "target": string, "label": string, "confidence": number, "reason": string}],\n'
            '  "next_actions": [string]\n'
            "}"
        )

    def _parse_json(self, text: str) -> dict:
        text = (text or "").strip()
        # try direct json
        try:
            value = json.loads(text)
            if isinstance(value, dict):
                return value
        except Exception:
            pass

        # try extract first json object
        m = re.search(r"\{[\s\S]*\}", text)
        if m:
            try:
                value = json.loads(m.group(0))
                if isinstance(value, dict):
                    return value
            except Exception:
                pass

        return {}

    def _coerce_response(self, value: dict) -> dict:
        summary = value.get("summary") if isinstance(value.get("summary"), str) else ""
        insights_value = value.get("insights")
        insights: list[Any] = cast(list[Any], insights_value) if isinstance(insights_value, list) else []

        suggested_links_value = value.get("suggested_links")
        suggested_links: list[Any] = (
            cast(list[Any], suggested_links_value) if isinstance(suggested_links_value, list) else []
        )

        next_actions_value = value.get("next_actions")
        next_actions: list[Any] = cast(list[Any], next_actions_value) if isinstance(next_actions_value, list) else []

        def _clean_insight(item: Any) -> dict:
            if not isinstance(item, dict):
                return {}
            title = item.get("title") if isinstance(item.get("title"), str) else ""
            detail = item.get("detail") if isinstance(item.get("detail"), str) else ""
            severity = item.get("severity") if item.get("severity") in {"low", "medium", "high"} else "low"
            node_ids_value = item.get("node_ids")
            node_ids_raw: list[Any] = cast(list[Any], node_ids_value) if isinstance(node_ids_value, list) else []
            node_ids = [str(x) for x in node_ids_raw if x is not None]
            return {"title": title, "detail": detail, "severity": severity, "node_ids": node_ids}

        cleaned_insights: list[dict] = []
        for x in insights:
            cleaned = _clean_insight(x)
            if cleaned:
                cleaned_insights.append(cleaned)

        def _clean_link(item: Any) -> dict:
            if not isinstance(item, dict):
                return {}
            source = str(item.get("source")) if item.get("source") is not None else ""
            target = str(item.get("target")) if item.get("target") is not None else ""
            label = item.get("label") if isinstance(item.get("label"), str) else ""
            reason = item.get("reason") if isinstance(item.get("reason"), str) else ""
            conf = item.get("confidence")
            try:
                confidence = float(conf) if conf is not None else 0.0
            except Exception:
                confidence = 0.0
            return {"source": source, "target": target, "label": label, "confidence": confidence, "reason": reason}

        cleaned_links: list[dict] = []
        for x in suggested_links:
            cleaned = _clean_link(x)
            if cleaned:
                cleaned_links.append(cleaned)

        cleaned_actions: list[str] = []
        for a in next_actions:
            if a is not None:
                cleaned_actions.append(str(a))

        return {
            "summary": summary,
            "insights": cleaned_insights,
            "suggested_links": cleaned_links,
            "next_actions": cleaned_actions,
        }
