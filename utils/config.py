from __future__ import annotations

import os
from pathlib import Path


def load_env(path: Path | None = None) -> None:
    target = path or Path(__file__).resolve().parent.parent / ".env"
    if not target.exists():
        return
    for line in target.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key and key not in os.environ:
            os.environ[key] = value


load_env()

try:
    ATTACK_ANIMATION_SECONDS = float(os.getenv("ATTACK_ANIMATION_DURATION", "0.2"))
except ValueError:
    ATTACK_ANIMATION_SECONDS = 0.2
