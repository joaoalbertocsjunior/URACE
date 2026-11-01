"""Native MCP project tools. Untrusted programs run only in a networkless container."""
from pathlib import Path
import json,os,subprocess,sys,time,hashlib
from common import atomic
from executable_sandbox import IMAGE,SandboxInfrastructureError
MAX_BYTES=1048576
TOOLS=[{'name':'list_files','description':'List the isolated project files','inputSchema':{'type':'object','properties':{},'additionalProperties':False}}, {'name':'read_file','description':'Read a UTF-8 file inside the isolated project','inputSchema':{'type':'object','properties':{'path':{'type':'string'},'start_line':{'type':'integer','minimum':1},'end_line':{'type':'integer','minimum':1}},'required':['path'],'additionalProperties':False}}, {'name':'write_file','description':'Write implementation source inside the isolated project','inputSchema':{'type':'object','properties':{'path':{'type':'string'},'content':{'type':'string'}},'required':['path','content'],'additionalProperties':False}}, {'name':'run_checks','description':'Run immutable published development checks, with diagnostic feedback','inputSchema':{'type':'object','properties':{},'additionalProperties':False}}, {'name':'run_python','description':'Run Python with arguments inside the isolated networkless project container','inputSchema':{'type':'object','properties':{'args':{'type':'array','items':{'type':'string'},'maxItems':30}},'required':['args'],'additionalProperties':False}}]

for tool in TOOLS:tool['annotations']={'readOnlyHint':tool['name'] in ('list_files','read_file'),'destructiveHint':False,'openWorldHint':False}

def confined(root,relative):
    root=Path(root).resolve()
    if not isinstance(relative,str) or not relative or Path(relative).is_absolute() or '..' in Path(relative).parts:raise ValueError('Project-relative path required')
    p=root/relative
    if p.is_symlink() or not p.resolve().is_relative_to(root):raise ValueError('Project path escape')
    return p

def inventory(root):
    root=Path(root);items=[]
    for p in root.rglob('*'):
        if p.is_symlink():raise ValueError('Project symlinks are prohibited')
        if p.is_file():
            if p.stat().st_size>MAX_BYTES:raise ValueError('Project file size limit')
            items.append(str(p.relative_to(root)))
    if len(items)>100 or sum((root/n).stat().st_size for n in items)>4194304:raise ValueError('Project size limit')
    return sorted(items)

def container(root,args,*,checks=None,stdin='',wall=30,writable=True):
    root=Path(root).resolve();inventory(root)
    if not isinstance(args,list) or len(args)>30 or any(not isinstance(x,str) or len(x)>32768 for x in args):raise ValueError('Invalid Python arguments')
    cmd=['docker','run','-i','--rm','--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--user',str(os.getuid())+':'+str(os.getgid()),'--pids-limit','32','--memory','256m','--memory-swap','256m','--cpus','1','--tmpfs','/tmp:rw,nosuid,noexec,size=32m','--env','PYTHONDONTWRITEBYTECODE=1','--workdir','/workspace','--mount','type=bind,src='+str(root)+',dst=/workspace'+('' if writable else ',readonly')]
    if checks:cmd+=['--mount','type=bind,src='+str(Path(checks).resolve())+',dst=/public_checks.py,readonly']
    wrapper='import os,sys,signal,resource,subprocess;resource.setrlimit(resource.RLIMIT_CPU,(8,8));signal.signal(signal.SIGALRM,lambda *a:os._exit(124));signal.alarm(25);sys.exit(subprocess.call([sys.executable,*sys.argv[1:]]))'
    cmd+=[IMAGE,'python3','-c',wrapper,*args]
    name='urace-project-'+os.urandom(8).hex();cmd[3:3]=['--name',name]
    started=time.monotonic();proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    import selectors
    selector=selectors.DefaultSelector();out=bytearray();err=bytearray();data=memoryview(stdin.encode())
    for stream in (proc.stdin,proc.stdout,proc.stderr):os.set_blocking(stream.fileno(),False)
    selector.register(proc.stdin,selectors.EVENT_WRITE,'in');selector.register(proc.stdout,selectors.EVENT_READ,'out');selector.register(proc.stderr,selectors.EVENT_READ,'err')
    try:
        while selector.get_map():
            if time.monotonic()-started>wall:raise TimeoutError('Project command wall limit')
            for key,_ in selector.select(.05):
                stream=key.fileobj
                if key.data=='in':
                    try:data=data[os.write(stream.fileno(),data[:16384]):] if data else data
                    except BrokenPipeError:data=data[len(data):]
                    if not data:selector.unregister(stream);stream.close()
                else:
                    part=os.read(stream.fileno(),65536)
                    if not part:selector.unregister(stream);continue
                    (out if key.data=='out' else err).extend(part)
                    if len(out)+len(err)>MAX_BYTES:raise ValueError('Project output limit')
        proc.wait(timeout=2)
        if proc.returncode in (125,126,127):raise SandboxInfrastructureError(err.decode(errors='replace')[:500])
        return {'returncode':proc.returncode,'stdout':out.decode(errors='replace'),'stderr':err.decode(errors='replace'),'seconds':time.monotonic()-started}
    finally:
        selector.close()
        if proc.poll() is None:
            subprocess.run(['docker','kill',name],capture_output=True,timeout=10);proc.kill();proc.wait()
        for stream in (proc.stdin,proc.stdout,proc.stderr):
            if not stream.closed:stream.close()

