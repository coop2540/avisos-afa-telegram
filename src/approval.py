"""Aprovació de sol·licituds d'unió al grup (semi-automàtica).

Rep `chat_join_request` (via long polling per defecte), avisa l'administrador
amb botons i aplica la seva decisió. Els filtres heurístics opcionals només
poden **rebutjar**, mai aprovar. Vegeu design.md D1–D7.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from .config import ApprovalConfig, Config
from .logging_setup import get_logger
from .state import State
from .telegram_out import API_BASE, TelegramClient

log = get_logger(__name__)

# Patrons de bio/usuari que solen indicar comptes de spam (heurística simple).
SPAM_PATTERNS = (
    "http://", "https://", "t.me/", "trial", "free", "crypto", "invest",
    "bitcoin", "viagra", "casino", "porn", "xxx", "get rich",
)


@dataclass
class JoinRequest:
    user_id: int
    chat_id: int
    first_name: str = ""
    last_name: str = ""
    username: str = ""
    bio: str = ""

    @property
    def display_name(self) -> str:
        name = f"{self.first_name} {self.last_name}".strip()
        return name or "(sense nom)"

    @property
    def handle(self) -> str:
        return f"@{self.username}" if self.username else "(sense usuari)"


def parse_join_request(update: dict[str, Any]) -> JoinRequest | None:
    """Extreu una JoinRequest d'un update de Telegram, o None si no ho és."""
    req = update.get("chat_join_request")
    if not isinstance(req, dict):
        return None
    user = req.get("from") or {}
    chat = req.get("chat") or {}
    if "id" not in user or "id" not in chat:
        return None
    return JoinRequest(
        user_id=int(user["id"]),
        chat_id=int(chat["id"]),
        first_name=str(user.get("first_name") or ""),
        last_name=str(user.get("last_name") or ""),
        username=str(user.get("username") or ""),
        bio=str(req.get("bio") or user.get("bio") or ""),
    )


def should_auto_reject(jr: JoinRequest, cfg: ApprovalConfig) -> str | None:
    """Retorna el motiu de rebuig automàtic, o None si ha de decidir l'admin."""
    ar = cfg.auto_reject
    if not ar.enabled:
        return None
    name = jr.display_name.strip()
    if ar.block_empty_name and (not name or name == "(sense nom)" or name.isdigit()):
        return "nom buit o numèric"
    if ar.block_spam_bio:
        haystack = f"{jr.username} {jr.bio}".lower()
        for spam in SPAM_PATTERNS:
            if spam in haystack:
                return f"patró sospitós («{spam}»)"
    return None


def approval_notice(jr: JoinRequest) -> str:
    lines = [
        "🔔 <b>Nova sol·licitud d'unió</b>",
        f"Nom: {jr.display_name}",
        f"Usuari: {jr.handle}",
        f"ID: <code>{jr.user_id}</code>",
    ]
    if jr.bio:
        lines.append(f"Bio: {jr.bio}")
    lines.append("Vol entrar al grup. Què fem?")
    return "\n".join(lines)


def decision_keyboard(user_id: int) -> dict[str, Any]:
    return {
        "inline_keyboard": [
            [
                {"text": "✅ Aprovar", "callback_data": f"apr:{user_id}"},
                {"text": "❌ Rebutjar", "callback_data": f"rej:{user_id}"},
            ]
        ]
    }


