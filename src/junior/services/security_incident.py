"""Security incident response service for Phase 1 (Detection) and Phase 2 (Containment)."""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from threading import RLock
from typing import Any
from uuid import uuid4

from junior.core import get_logger

logger = get_logger(__name__)


FAILED_LOGIN_WINDOW_SECONDS = 60
FAILED_LOGIN_THRESHOLD = 5


@dataclass
class SecurityAlert:
    id: str
    kind: str
    severity: str
    message: str
    source_ip: str | None
    created_at: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class SecurityIncident:
    id: str
    title: str
    summary: str
    status: str
    phase: int
    created_at: str
    detected_at: str
    notified_at: str | None = None
    assessment_started_at: str | None = None
    containment_started_at: str | None = None
    contained_at: str | None = None
    affected_systems: list[str] = field(default_factory=list)
    blocked_ips: list[str] = field(default_factory=list)
    revoked_credentials: list[str] = field(default_factory=list)
    evidence_items: list[dict[str, Any]] = field(default_factory=list)
    timeline: list[dict[str, Any]] = field(default_factory=list)


class SecurityIncidentService:
    def __init__(self) -> None:
        self._lock = RLock()
        self._alerts: deque[SecurityAlert] = deque(maxlen=2000)
        self._incidents: dict[str, SecurityIncident] = {}
        self._blocked_ips: set[str] = set()
        self._isolated_systems: set[str] = set()
        self._revoked_credentials: set[str] = set()
        self._failed_logins: dict[str, deque[datetime]] = defaultdict(deque)

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def _iso(self) -> str:
        return self._now().isoformat()

    def _timeline_event(self, incident: SecurityIncident, action: str, details: dict[str, Any] | None = None) -> None:
        incident.timeline.append(
            {
                "timestamp": self._iso(),
                "action": action,
                "details": details or {},
            }
        )

    def create_alert(
        self,
        kind: str,
        severity: str,
        message: str,
        source_ip: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            alert = SecurityAlert(
                id=f"alert_{uuid4().hex[:12]}",
                kind=kind,
                severity=severity,
                message=message,
                source_ip=source_ip,
                created_at=self._iso(),
                details=details or {},
            )
            self._alerts.appendleft(alert)
            return self._alert_to_dict(alert)

    def start_phase1_detection(
        self,
        title: str,
        summary: str,
        source_ip: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            incident_id = f"inc_{uuid4().hex[:12]}"
            now = self._iso()
            incident = SecurityIncident(
                id=incident_id,
                title=title,
                summary=summary,
                status="detected",
                phase=1,
                created_at=now,
                detected_at=now,
                notified_at=now,
                assessment_started_at=now,
            )
            incident.timeline.append({"timestamp": now, "action": "automated_alert_triggered", "details": details or {}})
            incident.timeline.append({"timestamp": now, "action": "security_team_notified", "details": {}})
            incident.timeline.append({"timestamp": now, "action": "initial_assessment_started", "details": {}})
            self._incidents[incident.id] = incident

            self._alerts.appendleft(
                SecurityAlert(
                    id=f"alert_{uuid4().hex[:12]}",
                    kind="incident_detection",
                    severity="high",
                    message=title,
                    source_ip=source_ip,
                    created_at=now,
                    details=details or {},
                )
            )

            logger.warning("Security incident detected: %s (%s)", incident.title, incident.id)
            return self._incident_to_dict(incident)

    def run_phase2_containment(
        self,
        incident_id: str,
        systems: list[str] | None = None,
        ips: list[str] | None = None,
        credential_ids: list[str] | None = None,
        evidence_note: str | None = None,
        evidence_artifacts: list[str] | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            incident = self._incidents.get(incident_id)
            if not incident:
                raise KeyError(f"Incident not found: {incident_id}")

            now = self._iso()
            incident.phase = 2
            incident.status = "containment_in_progress"
            if not incident.containment_started_at:
                incident.containment_started_at = now
                self._timeline_event(incident, "containment_started")

            for system_id in systems or []:
                if system_id not in self._isolated_systems:
                    self._isolated_systems.add(system_id)
                    incident.affected_systems.append(system_id)
                    self._timeline_event(incident, "system_isolated", {"system_id": system_id})

            for ip in ips or []:
                if ip not in self._blocked_ips:
                    self._blocked_ips.add(ip)
                    incident.blocked_ips.append(ip)
                    self._timeline_event(incident, "ip_blocked", {"ip": ip})

            for credential_id in credential_ids or []:
                if credential_id not in self._revoked_credentials:
                    self._revoked_credentials.add(credential_id)
                    incident.revoked_credentials.append(credential_id)
                    self._timeline_event(incident, "credential_revoked", {"credential_id": credential_id})

            if evidence_note or evidence_artifacts:
                evidence_item = {
                    "id": f"evid_{uuid4().hex[:10]}",
                    "captured_at": now,
                    "note": evidence_note or "evidence_preserved",
                    "artifacts": evidence_artifacts or [],
                }
                incident.evidence_items.append(evidence_item)
                self._timeline_event(incident, "evidence_preserved", evidence_item)

            incident.status = "contained"
            incident.contained_at = self._iso()
            self._timeline_event(incident, "containment_completed")
            logger.warning("Security incident contained: %s", incident.id)
            return self._incident_to_dict(incident)

    def record_failed_login(self, email: str, source_ip: str | None = None) -> dict[str, Any] | None:
        key = f"{(source_ip or 'unknown').strip()}::{email.strip().lower()}"
        with self._lock:
            now = self._now()
            bucket = self._failed_logins[key]
            bucket.append(now)

            cutoff = now - timedelta(seconds=FAILED_LOGIN_WINDOW_SECONDS)
            while bucket and bucket[0] < cutoff:
                bucket.popleft()

            attempts = len(bucket)
            if attempts < FAILED_LOGIN_THRESHOLD:
                return None

            source = source_ip or "unknown"
            alert = self.create_alert(
                kind="failed_login_spike",
                severity="high",
                message=f"{attempts} failed sign-in attempts for {email} in {FAILED_LOGIN_WINDOW_SECONDS}s",
                source_ip=source,
                details={"attempts": attempts, "email": email},
            )
            incident = self.start_phase1_detection(
                title="Potential credential attack detected",
                summary=f"Repeated failed login attempts detected for account {email} from {source}",
                source_ip=source,
                details={"alert_id": alert["id"], "attempts": attempts, "email": email},
            )
            return incident

    def clear_failed_login_window(self, email: str, source_ip: str | None = None) -> None:
        key = f"{(source_ip or 'unknown').strip()}::{email.strip().lower()}"
        with self._lock:
            if key in self._failed_logins:
                self._failed_logins.pop(key, None)

    def get_status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "alerts": [self._alert_to_dict(alert) for alert in list(self._alerts)[:100]],
                "incidents": [self._incident_to_dict(v) for v in self._incidents.values()],
                "blocked_ips": sorted(self._blocked_ips),
                "isolated_systems": sorted(self._isolated_systems),
                "revoked_credentials": sorted(self._revoked_credentials),
                "summary": {
                    "total_alerts": len(self._alerts),
                    "total_incidents": len(self._incidents),
                    "active_incidents": sum(1 for i in self._incidents.values() if i.status != "contained"),
                },
            }

    @staticmethod
    def _alert_to_dict(alert: SecurityAlert) -> dict[str, Any]:
        return {
            "id": alert.id,
            "kind": alert.kind,
            "severity": alert.severity,
            "message": alert.message,
            "source_ip": alert.source_ip,
            "created_at": alert.created_at,
            "details": alert.details,
        }

    @staticmethod
    def _incident_to_dict(incident: SecurityIncident) -> dict[str, Any]:
        return {
            "id": incident.id,
            "title": incident.title,
            "summary": incident.summary,
            "status": incident.status,
            "phase": incident.phase,
            "created_at": incident.created_at,
            "detected_at": incident.detected_at,
            "notified_at": incident.notified_at,
            "assessment_started_at": incident.assessment_started_at,
            "containment_started_at": incident.containment_started_at,
            "contained_at": incident.contained_at,
            "affected_systems": incident.affected_systems,
            "blocked_ips": incident.blocked_ips,
            "revoked_credentials": incident.revoked_credentials,
            "evidence_items": incident.evidence_items,
            "timeline": incident.timeline,
        }


_incident_service = SecurityIncidentService()


def get_incident_service() -> SecurityIncidentService:
    return _incident_service
