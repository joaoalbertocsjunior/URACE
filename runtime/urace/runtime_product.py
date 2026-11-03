"""Runtime codebase product identity; observations never confer authority."""
from pathlib import Path
import hashlib

PRODUCT_ID = 'urace-runtime:' + str(Path(__file__).resolve().parent.parent.parent)
PRODUCT_NAME = 'urace runtime'


def engine_identity(root=None):
    """Content hash of the runtime Python source files; stable for identical sources."""
    if root is None:
        root = Path(__file__).resolve().parent
    root = Path(root)
    digest = hashlib.sha256()
    for path in sorted(root.glob('*.py')):
        digest.update(path.name.encode())
        digest.update(b':')
        try:
            digest.update(path.read_bytes())
        except OSError:
            pass
        digest.update(b'\n')
    return digest.hexdigest()


def registration():
    """Products.json entry for the runtime product."""
    return {'id': PRODUCT_ID, 'name': PRODUCT_NAME, 'source': 'runtime-codebase', 'kind': 'runtime'}


def quality_gate(config):
    """Minimum score delta and metric required to accept a runtime improvement."""
    wf = config.get('runtime_workflow', {}) if isinstance(config, dict) else {}
    return {
        'metric': wf.get('quality_gate_metric', 'executable_benchmark_score'),
        'minimum_delta': wf.get('quality_gate_minimum_score_delta', 5.0),
    }


def mutation_blocker(root,argv):
    """Defer external mutations during publication; retain observation/emergency controls."""
    import json
    from .command_surface import read_only
    args=list(argv)
    while args and args[0].startswith('--'):
        args=args[2:] if args[0]=='--format' else args[1:]
    if not args:return None
    args[0]=args[0].lstrip('/')
    path=Path(root)/'trial/runtime-deployment-transaction.json'
    if not path.exists():return None
    try:transaction=json.loads(path.read_text())
    except (OSError,ValueError):return 'Deployment journal unreadable; mutations require operator review'
    if transaction.get('status')!='PREPARED':return None
    if args[0]=='api' or args[0]=='pause' or read_only(args):return None
    if args[:2]==['product','disable'] or args[:3]==['product','improvements','disable']:return None
    if args[:2]==['configuration','runtime-improvement']:
        controls=[];i=2
        while i<len(args):
            token=args[i]
            if token in ('--json',):i+=1;continue
            if '=' in token:flag,value=token.split('=',1)
            elif i+1<len(args):flag,value=token,args[i+1];i+=1
            else:return 'Runtime deployment is in progress; mutations deferred'
            if flag not in ('--enabled','--auto-deploy') or value!='false':return 'Runtime deployment is in progress; mutations deferred'
            controls.append(flag);i+=1
        if controls:return None
    return 'Runtime deployment is in progress; mutations deferred while read-only status and emergency pause remain available'
