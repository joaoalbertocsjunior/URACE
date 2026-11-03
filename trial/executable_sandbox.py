"""Run generated pure-function artifacts without mounting tests or project data."""
import ast,json,os,selectors,subprocess,time,uuid
from pathlib import Path
IMAGE='sha256:e555fc7e038293074ff704a2c842a6d1eee643864c4e93e5d20befb8029a27c7'
class SandboxInfrastructureError(RuntimeError):pass

FUNCTIONS={'quality_delta','evidence_verdict','ready_operations','aggregate_records'}
ALLOWED_IMPORTS={'__future__','math','collections','functools','itertools','heapq','typing'}
FORBIDDEN={'sys','os','builtins','inspect','importlib','eval','exec','compile','open','input','print','globals','locals','vars','getattr','setattr','delattr','breakpoint','help','exit','quit'}

def validate_source(source,required=None):
    if not isinstance(source,str) or not source.strip() or len(source.encode())>30000:raise ValueError('Bounded Python source required')
    tree=ast.parse(source)
    defined={n.name for n in tree.body if isinstance(n,ast.FunctionDef)}
    if not (FUNCTIONS if required is None else set(required))<=defined:raise ValueError('Missing requested workflow function')
    for n in tree.body:
        if isinstance(n,(ast.Import,ast.ImportFrom,ast.FunctionDef)):continue
        if isinstance(n,ast.Expr) and isinstance(n.value,ast.Constant) and isinstance(n.value.value,str):continue
        if isinstance(n,(ast.Assign,ast.AnnAssign)):
            try:ast.literal_eval(n.value);continue
            except (ValueError,TypeError):pass
        raise ValueError('Module-level code must be imports, function definitions or literal constants')
    for n in ast.walk(tree):
        if isinstance(n,ast.Import) and any(a.name.split('.')[0] not in ALLOWED_IMPORTS or (a.asname in FORBIDDEN if a.asname else False) for a in n.names):raise ValueError('Import outside pure-workflow contract')
        if isinstance(n,ast.ImportFrom) and (n.level or (n.module or '').split('.')[0] not in ALLOWED_IMPORTS):raise ValueError('Import outside pure-workflow contract')
        if isinstance(n,ast.Name) and (n.id in FORBIDDEN or n.id.startswith('__')):raise ValueError('I/O or introspection is outside the artifact contract')
        if isinstance(n,ast.Attribute) and (n.attr.startswith('_') or n.attr in FORBIDDEN or n.attr in {'modules','system','popen'}):raise ValueError('Artifact introspection is prohibited')
        if isinstance(n,ast.ImportFrom) and any(a.name.startswith('_') or a.name in FORBIDDEN for a in n.names):raise ValueError('Private import is prohibited')
        if isinstance(n,ast.FunctionDef) and (n.name.startswith('__') or n.decorator_list):raise ValueError('Decorated or magic functions are outside artifact contract')
    return tree

RUNNER=r"""
import json,resource,sys,types
resource.setrlimit(resource.RLIMIT_CPU,(8,8))
requests=json.load(sys.stdin)
module=types.ModuleType('artifact')
code=open('/artifact.py',encoding='utf-8').read()
exec(compile(code,'/artifact.py','exec'),module.__dict__)
results=[]
for request in requests:
    try:
        result=getattr(module,request['function'])(*request['args'])
        # Serialize each output immediately; custom objects and NaN are errors.
        result=json.loads(json.dumps(result,allow_nan=False))
        results.append({'id':request['id'],'value':result})
    except Exception as error:results.append({'id':request['id'],'error':type(error).__name__})
print(json.dumps({'results':results},allow_nan=False))
"""

def check_image():
    subprocess.run(['docker','image','inspect',IMAGE],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,timeout=10)

def execute(path,cases,wall_limit=30):
    source=Path(path).read_text();validate_source(source,{c['function'] for c in cases})
    name='urace-executable-'+uuid.uuid4().hex
    requests=[{k:c[k] for k in ('id','function','args')} for c in cases]
    cmd=['docker','run','-i','--rm','--name',name,'--log-driver','none','--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--user',str(os.getuid())+':'+str(os.getgid()),'--pids-limit','32','--memory','256m','--memory-swap','256m','--cpus','1','--tmpfs','/tmp:rw,nosuid,noexec,size=32m','--mount','type=bind,src='+str(Path(path).resolve())+',dst=/artifact.py,readonly',IMAGE,'python3','-I','-c',RUNNER]
    process=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    started=time.monotonic();payload=memoryview(json.dumps(requests,separators=(',',':')).encode());selector=selectors.DefaultSelector();stdout=bytearray();stderr=bytearray();failure=None
    for stream in (process.stdin,process.stdout,process.stderr):os.set_blocking(stream.fileno(),False)
    selector.register(process.stdin,selectors.EVENT_WRITE,'input');selector.register(process.stdout,selectors.EVENT_READ,'output');selector.register(process.stderr,selectors.EVENT_READ,'error')
    try:
        while selector.get_map():
            if time.monotonic()-started>wall_limit:raise TimeoutError('Artifact sandbox wall limit')
            for key,_ in selector.select(.05):
                stream=key.fileobj
                if key.data=='input':
                    try:written=os.write(stream.fileno(),payload[:16384]);payload=payload[written:]
                    except BrokenPipeError:payload=payload[len(payload):]
                    if not payload:selector.unregister(stream);stream.close()
                else:
                    part=os.read(stream.fileno(),65536)
                    if not part:selector.unregister(stream);continue
                    target=stdout if key.data=='output' else stderr;target.extend(part)
                    if len(stdout)+len(stderr)>1048576:raise ValueError('Artifact output limit')
        process.wait(timeout=2)
        if process.returncode in (125,126,127):raise SandboxInfrastructureError('Container runtime unavailable: '+stderr.decode(errors='replace')[:300])
        if process.returncode:raise ValueError('Artifact sandbox exited '+str(process.returncode)+': '+stderr.decode(errors='replace')[:300])
        response=json.loads(stdout,parse_constant=lambda s:(_ for _ in ()).throw(ValueError('Nonfinite artifact JSON')))
        results=response.get('results')
        if not isinstance(results,list) or len(results)!=len(cases) or [r.get('id') for r in results]!=[c['id'] for c in cases]:raise ValueError('Incomplete sandbox output')
        return {'status':'EXECUTED','results':results,'sandbox_seconds':time.monotonic()-started,'image':IMAGE}
    finally:
        selector.close()
        if process.poll() is None:
            subprocess.run(['docker','kill',name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=10)
            process.kill();process.wait(timeout=5)
        for stream in (process.stdin,process.stdout,process.stderr):
            if not stream.closed:stream.close()
