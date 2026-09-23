"""Estat persistent de deduplicació.

Un sol document JSON amb escriptura atòmica (write temp + os.replace) perquè
un reinici del procés no provoqui avisos duplicats. Vegeu design.md D7.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .logging_setup import get_logger

log = get_logger(__name__)

STATE_VERSION = 1


def now_iso() -> str:
    """Marca de temps UTC en ISO 8601."""
    return datetime.now(timezone.utc).isoformat()


@dataclass
class State:
    rss_guids: list[str] = field(default_factory=list)
    carta_url: str | None = None
    cal_hash: str | None = None
    ultima_novetat: str | None = None
    intent_errors: dict[str, int] = field(default_factory=dict)
    baseline_done: bool = False
    version: int = STATE_VERSION

    # --- càrrega / guardat -------------------------------------------------
    @classmethod
    def load(cls, path: str | Path) -> "State":
        """Carrega l'estat. Si no existeix, retorna un estat buit (primera execució)."""
        p = Path(path)
        if not p.exists():
            log.info("Estat inexistent a %s: primera execució (línia base).", p)
            return cls()
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            log.error("No s'ha pogut llegir l'estat %s (%s); es comença de nou.", p, exc)
            return cls()
        if not isinstance(data, dict):
            log.error("Estat %s invàlid; es comença de nou.", p)
            return cls()
        return cls(
            rss_guids=list(data.get("rss_guids") or []),
            carta_url=data.get("carta_url"),
            cal_hash=data.get("cal_hash"),
            ultima_novetat=data.get("ultima_novetat"),
            intent_errors=dict(data.get("intent_errors") or {}),
            baseline_done=bool(data.get("baseline_done", False)),
            version=int(data.get("version", STATE_VERSION)),
        )

    def save(self, path: str | Path) -> None:
        """Guarda l'estat de forma atòmica (temp al mateix directori + replace)."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": self.version,
            "rss_guids": self.rss_guids,
            "carta_url": self.carta_url,
            "cal_hash": self.cal_hash,
            "ultima_novetat": self.ultima_novetat,
            "intent_errors": self.intent_errors,
            "baseline_done": self.baseline_done,
        }
        fd, tmp_name = tempfile.mkstemp(dir=str(p.parent), prefix=".state-", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, ensure_ascii=False, indent=2)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp_name, p)
        finally:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)

    # --- helpers -----------------------------------------------------------
    @property
    def is_new(self) -> bool:
        """True si no hi ha cap línia base encara (primera execució real)."""
        return (
            not self.rss_guids
            and self.carta_url is None
            and self.cal_hash is None
            and self.ultima_novetat is None
        )

    def knows_rss(self, guid: str) -> bool:
        return guid in self.rss_guids

    def remember_rss(self, guid: str) -> None:
        if guid not in self.rss_guids:
            self.rss_guids.append(guid)

    def mark_change(self) -> None:
        """Registra que hi ha hagut una novetat (alimenta el sondeig adaptatiu)."""
        self.ultima_novetat = now_iso()

    def bump_error(self, source: str) -> None:
        self.intent_errors[source] = self.intent_errors.get(source, 0) + 1

    def clear_error(self, source: str) -> None:
        if source in self.intent_errors:
            self.intent_errors.pop(source, None)
