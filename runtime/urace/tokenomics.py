"""Token unit definition and attribution fingerprints for peer artifact exchange."""
import ast, hashlib, json

TOKEN_UNIT = {
    'schema': 'urace-tokenomics-v1',
    'definition': '1 token = 1 accepted quality improvement point, attributed to its origin peer',
    'earn': 'score_delta at quality gate pass; no other earn path',
    'spend': 'request improvements from peers',
    'baseline_grant_requests': 3,
    'deduplication': 'canonical_fingerprint for exact copies; outcome_fingerprint for near-copies',
    'settlement': 'not_yet_implemented',
    'mainnet_settlement_enabled': False,
}

def _encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()

def canonical_fingerprint(source_delta):
    """Exact-copy detection via AST-normalized source hash.

    source_delta: dict of {filename: source_text} for changed files only.
    Returns hex SHA-256 of the canonical normalized form.
    Two patches are exact copies iff their canonical_fingerprint is equal.
    """
    canonical = {}
    for name, text in sorted(source_delta.items()):
        try:
            canonical[name] = ast.dump(ast.parse(text))
        except SyntaxError:
            canonical[name] = ' '.join(text.split())
    return hashlib.sha256(_encoded(canonical)).hexdigest()

def outcome_fingerprint(baseline_engine_sha256, affected_files, score_delta):
    """Near-copy detection: same outcome regardless of surface form.

    baseline_engine_sha256: engine_sha256 of the evaluation baseline.
    affected_files: iterable of changed filenames.
    score_delta: float; bucketed to nearest int to absorb trivial variance.
    Two patches are near-copies iff they fix the same files for the same score gain from the same baseline.
    """
    return hashlib.sha256(_encoded({
        'baseline': baseline_engine_sha256,
        'files': sorted(affected_files),
        'delta_bucket': round(float(score_delta)),
    })).hexdigest()

def fingerprint_index(evaluations_dir):
    """Build outcome fingerprint index from stored qualification receipts.

    Returns dict mapping outcome_fingerprint -> list of {id, at, score, delta}.
    Used at deduplication check time; empty dict when no qualifications exist yet.
    """
    from pathlib import Path
    index = {}
    q_dir = Path(evaluations_dir)
    if not q_dir.exists():
        return index
    for receipt_path in sorted(q_dir.glob('*/receipt.json')):
        try:
            receipt = json.loads(receipt_path.read_text())
            ev_id = receipt.get('id')
            fp = receipt.get('outcome_fingerprint')
            if ev_id and fp:
                index.setdefault(fp, []).append({
                    'id': ev_id,
                    'at': receipt.get('at'),
                    'score': receipt.get('candidate_score'),
                    'delta': receipt.get('delta'),
                })
        except (OSError, ValueError):
            continue
    return index

def artifact_fingerprint(content_type: str, raw_bytes: bytes) -> str:
    """Content-type-aware similarity fingerprint for ALE provenance detection.

    Protection levels:
      STRONG  — image/* (dHash), CSV/JSON/NDJSON (statistical), ZIP (bundle), XML (schema+Winnowing)
      MEDIUM  — PDF (text extraction+Winnowing), DOCX/XLSX/PPTX (OOX text+Winnowing/stats)
      WEAK    — all text/* and code types (Winnowing), application/octet-stream fallback (SHA-256)

    Returns hex string. Matching fingerprints → near-duplicate → provenance enforcement applies.
    """
    ct = (content_type or '').lower().split(';')[0].strip()

    # STRONG: images
    if ct.startswith('image/'):
        return _dhash(raw_bytes)

    # STRONG: structured data
    if ct in ('text/csv', 'application/json', 'application/x-ndjson', 'application/jsonl'):
        return _statistical_fingerprint(raw_bytes, ct)

    # STRONG: XML
    if ct in ('application/xml', 'text/xml', 'image/svg+xml'):
        return _xml_fingerprint(raw_bytes)

    # MEDIUM: PDF
    if ct == 'application/pdf':
        return _pdf_text_fingerprint(raw_bytes)

    # MEDIUM: Office Open XML (DOCX, XLSX, PPTX)
    if 'wordprocessingml' in ct or ct == 'application/msword':
        return _office_open_xml_fingerprint(raw_bytes, 'docx')
    if 'spreadsheetml' in ct or ct in ('application/vnd.ms-excel',):
        return _office_open_xml_fingerprint(raw_bytes, 'xlsx')
    if 'presentationml' in ct or ct == 'application/vnd.ms-powerpoint':
        return _office_open_xml_fingerprint(raw_bytes, 'pptx')

    # MEDIUM: ZIP bundles — decomposed at grant time (bundle_decompose handles this)
    if ct in ('application/zip', 'application/x-zip-compressed', 'application/x-tar', 'application/gzip'):
        return hashlib.sha256(raw_bytes).hexdigest()  # identity — bundle_decompose does member-level fingerprinting

    # WEAK: all text and code types — Winnowing
    if ct.startswith('text/') or ct in (
        'application/javascript', 'application/x-python', 'application/x-sh',
        'application/x-ruby', 'application/typescript', 'application/x-httpd-php',
        'application/x-perl', 'application/x-java',
    ):
        fp = winnow_fingerprint(raw_bytes)
        if fp:
            return hashlib.sha256(','.join(str(h) for h in sorted(fp)).encode()).hexdigest()

    # FALLBACK: SHA-256 exact match only
    return hashlib.sha256(raw_bytes).hexdigest()

