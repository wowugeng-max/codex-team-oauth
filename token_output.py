import base64
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping
from zoneinfo import ZoneInfo


PACIFIC_TZ = ZoneInfo("America/Los_Angeles")


def format_codex_token_payload(email: str, token_response: Mapping[str, Any]) -> dict[str, Any]:
    access_token = str(token_response.get("access_token", "") or "")
    id_token = str(token_response.get("id_token", "") or "")
    refresh_token = str(token_response.get("refresh_token", "") or "")
    access_payload = decode_jwt_payload(access_token)
    id_payload = decode_jwt_payload(id_token)

    account_id = (
        (access_payload.get("https://api.openai.com/auth") or {}).get("chatgpt_account_id")
        or (id_payload.get("https://api.openai.com/auth") or {}).get("chatgpt_account_id")
        or ""
    )
    resolved_email = (
        str(email or "").strip()
        or str((access_payload.get("https://api.openai.com/profile") or {}).get("email") or "").strip()
        or str(id_payload.get("email") or "").strip()
    )

    return {
        "access_token": access_token,
        "account_id": str(account_id),
        "disabled": False,
        "email": resolved_email,
        "expired": timestamp_to_pacific_iso(access_payload.get("exp")),
        "id_token": id_token,
        "last_refresh": timestamp_to_pacific_iso(access_payload.get("iat") or id_payload.get("iat")),
        "refresh_token": refresh_token,
        "type": "codex",
    }


def save_codex_token_json(
    email: str,
    token_response: Mapping[str, Any],
    *,
    project_dir: str | Path,
) -> Path:
    output_dir = Path(project_dir) / "result" / "json"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / (safe_token_filename(email) + ".json")
    payload = format_codex_token_payload(email, token_response)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    return output_path


def format_saved_path_for_log(saved_path: str | Path, *, project_dir: str | Path) -> str:
    path = Path(saved_path)
    try:
        path = path.relative_to(Path(project_dir))
    except ValueError:
        pass
    return path.as_posix()


def decode_jwt_payload(token: str) -> dict[str, Any]:
    parts = str(token or "").split(".")
    if len(parts) < 2 or not parts[1]:
        return {}
    raw = parts[1]
    padding = "=" * ((4 - len(raw) % 4) % 4)
    try:
        decoded = base64.urlsafe_b64decode((raw + padding).encode("ascii"))
        payload = json.loads(decoded.decode("utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def timestamp_to_pacific_iso(value: Any) -> str:
    if value in (None, ""):
        return ""
    try:
        timestamp = int(value)
    except (TypeError, ValueError):
        return ""
    return datetime.fromtimestamp(timestamp, tz=PACIFIC_TZ).replace(microsecond=0).isoformat()


def safe_token_filename(email: str) -> str:
    value = str(email or "").strip() or "codex_token"
    for ch in ("/", "\\", ":", "\x00"):
        value = value.replace(ch, "_")
    return value