class ApprovalService:
    """Gestiona la recepció d'updates i les decisions d'aprovació."""

    def __init__(self, cfg: Config, state: State, client: TelegramClient | None = None) -> None:
        self.cfg = cfg
        self.state = state
        self._owns_client = client is None
        self.client = client or TelegramClient(
            cfg.telegram.token, cfg.telegram.chat_id, dry_run=cfg.telegram.dry_run
        )
        self._offset: int | None = None

    def close(self) -> None:
        if self._owns_client:
            self.client.close()

    # --- API helpers -------------------------------------------------------
    def _api(self, method: str, **params: Any) -> dict[str, Any]:
        token = self.cfg.telegram.token
        if not token:
            return {"ok": False, "description": "sense token"}
        url = f"{API_BASE}/bot{token}/{method}"
        try:
            resp = httpx.post(url, json=params, timeout=40)
            return resp.json()
        except httpx.HTTPError as exc:
            log.warning("Telegram %s ha fallat: %s", method, exc)
            return {"ok": False, "description": str(exc)}

    def _get_updates(self, timeout: int = 30) -> list[dict[str, Any]]:
        token = self.cfg.telegram.token
        if not token:
            return []
        url = f"{API_BASE}/bot{token}/getUpdates"
        params: dict[str, Any] = {"timeout": timeout, "allowed_updates": ["chat_join_request", "callback_query"]}
        if self._offset is not None:
            params["offset"] = self._offset
        try:
            resp = httpx.get(url, params=params, timeout=timeout + 15)
            data = resp.json()
        except httpx.HTTPError as exc:
            log.warning("getUpdates ha fallat: %s", exc)
            return []
        if not data.get("ok"):
            log.warning("getUpdates no OK: %s", data.get("description"))
            return []
        return data.get("result") or []

    def ensure_polling_ready(self) -> None:
        """Neteja qualsevol webhook per poder fer long polling."""
        info = self._api("deleteWebhook", drop_pending_updates=False)
        log.info("Webhook netejat per a polling: ok=%s", info.get("ok"))

    # --- processament ------------------------------------------------------
    def process_update(self, update: dict[str, Any]) -> None:
        if "chat_join_request" in update:
            self._handle_join_request(update)
        elif "callback_query" in update:
            self._handle_callback(update)

    def _handle_join_request(self, update: dict[str, Any]) -> None:
        jr = parse_join_request(update)
        if jr is None:
            return
        if self.state.is_join_notified(jr.user_id):
            log.info("Sol·licitud de %s ja notificada; s'ignora.", jr.user_id)
            return
        if not self.cfg.telegram.admin_chat_id:
            log.error("Sol·licitud rebuda però no hi ha admin_chat_id configurat.")
            return

        reason = should_auto_reject(jr, self.cfg.telegram.approval)
        if reason:
            self._decide(jr, approve=False, actor="auto")
            self._notify(jr, extra=f"\n\n⛔️ Rebutjada automàticament: {reason}")
            self.state.remember_join(jr.user_id, "declined")
            self.state.save(self.cfg.state_path)
            log.info("Sol·licitud %s rebutjada automàticament (%s).", jr.user_id, reason)
            return

        self._notify(jr)
        self.state.remember_join(jr.user_id, "notified")
        self.state.save(self.cfg.state_path)
        log.info("Sol·licitud notificada a l'admin: %s", jr.user_id)

    def _notify(self, jr: JoinRequest, extra: str = "") -> None:
        text = approval_notice(jr) + extra
        params: dict[str, Any] = {
            "chat_id": self.cfg.telegram.admin_chat_id,
            "text": text,
            "parse_mode": "HTML",
        }
        if not extra:  # només els avisos pendents porten botons
            params["reply_markup"] = decision_keyboard(jr.user_id)
        self._api("sendMessage", **params)

    def _handle_callback(self, update: dict[str, Any]) -> None:
        cq = update.get("callback_query") or {}
        data = str(cq.get("data") or "")
        cq_id = cq.get("id")
        message = cq.get("message") or {}
        chat = message.get("chat") or {}
        # Només acceptem decisions del xat de l'admin
        if str(chat.get("id")) != str(self.cfg.telegram.admin_chat_id):
            if cq_id:
                self._api("answerCallbackQuery", callback_query_id=cq_id, text="No autoritzat.")
            return

        if ":" not in data:
            return
        action, _, uid = data.partition(":")
        if not uid.isdigit():
            return
        user_id = int(uid)

        status = self.state.join_status(user_id)
        if status in {"approved", "declined"}:
            if cq_id:
                self._api("answerCallbackQuery", callback_query_id=cq_id, text="Ja està decidit.")
            return

        jr = JoinRequest(user_id=user_id, chat_id=int(self.cfg.telegram.chat_id or 0))
        approve = action == "apr"
        ok = self._decide(jr, approve=approve, actor="admin")
        self.state.remember_join(user_id, "approved" if approve else "declined")
        self.state.save(self.cfg.state_path)

        if cq_id:
            self._api(
                "answerCallbackQuery",
                callback_query_id=cq_id,
                text="Aprovat ✅" if approve else "Rebutjat ❌",
            )
        # Editar el missatge per treure botons i deixar constància
        if message.get("message_id"):
            self._api(
                "editMessageReplyMarkup",
                chat_id=self.cfg.telegram.admin_chat_id,
                message_id=message["message_id"],
                reply_markup={"inline_keyboard": []},
            )
        if not ok:
            self._api(
                "sendMessage",
                chat_id=self.cfg.telegram.admin_chat_id,
                text=f"⚠️ No s'ha pogut aplicar la decisió per a {user_id} (potser ja no és vàlida).",
            )

    def _decide(self, jr: JoinRequest, *, approve: bool, actor: str) -> bool:
        method = "approveChatJoinRequest" if approve else "declineChatJoinRequest"
        res = self._api(method, chat_id=jr.chat_id or self.cfg.telegram.chat_id, user_id=jr.user_id)
        ok = bool(res.get("ok"))
        log.info("%s user=%s per %s: ok=%s", method, jr.user_id, actor, ok)
        return ok

    def run_forever(self) -> None:
        """Bucle de long polling (bloquejant)."""
        if self.cfg.telegram.approval.receive == "webhook":
            log.info("Mode webhook configurat; no s'inicia polling.")
            return
        self.ensure_polling_ready()
        log.info("Comença el polling de sol·licituds d'unió.")
        while True:
            updates = self._get_updates()
            for update in updates:
                self._offset = int(update.get("update_id", 0)) + 1
                try:
                    self.process_update(update)
                except Exception as exc:  # un update dolent no atura el servei
                    log.exception("Error processant update: %s", exc)
