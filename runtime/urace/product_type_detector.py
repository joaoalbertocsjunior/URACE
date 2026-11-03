from __future__ import annotations
import os
from pathlib import Path

_TYPE_SIGNALS: dict[str, list[str]] = {
    "software": [".py", ".js", ".ts", ".go", ".rs", ".java", ".rb", ".c", ".cpp", ".cs", "Makefile", "pyproject.toml", "package.json", "Cargo.toml", "go.mod"],
    "media":    [".mp4", ".mov", ".avi", ".mkv", ".mp3", ".wav", ".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".blend"],
    "model":    [".pt", ".pth", ".pkl", ".h5", ".onnx", ".safetensors", ".bin", "train.py", "train.sh", "Makefile"],
    "data":     [".csv", ".parquet", ".jsonl", ".tsv", ".avro", ".feather", ".db", ".sqlite"],
    "content":  [".md", ".txt", ".rst", ".html", ".docx", ".pdf"],
}

_PRIORITY = ["software", "model", "data", "media", "content"]


def detect_product_types(root: Path, max_depth: int = 3) -> list[str]:
    """Scan directory tree and infer product types from file extensions/names."""
    scores: dict[str, int] = {t: 0 for t in _TYPE_SIGNALS}
    for dirpath, dirnames, filenames in os.walk(root):
        # Prune deep directories and common noise dirs
        rel = Path(dirpath).relative_to(root)
        if len(rel.parts) >= max_depth:
            dirnames.clear()
            continue
        for skip in (".git", "node_modules", "__pycache__", ".venv", "venv", "urace"):
            if skip in dirnames:
                dirnames.remove(skip)
        for name in filenames:
            lower = name.lower()
            ext = os.path.splitext(lower)[1]
            for ptype, signals in _TYPE_SIGNALS.items():
                if ext in signals or lower in signals:
                    scores[ptype] += 1
    detected = [t for t in _PRIORITY if scores[t] > 0]
    if not detected:
        return ["software"]
    # If software score is dominant, only return software (avoids spurious content from README)
    sw = scores["software"]
    total = sum(scores.values())
    if sw > 0 and sw / max(total, 1) > 0.6:
        return ["software"]
    return detected


def normalize_types(raw: "str | list | None") -> list:
    """Normalize --type input: flat list, nested list (legacy append), or comma/space string."""
    valid = set(_TYPE_SIGNALS)
    if raw is None:
        return ["software"]
    items: list = raw if isinstance(raw, list) else [raw]
    types: list = []
    for item in items:
        if isinstance(item, list):
            items.extend(item)
            continue
        for t in str(item).replace(",", " ").split():
            t = t.strip().lower()
            if t in valid and t not in types:
                types.append(t)
    return types or ["software"]
