"""Scoped application operations shared by MCP and future agent transports.

No inference is performed by this adapter. Authorized CLI/API operations retain
native executor governance and accounting. Receipts describe bridge work only.
"""
from __future__ import annotations
import argparse,contextlib,copy,fcntl,hashlib,io,json,os,re,selectors,signal,stat,subprocess,sys,threading,time,uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from . import api_interface,command_surface
from ._common import atomic_write_json,state_lock,SYSTEM_ROOT

SCHEMA='urace-integration-v1'
from .version import BRIDGE_VERSION,MIN_BRIDGE_CLIENT_VERSION
TERMINAL={'COMPLETED','FAILED','CANCELLED','TIMED_OUT','INTERRUPTED','OUTPUT_LIMIT'}
DEFAULT_COMMANDS=['commands','help','status runtime','status resources','status quality','status value','goal list','product list','executor status']
DEFAULT_LIMITS={'wall_seconds':480,'output_bytes':1048576,'resource_bytes':1048576,'parallel_jobs':2,'queued_jobs':256,'depth':4}
IDENTIFIER=re.compile(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,159}')
FORBIDDEN={'api call','api batch','api serve','api watch','product exchange network serve','classify','autonomous','self-evolution'}
ADMIN={'product create','product work clarify','product exchange', 'product improvements enable','product improvements disable','product enable','product disable','init','resume','update','configuration','executor attach','executor detach','product switch','product register','product remove','product deactivate','product activate','fleet','govern','rules'}

def encoded(value):return json.dumps(value,sort_keys=True,allow_nan=False,separators=(',',':')).encode()
def digest(value):return hashlib.sha256(encoded(value)).hexdigest()
def stamp():return time.time()
def pid_ticks(pid):
    try:
        fields=(Path('/proc')/str(pid)/'stat').read_text().rsplit(')',1)[1].split()
        return fields[19] if fields[0]!='Z' else None
    except (OSError,IndexError):return None

def descendants(pid):
    children={};identities={}
    for path in Path('/proc').glob('[0-9]*'):
        try:
            fields=(path/'stat').read_text().rsplit(')',1)[1].split();child=int(path.name)
            if fields[0]=='Z':continue
            children.setdefault(int(fields[1]),[]).append(child);identities[child]=fields[19]
        except (OSError,ValueError,IndexError):continue
    result={};pending=[pid]
    while pending:
        child=pending.pop()
        if child in identities:result[child]=identities[child]
        pending.extend(children.get(child,[]))
    return result

