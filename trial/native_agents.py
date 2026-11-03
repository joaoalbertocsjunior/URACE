"""Real Codex/Claude coding agents with identical confined MCP project tools."""
from pathlib import Path
from datetime import datetime,timezone
import json,os,hashlib,time,subprocess
from common import BASE,atomic,reserve,guard,append,operations_root
from providers import Transport,quota_view,failed_turn_message
from accounting import claude_usage,codex_usage,metadata_safe
from stream_usage import StreamUsage,next_claude_controls
from project_tools import TOOLS,inventory

def codex(prompt,work,record,context_path):
    command=['codex','app-server','--enable','stable_environment_tools','--enable','code_mode_host']
    for feature in ('shell_tool','unified_exec','apps','plugins','multi_agent','code_mode','computer_use','browser_use','image_generation','view_image','hooks','shell_snapshot','memories'):command+=['--disable',feature]
    for key,value in {'command':'/usr/bin/python3','args':[str(BASE/'project_tools.py'),str(context_path)],'enabled_tools':[t['name'] for t in TOOLS],'required':True}.items():command+=['-c','mcp_servers.project.'+key+'='+json.dumps(value)]
    client=Transport(command,work,wall_limit=record['wall_limit_seconds']);messages=[];ended=None;requested=False
    def event(e):
        nonlocal ended
        method=e.get('method');params=e.get('params',{})
        if method=='thread/tokenUsage/updated':record['usage']=params.get('tokenUsage')
        if method=='turn/completed':ended=params.get('turn')
        if method=='item/completed':
            item=params.get('item',{});kind=item.get('type')
            if kind=='agentMessage':messages.append(item.get('text',''))
            elif kind not in ('userMessage','reasoning','mcpToolCall','plan','contextCompaction'):raise RuntimeError('Tool outside project MCP scope: '+str(kind))
        if 'method' in e and 'id' in e:raise RuntimeError('Unapproved native permission request')
    def response(i):
        while True:
            line=client.line()
            if line is None:raise RuntimeError('Native agent server ended')
            e=json.loads(line)
            if e.get('id')==i:
                if 'error' in e:raise RuntimeError(str(e['error'])[:500])
                return e['result']
            event(e)
    try:
        client.send({'id':1,'method':'initialize','params':{'clientInfo':{'name':'urace-project-work','version':'1'},'capabilities':{'experimentalApi':True}}});response(1);client.send({'method':'initialized','params':{}})
        client.send({'id':2,'method':'thread/start','params':{'cwd':str(work),'model':record['requested_model'],'ephemeral':True,'environments':[],'approvalPolicy':'never','sandbox':'workspace-write'}});thread=response(2);record['instruction_sources']=thread.get('instructionSources',[]);record['provider_reported_model']=thread.get('model')
        client.send({'id':3,'method':'mcpServerStatus/list','params':{'limit':100,'threadId':thread['thread']['id']}});servers=response(3).get('data',[])
        record['project_tool_names']={r['name']:list(r.get('tools',{})) for r in servers}
        if {r.get('name') for r in servers}!={'project'}:raise RuntimeError('Project MCP server unavailable or unexpected server configured')
        client.send({'id':5,'method':'account/rateLimits/read','params':{}});record['quota_before']=quota_view(response(5))
        if record['quota_before'].get('ordinaryUsageAllowed') is False:record['tokens']=0;raise RuntimeError('Provider reports ordinary usage unavailable before inference')
        requested=True;client.send({'id':4,'method':'turn/start','params':{'threadId':thread['thread']['id'],'input':[{'type':'text','text':prompt,'text_elements':[]}],'environments':[],'effort':record['effort']}});response(4)
        while ended is None:
            line=client.line()
            if line is None:raise RuntimeError('Native agent ended before completion')
            event(json.loads(line))
        record['turn_status']=ended.get('status')
        if ended.get('status')!='completed':
            record['turn_error']=ended.get('error')
            raise RuntimeError(failed_turn_message(ended,'Native agent did not complete'))
        return {'source':messages[-1] if messages else 'Project turn completed','notes':'Project source is in isolated workspace'},None
    finally:
        record['inference_requested']=requested
        if not requested:record['tokens']=0
        elif record.get('usage'):record['tokens']=codex_usage(record).get('tokens')
        client.close()

def claude(prompt,work,record,context_path):
    mcp=work/'project-mcp.json';atomic(mcp,{'mcpServers':{'project':{'command':'/usr/bin/python3','args':[str(BASE/'project_tools.py'),str(context_path)]}}})
    command=['claude','-p','--model',record['requested_model'],'--effort',record['effort'],'--output-format','stream-json','--verbose','--tools','','--allowedTools','mcp__project__*','--permission-mode','dontAsk','--strict-mcp-config','--mcp-config',str(mcp),'--disable-slash-commands','--no-session-persistence','--setting-sources','user','--settings','{"disableAllHooks":true,"enableAllProjectMcpServers":false}','--max-turns','30']
    env={**os.environ,**next_claude_controls()};client=Transport(command,work,env,wall_limit=record['wall_limit_seconds']);usage=StreamUsage();envelope=None
    try:
        record['inference_requested']=True;client.write(prompt.encode());client.process.stdin.close()
        while True:
            line=client.line()
            if line is None:break
            try:e=json.loads(line)
            except ValueError:continue
            usage.ingest(e)
            if e.get('type')=='rate_limit_event':record.setdefault('quota_events',[]).append(e.get('rate_limit_info',{}))
            if e.get('type')=='result':envelope=e
        client.process.wait(timeout=3)
        if envelope is None:raise RuntimeError('Claude project agent returned no final envelope')
        record.update(returncode=client.process.returncode,is_error=envelope.get('is_error'),subtype=envelope.get('subtype'),usage=envelope.get('usage'),model_usage=envelope.get('modelUsage'),provider_reported_total_cost_usd=envelope.get('total_cost_usd'))
        record['tokens']=claude_usage(record).get('tokens')
        if client.process.returncode or envelope.get('is_error') is not False:raise RuntimeError(str(envelope.get('result') or envelope.get('subtype'))[:500])
        return {'source':str(envelope.get('result') or 'Project agent completed')[:32768],'notes':'Project source is in isolated workspace'},envelope
    finally:record['partial_usage']=usage.snapshot();client.close()

