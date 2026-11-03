from datetime import datetime,timezone
import hashlib,json,os,select,selectors,signal,subprocess,time
from common import BASE,atomic,append,guard,reserve
from accounting import claude_usage,codex_usage,metadata_safe
from stream_usage import StreamUsage,next_claude_controls,claude_transport_policy
SCHEMA={'type':'object','properties':{'source':{'type':'string'},'notes':{'type':'string'}},'required':['source','notes'],'additionalProperties':False}

class Transport:
    def __init__(self,command,cwd,env=None,wall_limit=None):
        self.wall_limit=int(wall_limit if wall_limit is not None else os.environ.get('URACE_NATIVE_WALL_SECONDS','300'))
        if not 60<=self.wall_limit<=480:raise ValueError('Invalid native wall allowance')
        self.started=time.monotonic();self.process=subprocess.Popen(command,cwd=cwd,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
        os.set_blocking(self.process.stdin.fileno(),False)
        self.selector=selectors.DefaultSelector();self.selector.register(self.process.stdout,selectors.EVENT_READ,'stdout');self.selector.register(self.process.stderr,selectors.EVENT_READ,'stderr');self.buffer=bytearray();self.stderr_bytes=0;self.total=0
    def write(self,data):
        view=memoryview(data)
        while view:
            if time.monotonic()-self.started>=self.wall_limit:raise TimeoutError('Native input wall cap exceeded')
            if not select.select([], [self.process.stdin.fileno()], [], .1)[1]:continue
            try:sent=os.write(self.process.stdin.fileno(),view)
            except BlockingIOError:continue
            if sent<=0:raise RuntimeError('Native input pipe closed')
            view=view[sent:]
    def send(self,value):
        self.write((json.dumps(value)+'\n').encode())
    def line(self):
        while time.monotonic()-self.started<self.wall_limit:
            if b'\n' in self.buffer:
                line,_,rest=self.buffer.partition(b'\n');self.buffer=bytearray(rest);return line
            for key,_ in self.selector.select(.1):
                part=os.read(key.fileobj.fileno(),65536);self.total+=len(part)
                if self.total>2097152:raise RuntimeError('Native output cap exceeded')
                if not part:self.selector.unregister(key.fileobj);continue
                if key.data=='stdout':self.buffer.extend(part)
                else:self.stderr_bytes+=len(part)
            if not self.selector.get_map():
                if self.buffer:line=bytes(self.buffer);self.buffer.clear();return line
                return None
        raise TimeoutError('Native wall cap exceeded')
    def close(self):
        if self.process.poll() is None:
            try:os.killpg(self.process.pid,signal.SIGTERM)
            except ProcessLookupError:pass
        try:self.process.wait(timeout=3)
        except subprocess.TimeoutExpired:os.killpg(self.process.pid,signal.SIGKILL);self.process.wait()
        self.selector.close()
        for stream in (self.process.stdin,self.process.stdout,self.process.stderr):
            if stream and not stream.closed:stream.close()

def claude(prompt,work,record):
    policy=claude_transport_policy();record['transport_policy']=policy
    command=['claude','-p','--model',os.environ.get('URACE_TRIAL_MODEL','claude-sonnet-4-6'),'--effort',record['effort'],'--output-format','stream-json','--verbose','--tools','','--permission-mode','dontAsk','--strict-mcp-config','--mcp-config',str(BASE/'empty-mcp.json'),'--disable-slash-commands','--no-session-persistence','--setting-sources','user','--settings','{"disableAllHooks":true,"enableAllProjectMcpServers":false}','--max-turns',str(policy['max_turns']),'--json-schema',json.dumps(SCHEMA,separators=(',',':'))]
    env={**os.environ,**next_claude_controls()}
    env.pop('CLAUDE_CODE_DISABLE_ADAPTIVE_THINKING',None);env.pop('MAX_THINKING_TOKENS',None)
    client=Transport(command,work,env);usage=StreamUsage();envelope=None
    try:
        record['inference_requested']=True;client.write(prompt.encode());client.process.stdin.close()
        while True:
            line=client.line()
            if line is None:break
            try:event=json.loads(line)
            except ValueError:continue
            usage.ingest(event)
            if event.get('type')=='rate_limit_event':
                info=event.get('rate_limit_info',{})
                record.setdefault('quota_events',[]).append({key:info[key] for key in ('status','resetsAt','rateLimitType','utilization','isUsingOverage','overageStatus') if key in info})
            if event.get('type')=='assistant':
                atomic(BASE/'transport'/f"{record['id']}-partial-usage.json",usage.snapshot())
            if event.get('type')=='result':envelope=event
        client.process.wait(timeout=3)
        if envelope is None:raise RuntimeError('Claude returned no final envelope')
        record.update({'returncode':client.process.returncode,'is_error':envelope.get('is_error'),'subtype':envelope.get('subtype'),'usage':envelope.get('usage'),'model_usage':envelope.get('modelUsage'),'provider_reported_total_cost_usd':envelope.get('total_cost_usd')})
        record['structured_output_diagnostics']=(usage.final or {}).get('structured_output_diagnostics')
        if envelope.get('subtype')=='error_max_structured_output_retries':record['transport_failure_class']='STRUCTURED_OUTPUT_RETRY_EXHAUSTED'
        measured=claude_usage(record);record['tokens']=measured.get('tokens')
        if client.process.returncode or envelope.get('is_error') is not False:
            detail=envelope.get('result')
            if not isinstance(detail,str) or not detail.strip():detail='Claude failed ('+str(envelope.get('subtype','unknown'))[:100]+'; exit '+str(client.process.returncode)+')'
            raise RuntimeError(detail[:500])
        structured=envelope.get('structured_output')
        if isinstance(structured,dict):return structured,envelope
        text=envelope.get('result')
        if not isinstance(text,str):raise RuntimeError('Claude returned no artifact JSON text')
        record['artifact_text_sha256']=hashlib.sha256(text.encode()).hexdigest();record['artifact_text_bytes']=len(text.encode())
        return json.loads(text),envelope
    finally:
        record['partial_usage']=usage.snapshot();client.close()

def failed_turn_message(turn,fallback):
    error=turn.get('error')
    detail=error.get('message') if isinstance(error,dict) else error
    return fallback+(': '+detail[:500] if isinstance(detail,str) and detail else '')

def codex(prompt,work,record):
    command=['codex','app-server','--enable','stable_environment_tools']
    for feature in ('shell_tool','unified_exec','apps','plugins','multi_agent','code_mode','code_mode_host','computer_use','browser_use','image_generation','view_image','hooks','shell_snapshot','memories'):
        command+=['--disable',feature]
    client=Transport(command,work);messages=[];usage=None;ended=None;inference_requested=False
    def note(event):
        nonlocal usage,ended
        method=event.get('method');params=event.get('params',{})
        if method=='thread/tokenUsage/updated':
            usage=params.get('tokenUsage');record['usage']=usage
            atomic(BASE/'transport'/f"{record['id']}-partial-usage.json",{'usage':usage,'reasoning_text_retained':False})
        if method=='item/completed':
            item=params.get('item',{})
            if item.get('type')=='agentMessage':messages.append(item.get('text',''))
            elif item.get('type') not in ('userMessage','reasoning'):raise RuntimeError('Unexpected native tool event in artifact-only mode')
        if method=='turn/completed':ended=params.get('turn')
        if 'method' in event and 'id' in event:raise RuntimeError('No native approval or external tool request is authorized')
    def response(identifier):
        while True:
            raw=client.line()
            if raw is None:raise RuntimeError('Native server ended')
            event=json.loads(raw)
            if event.get('id')==identifier:
                if 'error' in event:raise RuntimeError(str(event['error'])[:500])
                return event['result']
            note(event)
    try:
        client.send({'id':1,'method':'initialize','params':{'clientInfo':{'name':'urace-productive-trial','version':'1'},'capabilities':{'experimentalApi':True}}});response(1);client.send({'method':'initialized','params':{}})
        client.send({'id':2,'method':'thread/start','params':{'cwd':str(work),'model':os.environ.get('URACE_TRIAL_MODEL','gpt-5.6-sol'),'ephemeral':True,'environments':[],'dynamicTools':[],'approvalPolicy':'never','sandbox':'read-only'}});thread=response(2)
        record['provider_reported_model']=thread.get('model') or thread.get('thread',{}).get('model')
        client.send({'id':3,'method':'mcpServerStatus/list','params':{'limit':100}})
        if response(3).get('data')!=[]:raise RuntimeError('Unexpected MCP server in constrained executor')
        try:
            client.send({'id':5,'method':'account/rateLimits/read','params':{}})
            record['quota_before']=quota_view(response(5))
        except Exception as error:record['quota_before_error']=type(error).__name__
        if (record.get('quota_before') or {}).get('ordinaryUsageAllowed') is False:
            record['tokens']=0
            raise RuntimeError('Provider reports ordinary usage unavailable before inference')
        inference_requested=True
        client.send({'id':4,'method':'turn/start','params':{'threadId':thread['thread']['id'],'input':[{'type':'text','text':prompt,'text_elements':[]}],'environments':[],'effort':record['effort'],'outputSchema':SCHEMA}});response(4)
        while ended is None:
            raw=client.line()
            if raw is None:raise RuntimeError('Native server ended before turn completion')
            note(json.loads(raw))
        record.update({'turn_status':ended.get('status'),'usage':usage})
        record['tokens']=codex_usage(record).get('tokens')
        if ended.get('status')!='completed' or not messages:
            record['turn_error']=ended.get('error')
            raise RuntimeError(failed_turn_message(ended,'Codex did not deliver artifact'))
        try:
            client.send({'id':6,'method':'account/rateLimits/read','params':{}})
            record['quota_after']=quota_view(response(6))
        except Exception as error:record['quota_after_error']=type(error).__name__
        return json.loads(messages[-1]),None
    finally:
        try:
            record['inference_requested']=inference_requested
            if not inference_requested:record['tokens']=0
            elif record.get('usage'):record['tokens']=codex_usage(record).get('tokens')
        finally:client.close()


def quota_view(value):
    keys=('limitId','limitName','normalModelSlug','primary','secondary','credits','individualLimit','spendControlReached','planType','rateLimitReachedType')
    result={'ordinaryUsageAllowed':value.get('ordinaryUsageAllowed'),'attribution':'Account-wide snapshot; concurrent usage prevents assigning a balance change to this job'}
    rate=value.get('rateLimits') or {}
    result['rateLimits']={key:rate[key] for key in keys if key in rate}
    if isinstance(value.get('rateLimitsByLimitId'),dict):
        result['rateLimitsByLimitId']={name:{key:row[key] for key in keys if key in row} for name,row in value['rateLimitsByLimitId'].items() if isinstance(row,dict)}
    result['available_rate_limit_reset_credit_count']=(value.get('rateLimitResetCredits') or {}).get('availableCount')
    return result

def run(provider,prompt):
    effort=os.environ.get('URACE_TRIAL_EFFORT','medium')
    resource_effort=os.environ.get('URACE_RESOURCE_EFFORT','medium')
    if effort not in {'low','medium','high'}:raise ValueError('Invalid executor effort')
    if len(prompt.encode())>65536:raise RuntimeError('Prompt exceeds frozen byte budget')
    identifier=reserve(provider);work=BASE/'work'/identifier;work.mkdir()
    record={'kind':'finished','id':identifier,'provider':provider,'inference_requested':False,'at':datetime.now(timezone.utc).isoformat(),'tokens':None,'provider_reported_total_cost_usd':None,'subscription_credit_decrement':None,'prompt_sha256':hashlib.sha256(prompt.encode()).hexdigest(),'failure':None,'effort':effort,'urace_resource_effort':resource_effort,'wall_limit_seconds':int(os.environ.get('URACE_NATIVE_WALL_SECONDS','300'))}
    contract=json.loads((BASE/'contract.json').read_text())
    record.update(product_id=contract['product_id'],product=contract['target_product'],trial_id=contract.get('trial_id'))
    record.update(requested_model=os.environ.get('URACE_TRIAL_MODEL','gpt-5.6-sol' if provider=='codex' else 'claude-sonnet-4-6'),baseline_commit=contract.get('baseline_commit'),job_id=os.environ.get('URACE_TRIAL_JOB_ID'),prompt_bytes=len(prompt.encode()),provider_reported_model=None)
    from urace._common import integration_context
    if integration_context():record['integration_context']=integration_context()
    started=time.monotonic();value=None;envelope=None
    try:
        version=subprocess.run([provider,'--version'],capture_output=True,text=True,timeout=10)
        record['client_version']=version.stdout.strip()[:100]
    except Exception as error:record['client_version_error']=type(error).__name__
    try:
        value,envelope=(claude if provider=='claude' else codex)(prompt,work,record)
        if not isinstance(value,dict) or set(value)!={'source','notes'} or not all(isinstance(value[k],str) for k in value):raise RuntimeError('Artifact schema mismatch')
        if not value['source'].strip() or len(value['source'].encode())>32768:raise RuntimeError('Empty or oversized artifact')
    except Exception as error:record['failure']=type(error).__name__+': '+str(error)[:500]
    finally:
        if record.get('tokens') is None and provider=='codex' and record.get('usage'):
            try:record['tokens']=codex_usage(record).get('tokens')
            except (ValueError,TypeError,KeyError,AttributeError) as error:
                record['accounting_error']=type(error).__name__+': '+str(error)[:200]
        record['wall_seconds']=time.monotonic()-started
        try:record['accounting_details']=(claude_usage if provider=='claude' else codex_usage)(record)
        except (ValueError,TypeError,KeyError,AttributeError) as error:record['accounting_details']={'known':False,'reason':type(error).__name__+': '+str(error)[:200]}
        if provider=='claude' and isinstance(record.get('model_usage'),dict):record['provider_reported_model_ids']=list(record['model_usage'])
        if record.get('provider_reported_model') is None:record['provider_reported_model_reason']='Provider did not return a resolved model identifier; requested model retained separately'
        from accounting import settle
        settle(record,provider)
        record=metadata_safe(record)
        atomic(BASE/'transport'/f'{identifier}.json',record)
        with guard():append(record)
    return value,envelope,record