@contextlib.contextmanager
def receipt_lock(path):
    """Serialize metadata, allowing transient fork/exec FD inheritance to clear.

    Lifecycle State uses its own nonblocking controller guard. Job receipts are
    independent metadata and may wait briefly without replaying an operation.
    Never unlink the kernel guard inode.
    """
    descriptor=os.open(path.with_suffix('.lock.guard'),os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    try:
        deadline=time.monotonic()+2
        while True:
            try:fcntl.flock(descriptor,fcntl.LOCK_EX|fcntl.LOCK_NB);break
            except BlockingIOError:
                if time.monotonic()>=deadline:raise BridgeError('Receipt busy; retry the same request/job ID') from None
                time.sleep(.01)
        yield
    finally:os.close(descriptor)

@contextlib.contextmanager
def owner_lifetime():
    """Close a transport when its CLI launcher disappears; restore signal state.

    The protected restart launcher keeps its existing activation semantics.
    A detached transport must not outlive that owning invocation.
    """
    if threading.current_thread() is not threading.main_thread():
        yield
        return
    previous=signal.signal(signal.SIGTERM,lambda signum,frame:(_ for _ in ()).throw(KeyboardInterrupt()))
    stop=threading.Event();watcher=None
    if os.environ.get('URACE_LAUNCHER_CHILD')=='1':
        parent=os.getppid();ticks=pid_ticks(parent)
        def watch():
            while not stop.wait(.2):
                if parent<=1 or os.getppid()!=parent or pid_ticks(parent)!=ticks:
                    os.kill(os.getpid(),signal.SIGTERM)
                    return
        watcher=threading.Thread(target=watch,name='urace-transport-owner',daemon=True)
        watcher.start()
    try:yield
    finally:
        stop.set()
        if watcher:watcher.join(timeout=1)
        signal.signal(signal.SIGTERM,previous)

def operations(parser):
    return command_surface.operation_parsers(parser)

class BridgeError(ValueError):pass

class Policy:
    def __init__(self,parser,raw,*,root,storage):
        if not isinstance(raw,dict) or set(raw)-{'schema','project_id','executor_id','active_product','read_only','operator','commands','resources','limits','client_version'}:raise BridgeError('Unknown or invalid integration policy')
        if raw.get('schema',SCHEMA)!=SCHEMA:raise BridgeError('Unsupported policy schema')
        _cv=raw.get('client_version',BRIDGE_VERSION)
        if type(_cv) is not int or _cv<MIN_BRIDGE_CLIENT_VERSION:raise BridgeError(f'client_version {_cv} is below minimum {MIN_BRIDGE_CLIENT_VERSION}; upgrade the integration client')
        project=raw.get('project_id');executor=raw.get('executor_id')
        if not isinstance(project,str) or not project or len(project)>512 or any(ord(v)<32 for v in project):raise BridgeError('Bounded project_id required')
        if not isinstance(executor,str) or not IDENTIFIER.fullmatch(executor):raise BridgeError('Bounded executor_id required')
        self.root=Path(root).resolve();self.storage=Path(storage).resolve();self.raw=copy.deepcopy(raw);self.catalog=operations(parser);self.parser=parser
        self.read_only=raw.get('read_only',True);self.operator=raw.get('operator',False)
        if type(self.read_only) is not bool or type(self.operator) is not bool:raise BridgeError('Policy switches must be booleans')
        if raw.get('active_product') is not None and (not isinstance(raw['active_product'],str) or not raw['active_product'].strip()):raise BridgeError('Invalid active product')
        limits=raw.get('limits',{})
        if not isinstance(limits,dict) or set(limits)-set(DEFAULT_LIMITS):raise BridgeError('Unknown integration limit')
        self.limits={**DEFAULT_LIMITS,**limits}
        for k,lo,hi in [('wall_seconds',1,86400),('output_bytes',1024,16777216),('resource_bytes',1024,16777216),('parallel_jobs',1,32),('queued_jobs',1,10000),('depth',1,16)]:
            if type(self.limits[k]) is not int or not lo<=self.limits[k]<=hi:raise BridgeError('Invalid '+k)
        grants=raw.get('commands',DEFAULT_COMMANDS)
        if not isinstance(grants,list) or len(grants)>2000:raise BridgeError('commands must be a bounded array')
        self.grants={}
        for item in grants:
            item={'command':item} if isinstance(item,str) else item
            if not isinstance(item,dict) or set(item)-{'command','allowed_params','fixed_params'}:raise BridgeError('Invalid command grant')
            name=item.get('command')
            if name not in self.catalog:raise BridgeError('Unknown installed operation: '+str(name))
            if name in FORBIDDEN or name.startswith(('api call ','api batch ','api serve ','api watch ','classify ')):raise BridgeError('Recursive/streaming wrapper is not a delegated operation')
            if not self.operator and any(name==p or name.startswith(p+' ') for p in ADMIN):raise BridgeError('Administrative operation needs explicit operator policy')
            if name in self.grants:raise BridgeError('Duplicate operation grant')
            allowed=item.get('allowed_params')
            if allowed is not None and (not isinstance(allowed,list) or any(not isinstance(v,str) for v in allowed)):raise BridgeError('allowed_params must be an array')
            if not isinstance(item.get('fixed_params',{}),dict):raise BridgeError('fixed_params must be an object')
            self.grants[name]=copy.deepcopy(item)
        self.resources={}
        resources=raw.get('resources',[])
        if not isinstance(resources,list) or len(resources)>1000:raise BridgeError('Bounded resource array required')
        for item in resources:
            if not isinstance(item,dict) or set(item)-{'uri','name','path','mimeType'}:raise BridgeError('Invalid resource grant')
            uri=item.get('uri');path=item.get('path')
            if not isinstance(uri,str) or not uri.startswith('urace://') or len(uri)>500 or uri in self.resources or uri=='urace://session/capabilities' or uri.startswith('urace://jobs/'):raise BridgeError('Unique urace:// resource URI required')
            if not isinstance(path,str) or not path or Path(path).is_absolute() or any(p in {'.','..'} or p.startswith('.') for p in Path(path).parts):raise BridgeError('Resource must be a nonhidden project-relative path')
            self.resources[uri]=copy.deepcopy(item)
        self.hash=digest(raw)
    def describe(self,command=None,query='',offset=0,limit=50):
        if type(offset) is not int or offset<0 or type(limit) is not int or not 1<=limit<=100:raise BridgeError('Invalid catalog page')
        if command is not None:
            if command not in self.grants:raise BridgeError('Operation not delegated')
            p=self.catalog[command];return {'command':command,'grant':self.grants[command],'arguments':api_interface.metadata_for_parser(p),'execution':'Same typed API handler; native authority and resource guards retained'}
        names=[n for n in sorted(self.grants) if query.lower() in n.lower()]
        return {'commands':names[offset:offset+limit],'total':len(names),'next_offset':offset+limit if offset+limit<len(names) else None,'read_only':self.read_only,'project_id':self.raw['project_id'],'executor_id':self.raw['executor_id'],'policy_sha256':self.hash}
    def canonical_params(self,command,params):
        aliases={}
        for action in self.catalog[command]._actions:
            if action.option_strings:
                canonical=next((f for f in action.option_strings if f.startswith('--')),action.option_strings[0]).lstrip('-').replace('-','_')
                aliases.setdefault(action.dest,canonical)
                for flag in action.option_strings:aliases[flag.lstrip('-').replace('-','_')]=canonical
            else:aliases[action.dest]=action.dest
        result={}
        for key,value in params.items():
            if not isinstance(key,str):raise BridgeError('Parameter names must be strings')
            key=aliases.get(key.replace('-','_'),key)
            if key in result:raise BridgeError('Duplicate parameter aliases')
            result[key]=value
        return result
    def authorize(self,command,params):
        if command not in self.grants:raise BridgeError('Operation not delegated')
        if not isinstance(params,dict) or len(encoded(params))>65536:raise BridgeError('Bounded typed parameters required')
        grant=self.grants[command];fixed=self.canonical_params(command,grant.get('fixed_params',{}));allowed=grant.get('allowed_params')
        if allowed is not None:allowed=set(self.canonical_params(command,{key:None for key in allowed}))
        params=self.canonical_params(command,params)
        for k,v in params.items():
            if k in fixed and v!=fixed[k]:raise BridgeError('Fixed parameter cannot be overridden: '+k)
            if allowed is not None and k not in allowed and k not in fixed:raise BridgeError('Parameter not delegated: '+k)
        values={**params,**fixed}
        try:argv=api_interface.build_argv(self.parser,command,values)
        except (ValueError,TypeError) as error:raise BridgeError(str(error)) from error
        actual=max((name for name in self.catalog if argv[:len(name.split())]==name.split()),key=lambda name:len(name.split()))
        if actual!=command:raise BridgeError('Use the exact delegated operation path, not a parent command with an action parameter')
        with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
            try:
                namespace=self.parser.parse_args(argv)
                command_surface.validate(namespace,argv,self.parser)
            except SystemExit:raise BridgeError('Parameters do not form a valid installed operation') from None
        if api_interface.persistent(argv):raise BridgeError('Use finite cycles for delegated work; persistent controllers remain owner-managed')
        if not self.operator and command=='derive' and '--apply-capabilities' in argv:raise BridgeError('Capability configuration requires operator policy')
        readonly=command_surface.read_only(argv)
        if self.read_only and not readonly:raise BridgeError('Policy permits read-only operations')
        return argv,readonly
    def read_resource(self,uri):
        if uri not in self.resources:raise BridgeError('Resource not delegated')
        from .outcome_verification import _open_beneath
        item=self.resources[uri]
        with os.fdopen(_open_beneath(self.root,Path(item['path'])),'rb') as stream:
            info=os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode):raise BridgeError('Regular resource file required')
            content=stream.read(self.limits['resource_bytes']+1)
        if len(content)>self.limits['resource_bytes']:raise BridgeError('Resource byte allowance exceeded')
        result={'uri':uri,'mimeType':item.get('mimeType','text/plain'),'sha256':hashlib.sha256(content).hexdigest()}
        try:result['text']=content.decode('utf-8')
        except UnicodeDecodeError:
            import base64
            result['blob']=base64.b64encode(content).decode('ascii');result['mimeType']=item.get('mimeType','application/octet-stream')
        return result

