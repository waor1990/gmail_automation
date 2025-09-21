import csv
import json
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Any, Dict, List, Tuple, cast

from .constants import CONFIG_BACKUPS_DIR


def read_json(p: Path) -> Dict[str, Any]:
    with p.open("r", encoding="utf-8") as f:
        return cast(Dict[str, Any], json.load(f))


def write_json(obj: dict, p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)


def backup_file(p: Path) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"{p.name}.backup_{ts}"
    target = CONFIG_BACKUPS_DIR / backup_name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(p.read_bytes())
    return target


def validate_import_file(contents: str, filename: str) -> Tuple[bool, List[str]]:
    """Validate uploaded CSV or JSON file contents.

    Parameters
    ----------
    contents:
        Raw file contents decoded as a string.
    filename:
        Name of the uploaded file used to infer its extension.

    Returns
    -------
    Tuple[bool, List[str]]
        ``(is_valid, errors)`` where ``is_valid`` indicates whether the file
        matches the expected schema and ``errors`` contains any validation
        issues to surface to the user.
    """

    required_fields = {"sender", "labels"}
    errors: List[str] = []
    ext = Path(filename).suffix.lower()

    try:
        if ext == ".json":
            data = json.loads(contents)
            if not isinstance(data, list):
                errors.append("JSON must be a list of objects")
            else:
                for idx, item in enumerate(data):
                    if not isinstance(item, dict):
                        errors.append(f"Item {idx} is not an object")
                        continue
                    missing = required_fields - item.keys()
                    if missing:
                        missing_str = ", ".join(sorted(missing))
                        errors.append(f"Item {idx} missing fields: {missing_str}")
        elif ext == ".csv":
            reader = csv.DictReader(StringIO(contents))
            header = set(reader.fieldnames or [])
            missing = required_fields - header
            if missing:
                missing_str = ", ".join(sorted(missing))
                errors.append(f"Missing columns: {missing_str}")
        else:
            errors.append("Unsupported file type")
    except Exception as exc:  # pragma: no cover - unexpected parsing issues
        errors.append(f"Failed to parse file: {exc}")

    return (not errors, errors)