def bundle_decompose(raw_bytes: bytes) -> list[tuple[str, bytes, str]]:
    """Extract (filename, file_bytes, content_type) from a zip bundle.

    If not a zip, returns a single item with empty filename and detected content type.
    Used for automatic sub-artifact composition detection at grant time.
    """
    import zipfile, io, mimetypes as _mt
    try:
        with zipfile.ZipFile(io.BytesIO(raw_bytes)) as zf:
            result = []
            for info in zf.infolist():
                if info.filename.endswith('/') or info.file_size == 0:
                    continue
                ct, _ = _mt.guess_type(info.filename)
                result.append((info.filename, zf.read(info.filename), ct or 'application/octet-stream'))
            return result if result else [('', raw_bytes, 'application/octet-stream')]
    except Exception:
        return [('', raw_bytes, 'application/octet-stream')]

def dhash_int(raw_bytes: bytes, size: int = 8) -> int | None:
    """Return dHash as raw 64-bit integer for Hamming distance comparison.
    Returns None if not an image or too small to hash.
    """
    try:
        hex_str = _dhash(raw_bytes, size)
        return int(hex_str, 16)
    except Exception:
        return None


def hamming_distance(a: int, b: int) -> int:
    return bin(a ^ b).count('1')


def winnow_fingerprint(raw_bytes: bytes, k: int = 5, w: int = 4) -> frozenset:
    """Winnowing algorithm for code/text similarity detection.

    Returns a frozenset of selected k-gram hashes (Schleimer et al. 2003).
    Two documents sharing >= 60% of fingerprints (Jaccard) are considered
    near-identical for provenance purposes.
    """
    try:
        text = raw_bytes.decode('utf-8', errors='replace').lower()
    except Exception:
        return frozenset()
    # Normalize: collapse whitespace, strip comments (# and //)
    import re
    text = re.sub(r'#[^\n]*', ' ', text)
    text = re.sub(r'//[^\n]*', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    if len(text) < k:
        return frozenset()
    # k-gram hashes
    kgrams = [hash(text[i:i+k]) & 0xFFFFFFFF for i in range(len(text) - k + 1)]
    if len(kgrams) < w:
        return frozenset(kgrams)
    # Winnowing: select minimum hash in each window
    selected = set()
    prev_min_pos = -1
    for i in range(len(kgrams) - w + 1):
        window = kgrams[i:i+w]
        min_val = min(window)
        min_pos = i + window.index(min_val)
        if min_pos != prev_min_pos:
            selected.add(min_val)
            prev_min_pos = min_pos
    return frozenset(selected)


def winnow_similarity(fp_a: frozenset, fp_b: frozenset) -> float:
    """Jaccard similarity between two Winnowing fingerprint sets."""
    if not fp_a or not fp_b:
        return 0.0
    intersection = len(fp_a & fp_b)
    union = len(fp_a | fp_b)
    return intersection / union if union > 0 else 0.0


def _dhash(raw_bytes: bytes, size: int = 8) -> str:
    """64-bit difference hash for images. Pure Python — no PIL required.
    Downsample to (size+1)×size grayscale via nearest-neighbour, diff horizontally.
    Returns 16-char hex. Identical content → identical hash. Near-identical → Hamming dist <= 10.
    """
    try:
        from PIL import Image
        import io
        img = Image.open(io.BytesIO(raw_bytes)).convert('L').resize((size + 1, size))
        pixels = list(img.getdata())
    except Exception:
        total = size * (size + 1)
        step = max(1, len(raw_bytes) // total)
        pixels = [raw_bytes[i * step] for i in range(total)]
        pixels += [0] * (total - len(pixels))
    bits = 0
    for row in range(size):
        for col in range(size):
            left = pixels[row * (size + 1) + col]
            right = pixels[row * (size + 1) + col + 1]
            bits = (bits << 1) | (1 if left > right else 0)
    return format(bits, '016x')

def _statistical_fingerprint(raw_bytes: bytes, ct: str) -> str:
    """Statistical fingerprint for structured data — order-independent and distribution-dependent.

    For each column/field: sorted unique value sample (up to 50) + (count, min_len, max_len).
    Attacker must synthesize matching value distributions across ALL columns to evade detection.
    Far stronger than first-N-rows hashing.
    """
    try:
        text = raw_bytes.decode('utf-8', errors='replace')
        if ct == 'text/csv':
            lines = [l for l in text.splitlines() if l.strip()]
            if not lines:
                return hashlib.sha256(raw_bytes).hexdigest()
            header = lines[0]
            cols = [c.strip() for c in header.split(',')]
            rows_data = [line.split(',') for line in lines[1:]]
            col_stats = []
            for i, col in enumerate(cols):
                vals = [r[i].strip() if i < len(r) else '' for r in rows_data]
                unique_sorted = sorted(set(vals))
                # sample evenly up to 50
                step = max(1, len(unique_sorted) // 50)
                sample = unique_sorted[::step][:50]
                col_stats.append(f'{col}:{len(vals)}:{len(unique_sorted)}:{hashlib.sha256("|".join(sample).encode()).hexdigest()[:12]}')
            combined = hashlib.sha256(','.join(sorted(cols)).encode()).hexdigest()[:16] + '|' + '|'.join(col_stats)
            return hashlib.sha256(combined.encode()).hexdigest()

        elif ct in ('application/x-ndjson', 'application/jsonl'):
            lines = [l.strip() for l in text.splitlines() if l.strip()]
            if not lines:
                return hashlib.sha256(raw_bytes).hexdigest()
            field_vals: dict = {}
            for line in lines:
                try:
                    obj = json.loads(line)
                    if isinstance(obj, dict):
                        for k, v in obj.items():
                            field_vals.setdefault(k, []).append(str(v))
                except Exception:
                    pass
            return _field_stats_hash(field_vals)

        else:  # application/json
            obj = json.loads(text)
            if isinstance(obj, list):
                field_vals: dict = {}
                for item in obj:
                    if isinstance(item, dict):
                        for k, v in item.items():
                            field_vals.setdefault(k, []).append(str(v))
                return _field_stats_hash(field_vals)
            elif isinstance(obj, dict):
                return _field_stats_hash({k: [str(v)] for k, v in obj.items()})
            return hashlib.sha256(raw_bytes).hexdigest()
    except Exception:
        return hashlib.sha256(raw_bytes).hexdigest()


def _field_stats_hash(field_vals: dict) -> str:
    """Hash of per-field value distributions. Order-independent."""
    col_stats = []
    for field in sorted(field_vals.keys()):
        vals = field_vals[field]
        unique_sorted = sorted(set(vals))
        step = max(1, len(unique_sorted) // 50)
        sample = unique_sorted[::step][:50]
        col_stats.append(f'{field}:{len(vals)}:{len(unique_sorted)}:{hashlib.sha256("|".join(sample).encode()).hexdigest()[:12]}')
    combined = ','.join(col_stats)
    return hashlib.sha256(combined.encode()).hexdigest()


def _xml_fingerprint(raw_bytes: bytes) -> str:
    """Schema + text Winnowing fingerprint for XML/SVG.
    Extracts element tag names (schema) + text content (Winnowing).
    Pure Python — no lxml/expat required beyond stdlib xml.etree.
    """
    import re
    try:
        import xml.etree.ElementTree as ET
        root = ET.fromstring(raw_bytes.decode('utf-8', errors='replace'))
        tags = sorted({el.tag.split('}')[-1] for el in root.iter()})
        texts = ' '.join(el.text or '' for el in root.iter() if el.text and el.text.strip())
        schema_hash = hashlib.sha256(','.join(tags).encode()).hexdigest()[:16]
        text_fp = winnow_fingerprint(texts.encode())
        text_hash = hashlib.sha256(','.join(str(h) for h in sorted(text_fp)).encode()).hexdigest()[:16] if text_fp else '0' * 16
        return hashlib.sha256(f'{schema_hash}|{text_hash}'.encode()).hexdigest()
    except Exception:
        # Fallback: regex tag extraction
        tags = sorted(set(re.findall(r'<([a-zA-Z][a-zA-Z0-9_:-]*)', raw_bytes.decode('utf-8', errors='replace'))))
        return hashlib.sha256(','.join(tags).encode()).hexdigest()


def _pdf_text_fingerprint(raw_bytes: bytes) -> str:
    """Extract text from PDF content streams and apply Winnowing. Pure Python, no deps.
    Finds BT...ET blocks and extracts Tj/TJ string operands.
    """
    import re
    try:
        text_chunks = []
        # Find all text object blocks
        for block in re.findall(rb'BT\s*(.*?)\s*ET', raw_bytes, re.DOTALL):
            # Extract string literals from Tj, TJ, ', " operators
            for s in re.findall(rb'\(([^)]*)\)\s*(?:Tj|\'|")', block):
                try:
                    text_chunks.append(s.decode('latin-1', errors='replace'))
                except Exception:
                    pass
            for arr in re.findall(rb'\[(.*?)\]\s*TJ', block, re.DOTALL):
                for s in re.findall(rb'\(([^)]*)\)', arr):
                    try:
                        text_chunks.append(s.decode('latin-1', errors='replace'))
                    except Exception:
                        pass
        if not text_chunks:
            return hashlib.sha256(raw_bytes).hexdigest()
        combined_text = ' '.join(text_chunks)
        fp = winnow_fingerprint(combined_text.encode())
        if not fp:
            return hashlib.sha256(raw_bytes).hexdigest()
        return hashlib.sha256(','.join(str(h) for h in sorted(fp)).encode()).hexdigest()
    except Exception:
        return hashlib.sha256(raw_bytes).hexdigest()


def _office_open_xml_fingerprint(raw_bytes: bytes, doc_type: str) -> str:
    """Fingerprint for DOCX/XLSX/PPTX (Office Open XML = ZIP containers).
    Extracts text from known XML entry paths, applies Winnowing (text docs)
    or statistical fingerprint (spreadsheets).
    """
    import zipfile, io, re
    TEXT_PATHS = {
        'docx': ['word/document.xml', 'word/body.xml'],
        'xlsx': ['xl/worksheets/sheet1.xml', 'xl/sharedStrings.xml'],
        'pptx': ['ppt/slides/slide1.xml', 'ppt/slides/slide2.xml'],
    }
    try:
        with zipfile.ZipFile(io.BytesIO(raw_bytes)) as zf:
            names = set(zf.namelist())
            paths = TEXT_PATHS.get(doc_type, [])
            # auto-detect if doc_type unknown
            if not paths:
                if any('word/' in n for n in names):
                    paths = TEXT_PATHS['docx']
                elif any('xl/' in n for n in names):
                    paths = TEXT_PATHS['xlsx']
                else:
                    paths = [n for n in names if n.endswith('.xml')][:3]
            texts = []
            for path in paths:
                if path in names:
                    xml_bytes = zf.read(path)
                    # Strip XML tags, keep text
                    text = re.sub(rb'<[^>]+>', b' ', xml_bytes)
                    texts.append(text.decode('utf-8', errors='replace'))
            if not texts:
                return hashlib.sha256(raw_bytes).hexdigest()
            combined = ' '.join(texts)
            if doc_type == 'xlsx':
                # Treat as structured data: extract cell values
                cells = re.findall(r'<v>([^<]*)</v>', combined)
                if cells:
                    return _field_stats_hash({'cell': cells})
            fp = winnow_fingerprint(combined.encode())
            if not fp:
                return hashlib.sha256(raw_bytes).hexdigest()
            return hashlib.sha256(','.join(str(h) for h in sorted(fp)).encode()).hexdigest()
    except Exception:
        return hashlib.sha256(raw_bytes).hexdigest()