def load_policy(parser,path=None):
    from ._common import load_config,state_path
    from .resource_usage import product_identity
    cfg=load_config();root=__import__('urace._common',fromlist=['ROOT']).ROOT
    if path:
        p=Path(path)
        if p.resolve().is_relative_to(Path(root).resolve()):raise BridgeError('Operator policy must be outside the delegated project tree')
        with os.fdopen(os.open(p,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK),'rb') as f:
            if not stat.S_ISREG(os.fstat(f.fileno()).st_mode):raise BridgeError('Policy must be a regular file')
            data=f.read(262145)
        if len(data)>262144:raise BridgeError('Policy exceeds256KiB')
        raw=json.loads(data)
    else:raw={'schema':SCHEMA,'project_id':product_identity(cfg),'executor_id':'external','read_only':True}
    if raw.get('active_product'):
        from . import _common
        with patched_product(raw['active_product']):cfg=_common.load_config()
    if raw.get('project_id')!=product_identity(cfg):raise BridgeError('Policy project does not match active resource product')
    storage=state_path(cfg).parent/'integrations'/digest(raw)[:24]
    return Policy(parser,raw,root=root,storage=storage)

@contextlib.contextmanager
def patched_product(value):
    old=os.environ.get('URACE_ACTIVE_PRODUCT');os.environ['URACE_ACTIVE_PRODUCT']=value
    try:yield
    finally:
        if old is None:os.environ.pop('URACE_ACTIVE_PRODUCT',None)
        else:os.environ['URACE_ACTIVE_PRODUCT']=old

