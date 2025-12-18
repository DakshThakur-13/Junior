"""Judge Analytics Agent.

Generates a structured judicial tendency/profile report from provided judgment text.
Designed to work even without a configured database: the client can pass judgment
excerpts directly.

Strict JSON output.
"""

from __future__ import annotations

import json
import re
from typing import Any, Optional

from junior.core.types import AgentRole

from .base import AgentState, BaseAgent

class JudgeAnalyticsAgent(BaseAgent):
    role = AgentRole.CRITIC

    @property
    def system_prompt(self) -> str:
        return (
            "You are a judicial analytics expert for Indian courts. "
            "You ONLY use the provided judgment excerpts. "
            "Do NOT fabricate statistics, case counts, or citations. "
            "If evidence is insufficient, state limitations. "
            "Return ONLY valid JSON matching the schema."
        )

    async def process(self, state: AgentState) -> AgentState:
        # Not used in LangGraph today.
        return state

    async def analyze(
        self,
        *,
        judge_name: str,
        court: Optional[str] = None,
        case_type: Optional[str] = None,
        judgments: list[str],
    ) -> dict:
        prompt = self._build_prompt(judge_name=judge_name, court=court, case_type=case_type, judgments=judgments)
        raw = await self.invoke_llm(prompt)
        parsed = self._parse_json(raw)
        return self._coerce_response(parsed, judge_name=judge_name)

    def _build_prompt(
        self,
        *,
        judge_name: str,
        court: Optional[str],
        case_type: Optional[str],
        judgments: list[str],
    ) -> str:
        ctx = {
            "judge_name": judge_name,
            "court": court,
            "case_type": case_type,
            "judgments": judgments,
        }
        return (
            "JUDGE ANALYTICS\n\n"
            "CONTEXT:\n"
            f"{json.dumps(ctx, ensure_ascii=False)}\n\n"
            "TASK:\n"
            "Analyze the judge's tendencies ONLY from the provided excerpts.\n"
            "Extract qualitative patterns (e.g., strictness in bail, approach to adjournments, emphasis on procedural compliance).\n"
            "Do not claim numeric rates unless the excerpts contain them explicitly.\n\n"
            "OUTPUT JSON SCHEMA (return only JSON):\n"
            "{\n"
            '  "judge_name": string,\n'
            '  "total_cases_analyzed": number,\n'
            '  "patterns": [\n'
            "    {\n"
            '      "pattern": string,\n'
            '      "signal": "low"|"medium"|"high",\n'
            '      "evidence": [string],\n'
            '      "caveats": [string]\n'
            "    }\n"
            "  ],\n"
            '  "recommendations": [string]\n'
            "}\n"
        )

    def _parse_json(self, text: str) -> dict:
        text = (text or "").strip()
        try:
            value = json.loads(text)
            if isinstance(value, dict):
                return value
        except Exception:
            pass

        m = re.search(r"\{[\s\S]*\}", text)
        if m:
            try:
                value = json.loads(m.group(0))
                if isinstance(value, dict):
                    return value
            except Exception:
                pass

        return {}

    def _coerce_response(self, value: dict, *, judge_name: str) -> dict:
        out_judge = value.get("judge_name") if isinstance(value.get("judge_name"), str) else judge_name

        tca = value.get("total_cases_analyzed")
        if isinstance(tca, (int, float)) and tca >= 0:
            total_cases_analyzed = int(tca)
        else:
            total_cases_analyzed = 0

        patterns_value: Any = value.get("patterns")
        patterns: list[dict] = []
        if isinstance(patterns_value, list):
            for item in patterns_value:
                if not isinstance(item, dict):
                    continue
                pattern = item.get("pattern") if isinstance(item.get("pattern"), str) else ""
                signal = item.get("signal") if item.get("signal") in {"low", "medium", "high"} else "low"

                ev_raw = item.get("evidence")
                evidence: list[str] = []
                if isinstance(ev_raw, list):
                    evidence = [str(x) for x in ev_raw if x is not None][:6]

                cav_raw = item.get("caveats")
                caveats: list[str] = []
                if isinstance(cav_raw, list):
                    caveats = [str(x) for x in cav_raw if x is not None][:6]

                if pattern:
                    patterns.append(
                        {
                            "pattern": pattern,
                            "signal": signal,
                            "evidence": evidence,
                            "caveats": caveats,
                        }
                    )

        recs_value: Any = value.get("recommendations")
        recommendations: list[str] = []
        if isinstance(recs_value, list):
            recommendations = [str(x) for x in recs_value if x is not None][:10]

        return {
            "judge_name": out_judge,
            "total_cases_analyzed": total_cases_analyzed,
            "patterns": patterns,
            "recommendations": recommendations,
        }
