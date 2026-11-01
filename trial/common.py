from pathlib import Path
from contextlib import contextmanager
import fcntl,hashlib,json,os,tempfile,time,uuid
BASE=Path(__file__).resolve().parent

def operations_root():
    """Source is bundled; optional shared operational state stays untracked."""
    path = BASE/'operations-location.json'
    if path.exists():
        value = json.loads(path.read_text())['root']
        if not isinstance(value, str) or not Path(value).is_absolute():
            raise ValueError('Operations state root must be an absolute path')
        return Path(value)
    return BASE/'operations'

def atomic(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile('w',dir=path.parent,delete=False) as stream:
        json.dump(value,stream,sort_keys=True,allow_nan=False);stream.write('\n');stream.flush();os.fsync(stream.fileno());name=stream.name
    os.replace(name,path)
    directory=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(directory)
    finally:os.close(directory)

def append(value):
    contract=json.loads((BASE/'contract.json').read_text())
    value={**value,'product_id':contract['product_id'],'product':contract['target_product'],'trial_id':contract.get('trial_id')}
    from urace.authenticated_journal import append_row
    append_row(BASE/'ledger.jsonl',value)

@contextmanager
def guard():
    with (operations_root()/'shared-resource.guard').open('a') as stream:
        fcntl.flock(stream,fcntl.LOCK_EX);yield

def events():
    from accounting import projected
    rows=[json.loads(line) for line in (BASE/'ledger.jsonl').read_text().splitlines()] if (BASE/'ledger.jsonl').exists() else []
    return projected(rows)

def _governor():
    import importlib.util
    path=BASE/'resource_governor.py'
    spec=importlib.util.spec_from_file_location('urace_shared_governor',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

def reserve(provider):return _governor().reserve(BASE,provider)
def budget_status(provider,next_wall=None):return _governor().status(provider,next_wall=next_wall)


def evidence_path(value):
    """Resolve preserved historical references without rewriting signed evidence."""
    path = Path(value)
    mapping = BASE / 'path-relocations.json'
    if not mapping.exists() or not path.is_absolute():
        return path
    for old in json.loads(mapping.read_text()).get('previous_roots', []):
        try:
            relative = path.relative_to(Path(old))
        except ValueError:
            continue
        target = (BASE / relative).resolve()
        if not target.is_relative_to(BASE.resolve()):
            raise ValueError('Historical reference escapes migrated trial root')
        return target
    return path
