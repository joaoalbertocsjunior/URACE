"""Tests for mime_validator.py — 15+ cases covering each validator (pass + fail) and strict."""
import io
import json
import struct
import pytest

from urace.mime_validator import validate_asset, validate_asset_strict


# ── helpers ──────────────────────────────────────────────────────────────────

def _png():
    return b'\x89PNG' + b'\x00' * 200


def _jpeg():
    return b'\xff\xd8\xff' + b'\x00' * 200


def _gif():
    return b'GIF8' + b'\x00' * 200


def _webp():
    return b'RIFF' + b'\x00\x00\x00\x00' + b'WEBP' + b'\x00' * 200


def _csv_good():
    return b'name,age,city\nAlice,30,NY\nBob,25,LA\n'


def _csv_bad_cols():
    return b'name,age\nAlice,30,NY\n'


def _pdf_good():
    return b'%PDF-1.4 some content BT (Hello) Tj ET'


def _pdf_no_text():
    return b'%PDF-1.4 no text marker here'


def _json_good():
    return json.dumps({'key': 'value'}).encode()


def _json_empty_dict():
    return b'{}'


def _json_empty_list():
    return b'[]'


def _code_good():
    return b'def foo():\n    pass\n\ndef bar():\n    return 1\n'


def _code_short():
    return b'x = 1\n'


def _zip_good():
    # minimal ZIP with one member: local file header (PK\x03\x04) + data + end of central dir
    lf = b'PK\x03\x04' + b'\x00' * 26 + b'\x00\x00'  # local file header stub
    eocd = b'PK\x05\x06' + b'\x00' * 18
    return lf + eocd


def _zip_bad():
    return b'\x00\x00\x00\x00notazip'


# ── image tests ───────────────────────────────────────────────────────────────

def test_image_png_pass():
    ok, reason = validate_asset(_png(), 'image/png')
    assert ok and reason == 'pass'


def test_image_jpeg_pass():
    ok, reason = validate_asset(_jpeg(), 'image/jpeg')
    assert ok and reason == 'pass'


def test_image_gif_pass():
    ok, reason = validate_asset(_gif(), 'image/gif')
    assert ok and reason == 'pass'


def test_image_webp_pass():
    ok, reason = validate_asset(_webp(), 'image/webp')
    assert ok and reason == 'pass'


def test_image_bad_magic():
    ok, reason = validate_asset(b'\x00' * 200, 'image/png')
    assert not ok and reason == 'invalid_image_magic'


def test_image_too_short():
    ok, reason = validate_asset(b'\x89PNG' + b'\x00' * 10, 'image/png')
    assert not ok and reason == 'invalid_image_magic'


# ── CSV tests ─────────────────────────────────────────────────────────────────

def test_csv_good():
    ok, reason = validate_asset(_csv_good(), 'text/csv')
    assert ok and reason == 'pass'


def test_csv_inconsistent_columns():
    ok, reason = validate_asset(_csv_bad_cols(), 'text/csv')
    assert not ok and reason == 'csv_inconsistent_columns'


def test_csv_too_few_rows():
    ok, reason = validate_asset(b'name,age\n', 'text/csv')
    assert not ok


# ── PDF tests ─────────────────────────────────────────────────────────────────

def test_pdf_good():
    ok, reason = validate_asset(_pdf_good(), 'application/pdf')
    assert ok and reason == 'pass'


def test_pdf_no_text_layer():
    ok, reason = validate_asset(_pdf_no_text(), 'application/pdf')
    assert not ok and reason == 'pdf_no_text_layer'


def test_pdf_bad_magic():
    ok, reason = validate_asset(b'not a pdf BT', 'application/pdf')
    assert not ok and reason == 'invalid_pdf_magic'


# ── JSON tests ────────────────────────────────────────────────────────────────

def test_json_good():
    ok, reason = validate_asset(_json_good(), 'application/json')
    assert ok and reason == 'pass'


def test_json_empty_dict():
    ok, reason = validate_asset(_json_empty_dict(), 'application/json')
    assert not ok and reason == 'json_empty'


def test_json_empty_list():
    ok, reason = validate_asset(_json_empty_list(), 'application/json')
    assert not ok and reason == 'json_empty'


def test_json_invalid():
    ok, reason = validate_asset(b'not json {{', 'application/json')
    assert not ok and reason == 'json_invalid'


# ── Code tests ────────────────────────────────────────────────────────────────

def test_code_good():
    ok, reason = validate_asset(_code_good(), 'text/x-python')
    assert ok and reason == 'pass'


def test_code_too_short():
    ok, reason = validate_asset(_code_short(), 'text/x-python')
    assert not ok and reason == 'code_too_short'


def test_code_app_x_python():
    ok, reason = validate_asset(_code_good(), 'application/x-python')
    assert ok and reason == 'pass'


# ── ZIP tests ─────────────────────────────────────────────────────────────────

def test_zip_good():
    ok, reason = validate_asset(_zip_good(), 'application/zip')
    assert ok and reason == 'pass'


def test_zip_bad_magic():
    ok, reason = validate_asset(_zip_bad(), 'application/zip')
    assert not ok and reason == 'invalid_zip_magic'


# ── Unknown type ──────────────────────────────────────────────────────────────

def test_unknown_type_passes():
    ok, reason = validate_asset(b'\x00\x01\x02', 'application/octet-stream')
    assert ok and reason == 'unvalidated'


def test_unknown_video_passes():
    ok, reason = validate_asset(b'\x00' * 50, 'video/mp4')
    assert ok and reason == 'unvalidated'


# ── strict variant ────────────────────────────────────────────────────────────

def test_strict_raises_on_fail():
    with pytest.raises(ValueError, match='invalid_image_magic'):
        validate_asset_strict(b'\x00' * 200, 'image/png')


def test_strict_passes_on_good():
    # Should not raise
    validate_asset_strict(_png(), 'image/png')


def test_strict_raises_json_empty():
    with pytest.raises(ValueError, match='json_empty'):
        validate_asset_strict(b'{}', 'application/json')