def call(context,name,arguments):
    root=Path(context['workspace']);inventory(root)
    if name=='list_files':return inventory(root)
    if name=='read_file' and isinstance(arguments.get('path'),str) and arguments['path'].startswith('@'):
        from urace.executor_capabilities import read
        return read(context.get('capabilities',{'skills':[],'requirements':{},'requirement_source_sha256':None,'clarifications':{}}),arguments['path'],arguments.get('start_line',1),arguments.get('end_line'))
    if name=='write_file' and isinstance(arguments.get('path'),str) and arguments['path'].startswith('@question/'):
        from urace.executor_capabilities import clarify
        answer=clarify(context['capabilities'],arguments['path'][len('@question/'):],arguments['content'])
        counts=context.setdefault('_clarification_counts',{});key=answer['id'];counts[key]=counts.get(key,0)+1
        if answer['status']=='SOURCE_PASSAGE_RETURNED' and counts[key]>=3:answer.update(status='NEEDS_OWNER_CLARIFICATION',next_action='Repeated source exchange has not resolved the question; wait for owner input rather than retrying inference')
        return answer
    if name=='read_file':
        text=confined(root,arguments['path']).read_text()
        if 'start_line' not in arguments and 'end_line' not in arguments:return text
        start=arguments.get('start_line',1);end=arguments.get('end_line',start+199)
        if type(start) is not int or type(end) is not int or start<1 or end<start or end-start>=1000:raise ValueError('Invalid bounded line range')
        return ''.join(text.splitlines(True)[start-1:end])
    if name=='write_file':
        path=confined(root,arguments['path'])
        if arguments['path'] not in context['allowed_files'] or not isinstance(arguments['content'],str) or len(arguments['content'].encode())>MAX_BYTES:raise ValueError('Write outside declared implementation scope')
        path.parent.mkdir(parents=True,exist_ok=True);path.write_text(arguments['content']);return {'written':arguments['path']}
    if name=='run_checks':return container(root,['/public_checks.py'],checks=context['public_checks'])
    if name=='run_python':return container(root,arguments['args'])
    raise ValueError('Unknown project tool')

def serve(context_path):
    context=json.loads(Path(context_path).read_text());log=Path(context['tool_log'])
    for line in sys.stdin:
        request={}
        try:
            if len(line)>MAX_BYTES:raise ValueError('MCP request size limit')
            request=json.loads(line);method=request.get('method');params=request.get('params',{});result={}
            if method=='initialize':result={'protocolVersion':params.get('protocolVersion','2024-11-05'),'capabilities':{'tools':{}},'serverInfo':{'name':'urace-project','version':'1'}}
            elif method=='tools/list':result={'tools':TOOLS}
            elif method=='tools/call':
                start=time.monotonic()
                try:value=call(context,params['name'],params.get('arguments',{}));result={'content':[{'type':'text','text':json.dumps(value,allow_nan=False)}]}
                except Exception as error:result={'isError':True,'content':[{'type':'text','text':type(error).__name__+': '+str(error)[:1000]}]}
                from urace.authenticated_journal import append_row
                append_row(log,{'tool':params['name'],'path':params.get('arguments',{}).get('path') if params['name'] in ('read_file','write_file') else None,'clarification':value if params['name']=='write_file' and params.get('arguments',{}).get('path','').startswith('@question/') and not result.get('isError') else None,'response_bytes':len(json.dumps(value).encode()) if not result.get('isError') else None,'seconds':time.monotonic()-start,'error':result.get('isError',False)})
            elif method=='ping':result={}
            elif method.startswith('notifications/'):continue
            else:raise ValueError('Unsupported MCP method')
            if 'id' in request:print(json.dumps({'jsonrpc':'2.0','id':request['id'],'result':result}),flush=True)
        except Exception as error:
            if 'id' in request:print(json.dumps({'jsonrpc':'2.0','id':request['id'],'error':{'code':-32602,'message':str(error)[:500]}}),flush=True)
if __name__=='__main__':serve(sys.argv[1])
