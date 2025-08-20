import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, cast


def read_json(p: Path) -> Dict[str, Any]:
    with p.open("r", encoding="utf-8") as f:
        return cast(Dict[str, Any], json.load(f))


def write_json(obj: dict, p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)


def backup_file(p: Path) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bkp = p.with_suffix(p.suffix + f".backup_{ts}")
    bkp.parent.mkdir(parents=True, exist_ok=True)
    bkp.write_bytes(p.read_bytes())
    return bkp
