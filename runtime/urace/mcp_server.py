"""MCP stdio transport over scoped URACE application operations.

No listener, scheduler or inference client starts at installation. One operator
launch grants a session; CLI/API/core execution remains authoritative.
"""
from __future__ import annotations
import json,sys,threading
from concurrent.futures import ThreadPoolExecutor
from .integration_bridge import Policy,Jobs,BridgeError,load_policy,encoded,paused,owner_lifetime

PROTOCOL='2025-06-18'
MAX_REQUEST=1048576
CALL_PROPERTIES={'command':{'type':'string','description':'Exact operation from urace_operations'},'params':{'type':'object','description':'Typed CLI/API parameters'},'request_id':{'type':'string','description':'Stable idempotency key; required for mutations'}}
def tool(name,description,properties,required=(),readonly=False):
    return {'name':name,'description':description,'inputSchema':{'type':'object','properties':properties,'required':list(required),'additionalProperties':False},'annotations':{'readOnlyHint':readonly,'destructiveHint':not readonly,'idempotentHint':readonly,'openWorldHint':not readonly}}
TOOLS=[
 tool('urace_operations','Discover delegated operations; obtain parameter schemas with command. Paginated to control context size.',{'command':{'type':'string'},'query':{'type':'string'},'offset':{'type':'integer','minimum':0},'limit':{'type':'integer','minimum':1,'maximum':100}},readonly=True),
 tool('urace_call','Run one delegated finite operation and await a structured result. Mutations require a stable request_id. Existing authority, budget and pause rules apply.',CALL_PROPERTIES,['command']),
 tool('urace_submit','Submit finite work and immediately receive a job ID. Poll or cancel through job tools. Session closure cancels unfinished work.',CALL_PROPERTIES,['command']),
 tool('urace_job_status','Read a job within this project/policy, including completion and bridge resource attribution.',{'job_id':{'type':'string'}},['job_id'],True),
 tool('urace_job_cancel','Cancel queued/running delegated work and terminate its process group. Does not erase prior effects or evidence.',{'job_id':{'type':'string'}},['job_id']),
]

class RpcError(ValueError):
    def __init__(self,code,message):super().__init__(message);self.code=code

