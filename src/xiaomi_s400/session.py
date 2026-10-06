"""Credential storage outside the checkout."""

import json
import os
import tempfile
from pathlib import Path

from .errors import AuthenticationError, InputError

DEFAULT_SESSION = Path.home() / ".config" / "xiaomi-s400" / "session.json"


def credentials(data: object) -> dict[str, str]:
    if not isinstance(data, dict):
        raise InputError()
    user = data.get("userId")
    token = data.get("passToken") or data.get("pass_token")
    if isinstance(user, bool) or not isinstance(user, (int, str)) or not str(user).isdigit():
        raise InputError()
    if not isinstance(token, str) or not token or any(ord(c) < 33 or ord(c) > 126 or c == ";" for c in token):
        raise InputError()
    return {"userId": str(user), "passToken": token}


def load_session(path: Path) -> dict[str, str]:
    try:
        return credentials(json.loads(Path(path).read_text(encoding="utf-8")))
    except (OSError, ValueError, InputError):
        raise AuthenticationError() from None


def save_session(path: Path, data: object) -> None:
    payload = credentials(data)
    path = Path(path).expanduser()
    temporary = None
    try:
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=".session-", dir=path.parent)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(payload, stream)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except OSError:
        raise InputError() from None
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)
