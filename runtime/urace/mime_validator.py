"""Quality validators for MIME-typed assets.

Validators check that submitted artifacts are genuine and usable.
Raises ValueError with reason on failure. Returns True on pass.
"""
import json


def _validate_image(raw_bytes: bytes, content_type: str) -> tuple[bool, str]:
    if len(raw_bytes) < 100:
        return False, 'invalid_image_magic'
    if raw_bytes[:4] == b'\x89PNG':
        return True, 'pass'
    if raw_bytes[:3] == b'\xff\xd8\xff':
        return True, 'pass'
    if raw_bytes[:4] in (b'GIF8',):
        return True, 'pass'
    if raw_bytes[:4] == b'RIFF' and len(raw_bytes) >= 12 and raw_bytes[8:12] == b'WEBP':
        return True, 'pass'
    return False, 'invalid_image_magic'


def _validate_csv(raw_bytes: bytes, content_type: str) -> tuple[bool, str]:
    try:
        text = raw_bytes.decode('utf-8')
    except UnicodeDecodeError:
        text = raw_bytes.decode('latin-1')
    rows = [r for r in text.splitlines() if r.strip()]
    if len(rows) < 2:
        return False, 'csv_too_few_rows'
    # Check consistent column count using simple comma split
    col_counts = [len(r.split(',')) for r in rows]
    if len(set(col_counts)) > 1:
        return False, 'csv_inconsistent_columns'
    return True, 'pass'


def _validate_pdf(raw_bytes: bytes, content_type: str) -> tuple[bool, str]:
    if not raw_bytes.startswith(b'%PDF-'):
        return False, 'invalid_pdf_magic'
    if b'BT' not in raw_bytes:
        return False, 'pdf_no_text_layer'
    return True, 'pass'


def _validate_json(raw_bytes: bytes, content_type: str) -> tuple[bool, str]:
    try:
        data = json.loads(raw_bytes)
    except (json.JSONDecodeError, ValueError):
        return False, 'json_invalid'
    if data == {} or data == []:
        return False, 'json_empty'
    return True, 'pass'


def _validate_code(raw_bytes: bytes, content_type: str) -> tuple[bool, str]:
    try:
        text = raw_bytes.decode('utf-8')
    except UnicodeDecodeError:
        return False, 'code_not_utf8'
    non_blank = [l for l in text.splitlines() if l.strip()]
    if len(non_blank) < 3:
        return False, 'code_too_short'
    return True, 'pass'


def _validate_zip(raw_bytes: bytes, content_type: str) -> tuple[bool, str]:
    if not raw_bytes.startswith(b'PK\x03\x04'):
        return False, 'invalid_zip_magic'
    # Check at least one member: scan for local file header signature
    # PK\x03\x04 is the local file header; count occurrences beyond position 0
    count = raw_bytes.count(b'PK\x03\x04')
    if count < 1:
        return False, 'zip_empty'
    return True, 'pass'


def validate_asset(raw_bytes: bytes, content_type: str) -> tuple[bool, str]:
    """Validate asset bytes against content_type.

    Returns (True, 'pass') or (True, 'unvalidated') on success,
    (False, reason) on failure.
    """
    ct = (content_type or '').lower().split(';')[0].strip()

    if ct.startswith('image/'):
        return _validate_image(raw_bytes, ct)

    if ct in ('text/csv', 'application/csv'):
        return _validate_csv(raw_bytes, ct)

    if ct == 'application/pdf':
        return _validate_pdf(raw_bytes, ct)

    if ct == 'application/json':
        return _validate_json(raw_bytes, ct)

    if ct in ('text/x-python', 'application/x-python', 'text/plain'):
        return _validate_code(raw_bytes, ct)

    if ct in ('application/zip', 'application/x-zip', 'application/x-zip-compressed'):
        return _validate_zip(raw_bytes, ct)

    return True, 'unvalidated'


def validate_asset_strict(raw_bytes: bytes, content_type: str) -> None:
    """Like validate_asset but raises ValueError on failure."""
    ok, reason = validate_asset(raw_bytes, content_type)
    if not ok:
        raise ValueError(reason)