class Server:
    def __init__(self,policy,output,*,jobs=None):
        self.policy=policy;self.jobs=jobs or Jobs(policy);self.output=output;self.write_lock=threading.Lock();self.lock=threading.RLock();self.pool=ThreadPoolExecutor(max_workers=4,thread_name_prefix='urace-mcp');self.active={};self.cancelled=set();self.ready=False;self.initialized=False
    def send(self,value):
        with self.write_lock:self.output.write(json.dumps(value,allow_nan=False)+'\n');self.output.flush()
    def error(self,identifier,code,message):self.send({'jsonrpc':'2.0','id':identifier,'error':{'code':code,'message':message}})
    def capabilities(self):
        return {**self.policy.describe(),'limits':self.policy.limits,'paused':self.jobs.pause_check(),'resources':len(self.policy.resources),'native_usage':'Native ledger counters remain authoritative; no token/credit consumption is inferred from bridge calls','job_lifecycle':'Async jobs within this stdio session; disconnect cancels active jobs. Durable receipts retained; interrupted work is not automatically replayed.'}
    def execute_tool(self,params,identifier):
        if not isinstance(params,dict) or set(params)-{'name','arguments','_meta'}:raise RpcError(-32602,'Invalid tool call')
        name=params.get('name');arguments=params.get('arguments',{})
        spec=next((t for t in TOOLS if t['name']==name),None)
        if spec is None:raise RpcError(-32602,'Unknown tool')
        schema=spec['inputSchema']
        if not isinstance(arguments,dict) or set(arguments)-set(schema['properties']) or any(k not in arguments for k in schema['required']):raise RpcError(-32602,'Invalid tool arguments')
        for k,value in arguments.items():
            kind=schema['properties'][k]['type'];expected={'string':str,'object':dict,'integer':int}[kind]
            if type(value) is not expected:raise RpcError(-32602,'Invalid argument type: '+k)
        try:
            if name=='urace_operations':value=self.policy.describe(**arguments)
            elif name=='urace_job_status':value=self.jobs.status(arguments['job_id'])
            elif name=='urace_job_cancel':value=self.jobs.cancel(arguments['job_id'])
            else:
                row=self.jobs.submit(**arguments)
                with self.lock:
                    self.active[identifier]=row['job_id']
                    if identifier in self.cancelled:self.jobs.cancel(row['job_id'])
                value=self.jobs.wait(row['job_id']) if name=='urace_call' else row
            failed=name in {'urace_call','urace_submit'} and isinstance(value,dict) and value.get('status') in {'FAILED','CANCELLED','TIMED_OUT','INTERRUPTED','OUTPUT_LIMIT'}
            return {'content':[{'type':'text','text':json.dumps(value,allow_nan=False)}],'structuredContent':value,'isError':failed}
        except (BridgeError,OSError,ValueError,KeyError,TypeError) as error:
            value={'status':'error','error':type(error).__name__+': '+str(error)}
            return {'content':[{'type':'text','text':json.dumps(value)}],'structuredContent':value,'isError':True}
    def dispatch(self,method,params,identifier):
        if method=='ping':return {}
        if method=='initialize':
            if self.initialized:raise RpcError(-32600,'Session already initialized')
            if not isinstance(params,dict) or not isinstance(params.get('protocolVersion'),str):raise RpcError(-32602,'protocolVersion required')
            self.initialized=True
            return {'protocolVersion':PROTOCOL,'capabilities':{'tools':{'listChanged':False},'resources':{'subscribe':False,'listChanged':False}},'serverInfo':{'name':'urace','version':'1.0'},'instructions':'Use delegated typed operations and scoped resources. URACE governs autonomous execution. Preserve job/request identities. Session closure cancels unfinished jobs; pause controls cannot be overridden through this transport.'}
        if not self.ready:raise RpcError(-32000,'Initialize session before requesting capabilities')
        if method=='tools/list':return {'tools':TOOLS}
        if method=='tools/call':return self.execute_tool(params,identifier)
        if method=='resources/list':
            items=[{'uri':'urace://session/capabilities','name':'URACE delegated capabilities and resource allowances','mimeType':'application/json'}]
            items.extend({k:v for k,v in r.items() if k in {'uri','name','mimeType'}} for r in self.policy.resources.values())
            for r in items:r.setdefault('name',r['uri'])
            return {'resources':items}
        if method=='resources/templates/list':return {'resourceTemplates':[{'uriTemplate':'urace://jobs/{job_id}','name':'Scoped job receipt','mimeType':'application/json'}]}
        if method=='resources/read':
            if not isinstance(params,dict) or not isinstance(params.get('uri'),str):raise RpcError(-32602,'Resource URI required')
            uri=params['uri']
            if uri=='urace://session/capabilities':item={'uri':uri,'mimeType':'application/json','text':json.dumps(self.capabilities())}
            elif uri.startswith('urace://jobs/'):item={'uri':uri,'mimeType':'application/json','text':json.dumps(self.jobs.status(uri.removeprefix('urace://jobs/')))}
            else:
                item=self.policy.read_resource(uri)
                item['_meta']={'sha256':item.pop('sha256')}
            return {'contents':[item]}
        raise RpcError(-32601,'Method not found')
    def handle(self,request):
        identifier=request.get('id')
        try:self.send({'jsonrpc':'2.0','id':identifier,'result':self.dispatch(request['method'],request.get('params',{}),identifier)})
        except RpcError as error:self.error(identifier,error.code,str(error))
        except (ValueError,KeyError,TypeError,OSError) as error:self.error(identifier,-32602,str(error))
        except Exception as error:self.error(identifier,-32603,'Internal error: '+type(error).__name__)
        finally:
            with self.lock:self.active.pop(identifier,None);self.cancelled.discard(identifier)
    def receive(self,request):
        if not isinstance(request,dict) or request.get('jsonrpc')!='2.0' or not isinstance(request.get('method'),str):self.error(None,-32600,'Invalid JSON-RPC request');return
        identifier=request.get('id')
        if 'id' not in request:
            if request['method']=='notifications/initialized' and self.initialized:self.ready=True
            elif request['method']=='notifications/cancelled':
                params=request.get('params',{});target=params.get('requestId') if isinstance(params,dict) else None
                if type(target) not in (str,int):return
                with self.lock:
                    if target in self.active:
                        self.cancelled.add(target);job=self.active[target]
                        if job:
                            try:self.jobs.cancel(job)
                            except BridgeError:pass
            return
        if type(identifier) not in (str,int):self.error(None,-32600,'Request ID must be a string or integer');return
        with self.lock:
            if identifier in self.active:self.error(identifier,-32600,'Request ID already active');return
            if len(self.active)>=self.policy.limits['queued_jobs']+4 and request['method']=='tools/call' and isinstance(request.get('params'),dict) and request['params'].get('name')=='urace_call':self.error(identifier,-32000,'Request queue busy');return
            self.active[identifier]=None
        params=request.get('params',{})
        if request['method']=='tools/call' and isinstance(params,dict) and params.get('name')=='urace_call':self.pool.submit(self.handle,request)
        else:self.handle(request)
    def close(self):
        # Prevent queued RPC calls from dispatching work after EOF, then join jobs.
        self.jobs.close();self.pool.shutdown(wait=True,cancel_futures=False)

def serve(parser,policy_path=None,input_stream=None,output_stream=None):
    source=input_stream or sys.stdin;target=output_stream or sys.stdout
    try:policy=load_policy(parser,policy_path)
    except (ValueError,OSError,KeyError) as error:print('URACE MCP: '+str(error),file=sys.stderr);return 2
    server=Server(policy,target)
    with owner_lifetime():
        try:
            while True:
                line=source.readline(MAX_REQUEST+1)
                if not line:break
                if len(line.encode('utf-8'))>MAX_REQUEST:
                    server.error(None,-32700,'Request exceeds byte allowance');return 2
                try:request=json.loads(line,parse_constant=lambda value:(_ for _ in ()).throw(ValueError('Nonfinite JSON')))
                except (ValueError,RecursionError):server.error(None,-32700,'Invalid JSON');continue
                server.receive(request)
        except (KeyboardInterrupt,BrokenPipeError):return 130
        finally:server.close()
    return 0
