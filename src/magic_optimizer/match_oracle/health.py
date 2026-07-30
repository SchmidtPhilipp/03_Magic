from __future__ import annotations

import os
from pathlib import Path


def forge_available(*, jar: str | None = None, java: str = "java") -> bool:
    del java  # observe-only: no process start
    jar_path = jar if jar is not None else os.environ.get("FORGE_JAR")
    if not jar_path:
        return False
    return Path(jar_path).is_file()