def paused():return (SYSTEM_ROOT/'.migration-in-progress').exists() or (SYSTEM_ROOT/'trial/user-pause.json').exists()

class Jobs:
    def __init__(self,policy,*,pause_check=paused,command_factory=None,private_env=()):
        self.private_env=frozenset(private_env)
        self.policy=policy;self.pause_check=pause_check;self.command_factory=command_factory or self.command;self.pool=ThreadPoolExecutor(max_workers=policy.limits['parallel_jobs'],thread_name_prefix='urace-integration');self.events={};self.futures={};self.lock=threading.RLock();self.closed=False
        policy.storage.mkdir(parents=True,exist_ok=True,mode=0o700)
        os.chmod(policy.storage,0o700)
    def command(self,argv):
        bootstrap='import sys,runpy;sys.path.insert(0,'+repr(str(Path(__file__).resolve().parent.parent))+');runpy.run_module("urace.integration_bridge",run_name="__main__")'
        return [sys.executable,'-c',bootstrap,'--worker',json.dumps(argv)]
    def path(self,job_id):
        if not isinstance(job_id,str) or not re.fullmatch(r'[0-9a-f]{32}',job_id):raise BridgeError('Invalid job ID')
        return self.policy.storage/(job_id+'.json')
    def update(self,job_id,**fields):
        path=self.path(job_id)
        with self.lock,receipt_lock(path):
            data=json.loads(path.read_text());data.update(fields,updated_unix=stamp());atomic_write_json(path,data)
        return data
    def submit(self,command,params=None,request_id=None):
        argv,readonly=self.policy.authorize(command,{} if params is None else params)
        if not readonly and self.pause_check():raise BridgeError('URACE is paused; delegated mutations and executor work are suspended')
        if request_id is None:
            if not readonly:raise BridgeError('Mutations require a stable request_id for deduplication')
            request_id=uuid.uuid4().hex
        if not isinstance(request_id,str) or not IDENTIFIER.fullmatch(request_id):raise BridgeError('Invalid request_id')
        try:depth=int(os.environ.get('URACE_BRIDGE_DEPTH','0'));parent_deadline=float(os.environ.get('URACE_BRIDGE_DEADLINE','inf'))
        except ValueError:raise BridgeError('Invalid inherited execution context') from None
        if depth<0 or depth>=self.policy.limits['depth']:raise BridgeError('Delegation depth exhausted')
        key=digest({'request_id':request_id,'policy':self.policy.hash})[:32];fingerprint=digest({'command':command,'params':params or {}});path=self.path(key)
        with self.lock,receipt_lock(path):
            if self.closed:raise BridgeError('Bridge is shutting down')
            if path.exists():
                row=json.loads(path.read_text())
                if row['request_sha256']!=fingerprint:raise BridgeError('request_id already belongs to a different operation')
                return row
            if len(self.events)>=self.policy.limits['queued_jobs']:raise BridgeError('Job queue busy; inspect existing work before submitting more')
            deadline=min(stamp()+self.policy.limits['wall_seconds'],parent_deadline)
            if deadline<=stamp():raise BridgeError('Inherited execution deadline exhausted')
            row={'schema':SCHEMA,'job_id':key,'request_id':request_id,'root_request_id':os.environ.get('URACE_BRIDGE_ROOT_REQUEST',request_id),'parent_job_id':os.environ.get('URACE_BRIDGE_JOB'),'depth':depth+1,'request_sha256':fingerprint,'command':command,'project_id':self.policy.raw['project_id'],'executor_id':self.policy.raw['executor_id'],'policy_sha256':self.policy.hash,'status':'PENDING','read_only':readonly,'created_unix':stamp(),'updated_unix':stamp(),'deadline_unix':deadline,'owner_pid':os.getpid(),'owner_start_ticks':pid_ticks(os.getpid()),'bridge_inference_calls':0,'native_tokens':None,'accounting':'Native operations retain their existing ledgers; bridge duration is separate and not an inferred token/credit charge'}
            atomic_write_json(path,row);event=threading.Event();self.events[key]=event;self.futures[key]=self.pool.submit(self.run,row,argv,event)
        return self.status(key)
    def status(self,job_id):
        path=self.path(job_id)
        if not path.exists():raise BridgeError('Unknown job')
        row=json.loads(path.read_text())
        if row.get('policy_sha256')!=self.policy.hash or row.get('project_id')!=self.policy.raw['project_id']:raise BridgeError('Job outside policy scope')
        if row['status'] not in TERMINAL and pid_ticks(row['owner_pid'])!=row.get('owner_start_ticks'):row=self.update(job_id,status='INTERRUPTED',reason='Owner process ended; automatic replay is deliberately withheld')
        return row
    def cancel(self,job_id):
        with self.lock:
            row=self.status(job_id)
            if row['status'] in TERMINAL:return row
            event=self.events.get(job_id)
            if event is None:raise BridgeError('Job belongs to another active bridge; cancel through its owning session')
            event.set();self.update(job_id,cancellation_requested=True)
        return self.status(job_id)
    def wait(self,job_id):
        # Durable deduplication may return another live session's receipt. Wait
        # for that same attempt instead of returning RUNNING or replaying it.
        future=self.futures.get(job_id)
        if future is not None:future.result()
        while True:
            row=self.status(job_id)
            if row['status'] in TERMINAL:return row
            if self.closed:raise BridgeError('Bridge is shutting down; receipt retained')
            if stamp()>row['deadline_unix']+6:raise BridgeError('Receipt did not settle by its deadline; inspect status before retrying')
            time.sleep(.05)
    @staticmethod
    def stop(child,tracked=None):
        targets={**(tracked or {}),**descendants(child.pid)}
        def send(sig):
            for pid,ticks in targets.items():
                if pid_ticks(pid)==ticks:
                    try:os.kill(pid,sig)
                    except ProcessLookupError:pass
        if child.poll() is None:
            try:os.killpg(child.pid,signal.SIGTERM)
            except ProcessLookupError:pass
        send(signal.SIGTERM)
        deadline=time.monotonic()+2
        while time.monotonic()<deadline and any(pid_ticks(pid)==ticks for pid,ticks in targets.items()):time.sleep(.02)
        send(signal.SIGKILL)
        try:child.wait(timeout=3)
        except subprocess.TimeoutExpired:child.kill();child.wait(timeout=3)
    def run(self,row,argv,event):
        started=time.monotonic();child=None;status='FAILED';output=bytearray();error=bytearray();reason=None;tracked={};next_scan=0
        try:
            if event.is_set():status='CANCELLED';return
            if not row['read_only'] and self.pause_check():status='CANCELLED';reason='URACE paused before dispatch';return
            if stamp()>=row['deadline_unix']:status='TIMED_OUT';return
            environment={k:v for k,v in os.environ.items() if k not in self.private_env};environment.update({'URACE_BRIDGE_DEPTH':str(row['depth']),'URACE_BRIDGE_DEADLINE':str(row['deadline_unix']),'URACE_BRIDGE_ROOT_REQUEST':row['root_request_id'],'URACE_BRIDGE_JOB':row['job_id'],'URACE_BRIDGE_PROJECT':row['project_id'],'URACE_BRIDGE_EXECUTOR':row['executor_id'],'URACE_BRIDGE_OUTPUT_BYTES':str(self.policy.limits['output_bytes'])})
            if self.policy.raw.get('active_product'):environment['URACE_ACTIVE_PRODUCT']=self.policy.raw['active_product']
            with self.lock:child=subprocess.Popen(self.command_factory(argv),cwd=self.policy.root,env=environment,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
            self.update(row['job_id'],status='RUNNING',started_unix=stamp(),child_pid=child.pid)
            with selectors.DefaultSelector() as selector:
                for pipe,key in [(child.stdout,'out'),(child.stderr,'err')]:os.set_blocking(pipe.fileno(),False);selector.register(pipe,selectors.EVENT_READ,key)
                while selector.get_map() or child.poll() is None:
                    if time.monotonic()>=next_scan:tracked.update(descendants(child.pid));next_scan=time.monotonic()+.5
                    if event.is_set() or (not row['read_only'] and self.pause_check()):status='CANCELLED';reason='Client cancelled or URACE paused';self.stop(child,tracked);break
                    if stamp()>=row['deadline_unix']:status='TIMED_OUT';self.stop(child,tracked);break
                    for key,_ in selector.select(.05):
                        data=os.read(key.fileobj.fileno(),65536)
                        if not data:selector.unregister(key.fileobj)
                        else:(output if key.data=='out' else error).extend(data)
                    if len(output)+len(error)>self.policy.limits['output_bytes']:status='OUTPUT_LIMIT';self.stop(child,tracked);break
                else:status='COMPLETED' if child.wait()==0 else 'FAILED'
            if status in {'COMPLETED','FAILED'}:
                try:result=json.loads(output)
                except (ValueError,UnicodeError):result={'status':'error','output':None,'error':'Worker returned invalid structured output'};status='FAILED'
                if isinstance(result,dict) and result.get('status')=='error':status='FAILED'
            else:result=None
        except Exception as exc:reason=type(exc).__name__+': '+str(exc)[:500];result=None
        finally:
            if child is not None:
                if child.poll() is None or any(pid_ticks(pid)==ticks for pid,ticks in tracked.items()):self.stop(child,tracked)
                for pipe in (child.stdout,child.stderr):pipe.close()
            fields={'status':status,'finished_unix':stamp(),'elapsed_seconds':time.monotonic()-started,'reason':reason,'exit_code':child.returncode if child is not None else None,'stderr':error[:4096].decode(errors='replace')}
            if 'result' in locals():fields['result']=result
            self.update(row['job_id'],**fields)
            with self.lock:self.events.pop(row['job_id'],None);self.futures.pop(row['job_id'],None)
    def close(self):
        with self.lock:
            self.closed=True
            for event in self.events.values():event.set()
        self.pool.shutdown(wait=True,cancel_futures=False)

def worker(argv):
    from . import cli
    from .resource_usage import product_identity
    from ._common import load_config
    if os.environ.get('URACE_BRIDGE_PROJECT')!=product_identity(load_config()):raise BridgeError('Active product changed before dispatch')
    if stamp()>=float(os.environ['URACE_BRIDGE_DEADLINE']):raise BridgeError('Execution deadline expired before dispatch')
    if not command_surface.read_only(argv) and paused():raise BridgeError('URACE paused before worker dispatch')
    result=api_interface.execute(cli.build_parser(),cli.main,argv=argv,max_output_bytes=int(os.environ['URACE_BRIDGE_OUTPUT_BYTES']))
    print(json.dumps(result,allow_nan=False));return result['exit_code']

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--worker',required=True);args=parser.parse_args()
    try:raise SystemExit(worker(json.loads(args.worker)))
    except Exception as exc:print(json.dumps({'status':'error','error':type(exc).__name__+': '+str(exc)[:500]}));raise SystemExit(2)