def run(provider,prompt,workspace,public_checks,allowed_files,*,model,effort,job_id,wall=300,product_id=None,product_name=None,resource_effort="medium",reference_metadata=None,context_profile=None,task_manifest=None):
    if resource_effort not in ('low','medium','high'):raise ValueError('Invalid URACE resource effort')
    if provider not in ('codex','claude') or effort not in ('low','medium','high') or not 60<=wall<=480:raise ValueError('Invalid native project profile')
    workspace=Path(workspace).resolve();inventory(workspace)
    # The model process gets no native filesystem/shell tool; all project tools
    # enforce this root and execute code only in a networkless container.
    from common import _governor
    override={'product_id':product_id,'product':product_name} if product_id else None
    from urace import executor_capabilities as capabilities
    config=json.loads((BASE.parent/'runtime/urace/config.json').read_text()) if (BASE.parent/'runtime/urace/config.json').exists() else {}
    packet=capabilities.prepare(config,provider,task_manifest or {})
    if packet['skills'] or packet['requirements']:
        prompt+='\nOptional task aids via existing project tools: read_file @skills, @skill/ID, @requirements, @requirement/ID; @attention and @related/ID expose declared context links without hiding source. Ask a precise question with write_file @question/REQUIREMENT_ID and JSON {question,needs_owner}; request an owner answer when unresolved. Never infer understanding from availability; unchanged public checks and scope still apply.'
    identifier=_governor().reserve(BASE,provider,product_override=override,request={'wall':wall,'job_id':job_id});work=operations_root()/'agent-sessions'/identifier;work.mkdir(parents=True);context=work/'project-context.json';atomic(context,{'workspace':str(workspace),'public_checks':str(Path(public_checks).resolve()),'allowed_files':allowed_files,'tool_log':str(work/'tools.jsonl'),'capabilities':packet})
    record={'kind':'finished','id':identifier,'provider':provider,'inference_requested':False,'at':datetime.now(timezone.utc).isoformat(),'tokens':None,'failure':None,'effort':effort,'requested_model':model,'job_id':job_id,'artifact_directory':str(work),'execution_mode':'native-project-agent','wall_limit_seconds':wall,'subscription_credit_decrement':None,'prompt_sha256':hashlib.sha256(prompt.encode()).hexdigest(),'prompt_bytes':len(prompt.encode()),'urace_resource_effort':resource_effort,'specification_reference':reference_metadata,'context_profile':context_profile,'skills_and_context_contract_sha256':packet['contract_sha256'],'skill_selection':[{k:item[k] for k in ('id','version','sha256','expected_benefit','status')} for item in packet['skills']],'skill_setup':'Pinned instruction packets only; no host/plugin installation or extra model call','owner_clarification_sha256':capabilities.digest(packet['clarifications'])}
    from urace._common import integration_context
    if integration_context():record['integration_context']=integration_context()
    contract=json.loads((BASE/'contract.json').read_text());record.update(product_id=contract['product_id'],product=contract['target_product'],trial_id=contract.get('trial_id'),baseline_commit=contract.get('baseline_commit'))
    if override:record.update(override)
    atomic(work/'prompt.json',{'text':prompt,'sha256':record['prompt_sha256']})
    started=time.monotonic();value=envelope=None
    try:
        record['client_version']=subprocess.run([provider,'--version'],capture_output=True,text=True,timeout=10).stdout.strip()[:100]
        value,envelope=(codex if provider=='codex' else claude)(prompt,work,record,context)
        atomic(work/'agent-result.json',value)
        if reference_metadata is not None:
            log=work/'tools.jsonl';events=[json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
            record['reference_reads']=[e['path'] for e in events if e.get('tool')=='read_file' and isinstance(e.get('path'),str) and e['path'].startswith('SPECIFICATION_') and e['path'].endswith('.md') and not e.get('error')]
            if not record['reference_reads']:raise RuntimeError('Specification reference protocol not met: no recorded document chunk read')
    except Exception as error:record['failure']=type(error).__name__+': '+str(error)[:500]
    finally:
        log=work/'tools.jsonl'
        try:events=[json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
        except (ValueError,OSError):events=[];record['failure']='Context receipt log unreadable; success withheld'
        record['context_feedback']=capabilities.feedback(packet,events)
        if record['context_feedback']['status']=='AWAITING_OWNER_CLARIFICATION':record['delivery_blocked_reason']='OWNER_CLARIFICATION_REQUIRED; transport success is not delivery success'
        elif record['context_feedback']['status']!='PROTOCOL_SATISFIED':record['failure']='Context protocol: '+record['context_feedback']['status']
        record['wall_seconds']=time.monotonic()-started
        try:record['accounting_details']=(codex_usage if provider=='codex' else claude_usage)(record)
        except Exception as error:record['accounting_details']={'known':False,'reason':type(error).__name__}
        from accounting import settle
        settle(record,provider)
        record=metadata_safe(record);atomic(BASE/'transport'/(identifier+'.json'),record)
        with guard():
            from urace.authenticated_journal import append_row
            append_row(BASE/'ledger.jsonl',record)
    return value,envelope,record
