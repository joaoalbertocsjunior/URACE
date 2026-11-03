"""Purpose-based CLI grammar, discoverability and shared input validation."""
import argparse,math

COMPATIBILITY = {'add-context','add-goal','add-source','add-metric','add-vital','declare','autonomous','self-evolution','policy','budget','executor-capacity','repair-controller','classify','compress','decompress','evaluation','check','vitals','quality','compliance','milestone','integrity-signal'}
PHANTOMS = {'activate','analytics','bootstrap','export','inspect','repair','schedule-task'}

def call_limit(value):
    if value == 'unlimited':return None
    try:return int(value)
    except ValueError:raise argparse.ArgumentTypeError('expected an integer or unlimited')

def boolean(value):
    if value.lower() not in {'true','false'}:
        raise argparse.ArgumentTypeError('expected true or false')
    return value.lower() == 'true'

def output_options(parser):
    parser.add_argument('--format', choices=['json','xml'], default=argparse.SUPPRESS)
    parser.add_argument('--json', action='store_const', const='json', dest='format', default=argparse.SUPPRESS, help=argparse.SUPPRESS)


def product(sub):
    root=sub.add_parser('product',help='manage products, isolated work, value evidence and improvement controls')
    root.set_defaults(command='product',name=None,improvement_product_id=None,all_products=False,product_state_path=None,product_files=[],intent_purpose=None,reason=None,force=False,value_id=None,value_data=None,project=None,template='navigation',work_executor='auto',execution_mode='auto',max_seconds=480,run_id=None,adaptive='true')
    output_options(root);children=root.add_subparsers(dest='action',required=True)
    for action in ('list','status','help','switch','register','remove','deactivate','activate','enable','disable'):
        p=children.add_parser(action,help=('compatibility alias for product improvements '+action if action in ('enable','disable') else action+' product'))
        output_options(p)
        if action not in ('list','status','help'):p.add_argument('name')
        if action=='register':
            p.add_argument('--state-path',dest='product_state_path',required=True);p.add_argument('--product-files',dest='product_files',nargs='+',default=[]);p.add_argument('--intent-purpose',dest='intent_purpose')
        if action in ('switch','register','remove','deactivate','activate'):p.add_argument('--reason')
        if action=='remove':p.add_argument('--force',action='store_true')
    create=children.add_parser('create',help='bootstrap a registered draft product directly from a description');create.add_argument('description');create.add_argument('--name',dest='creation_name');output_options(create)
    work=children.add_parser('work',help='isolated executable product work');output_options(work);verbs=work.add_subparsers(dest='name',required=True)
    for action in ('init','run','status','clarify'):
        p=verbs.add_parser(action,help=action+' isolated work');p.set_defaults(action='work',name=action);p.add_argument('--project',required=True);output_options(p)
        if action=='clarify':p.add_argument('--requirement-id',required=True);p.add_argument('--answer',required=True)
        if action=='init':p.add_argument('--template',choices=('navigation','failover','recovery','receipts','requirements_change','interruption'),default='navigation')
        if action=='run':
            p.add_argument('--executor',dest='work_executor',choices=('auto','codex','claude'),default='auto');p.add_argument('--execution-mode',choices=('auto','lightweight','managed'),default='auto');p.add_argument('--max-seconds',type=int,default=480);p.add_argument('--run-id');p.add_argument('--adaptive',choices=('true','false'),default='true')
    value=children.add_parser('value',help='project value evidence; observations do not grant authority');output_options(value);verbs=value.add_subparsers(dest='name',required=True)
    for action in ('propose','list','inspect','define','observe','evidence','validate','research','rank','experiment'):
        p=verbs.add_parser(action);p.set_defaults(action='value',name=action);output_options(p)
        if action not in ('propose','list','rank'):p.add_argument('--id',dest='value_id')
        if action in ('define','observe','evidence','experiment'):p.add_argument('--data',dest='value_data')
    improvements=children.add_parser('improvements',help='controls for products with an actual improvement worker');improvements.set_defaults(action='improvements',name='list');output_options(improvements);verbs=improvements.add_subparsers(dest='improvement_action')
    for action in ('list','enable','disable'):
        p=verbs.add_parser(action);p.set_defaults(action='improvements',name=action);output_options(p)
        if action=='list':p.add_argument('--all-products',action='store_true')
        else:p.add_argument('improvement_product_id')
    from .exchange_cli import grammar
    grammar(children)
    return root

def watch(sub):
    root=sub.add_parser('watch',help='observe runtime improvement cycles and deployment evidence')
    root.set_defaults(command='watch',watch_action='events',follow=False,limit=20,report=False,guard=False,dashboard=False)
    root.add_argument('--follow','-f',action='store_true');root.add_argument('--limit',type=int,default=20);output_options(root)
    old=root.add_mutually_exclusive_group()
    for name in ('report','guard','dashboard'):old.add_argument('--'+name,action='store_true',help='compatibility alias for watch '+name)
    children=root.add_subparsers(dest='watch_action')
    for name in ('events','dashboard','guard','report'):
        p=children.add_parser(name,help='runtime '+name+' view');p.set_defaults(watch_action=name);output_options(p)
        if name=='events':p.add_argument('--follow','-f',action='store_true',default=argparse.SUPPRESS);p.add_argument('--limit',type=int,default=argparse.SUPPRESS)
    root.set_defaults(watch_action='events')
    return root


def configuration(sub):
    root = sub.add_parser('configuration', help='inspect or change persistent settings', formatter_class=argparse.RawDescriptionHelpFormatter, description='Persistent settings. Examples: configuration effort high; configuration executor codex --model MODEL; configuration auto-goals replenish disable. Existing tasks and Authority remain separate.')
    root.set_defaults(setting='show',value=None,daily=None,monthly=None,component=None)
    output_options(root)
    children = root.add_subparsers(dest='configuration_setting', metavar='SETTING')
    descriptions = {'show':'show persistent settings','workflow':'select the core or isolated specification execution workflow','self-evolution':'set whether URACE can improve its implementation','change-explanations':'set automatic explanation policy','external-metrics':'set external observation policy','analytics-export':'set automatic analytics policy','executor-budget':'set executor call budgets','evaluation-minimum':'set minimum evidence units','evaluation-weight':'set an evaluator component weight'}
    for setting,description in descriptions.items():
        p=children.add_parser(setting,help=description);p.set_defaults(setting=setting)
        if setting != 'show':p.add_argument('value',nargs='?')
        if setting=='executor-budget':p.add_argument('--daily',type=int);p.add_argument('--monthly',type=int)
        if setting=='evaluation-weight':p.add_argument('--component')
        output_options(p)
    p=children.add_parser('value-discovery',help='project value suggestions and optional configured-source research');p.set_defaults(command='value-discovery-config')
    for name in ('enabled','external-research','ranking'):p.add_argument('--'+name,type=boolean)
    for name in ('freshness-seconds','research-seconds','research-sources'):p.add_argument('--'+name,type=int)
    output_options(p)
    p=children.add_parser('decision-feedback',help='local decision benefit forecasts; optional explicit executor assessments');p.set_defaults(command='decision-feedback-config')
    p.add_argument('--enabled',type=boolean);p.add_argument('--mode',choices=['auto','executor']);p.add_argument('--executor',choices=['auto','codex','claude']);p.add_argument('--cache-seconds',type=int);output_options(p)
    p=children.add_parser('executor-skills',help='default-auto task-relevant pinned instruction skills; no automatic host installation');p.set_defaults(command='executor-skills-config');p.add_argument('--enabled',type=boolean);p.add_argument('--mode',choices=['auto','off']);p.add_argument('--max-selected',type=int);p.add_argument('--max-instruction-bytes',type=int);p.add_argument('--catalog-file');output_options(p)
    p=children.add_parser('context-guard',help='source-bound requirement retrieval and owner clarification loop');p.set_defaults(command='context-guard-config');p.add_argument('--enabled',type=boolean);output_options(p)
    p=children.add_parser('runtime-improvement',help='bounded runtime cycle controls; independent acceptance remains required');p.set_defaults(command='runtime-improvement-config')
    p.add_argument('--enabled',type=boolean);p.add_argument('--auto-deploy',type=boolean);p.add_argument('--interval-seconds',type=int);output_options(p)
    p=children.add_parser('auto-milestones',help='local milestone drafts; never automatically activates gates');p.set_defaults(command='auto-milestones-config')
    p.add_argument('--enabled',type=boolean);output_options(p)
    p=children.add_parser('auto-goals',help='toggle automatic project goals and replenishment');p.set_defaults(command='auto-goals')
    p.add_argument('action',nargs='?',default='status',choices=['status','enable','disable','replenish'])
    p.add_argument('value',nargs='?',choices=['status','enable','disable']);output_options(p)
    p=children.add_parser('effort',help='URACE resource allocation; independent of native reasoning');p.set_defaults(command='effort')
    p.add_argument('mode',nargs='?',default='status',choices=['status','low','medium','high','inherit']);p.add_argument('--executor',dest='executor_id');output_options(p)
    p=children.add_parser('executor',help='persistent native model/reasoning overrides; use executor attach for registration');p.set_defaults(command='executor-options')
    p.add_argument('executor_id');g=p.add_mutually_exclusive_group();g.add_argument('--model');g.add_argument('--inherit-model',action='store_true')
    p.add_argument('--native-effort',choices=['low','medium','high','inherit']);output_options(p)
    return root

def child_parsers(parser):
    for action in parser._actions:
        if isinstance(action,argparse._SubParsersAction):return action.choices
    return {}

def help_parser(root,path):
    if not path:return root
    key=' '.join(path)
    catalog=operation_parsers(root)
    if key not in catalog:raise ValueError('unknown help path: '+key)
    return catalog[key]


def operation_parsers(parser):
    """Discover installed paths/actions from the same grammar; no shadow handlers."""
    found={}
    def visit(p,path):
        if path:found[' '.join(path)]=p
        children=child_parsers(p)
        if children:
            for name,child in children.items():visit(child,[*path,name])
        else:
            positions=[a for a in p._actions if not a.option_strings]
            if positions and positions[0].choices:
                for value in positions[0].choices:found[' '.join([*path,str(value)])]=p
    visit(parser,[])
    # Product work/value use the existing positional action grammar.
    product=child_parsers(parser).get('product')
    if product and not child_parsers(product):
        for action,verbs in [('work',['init','run','status']),('value',['propose','list','inspect','define','observe','evidence','validate','research','rank','experiment']),('improvements',['list','enable','disable'])]:
            for verb in verbs:found['product '+action+' '+verb]=product
    from . import portfolio
    visit(portfolio.parser(),['portfolio'])
    return found


def finalize(parser,root=True):
    if "--format" in parser._option_string_actions and "--json" not in parser._option_string_actions:
        parser.add_argument("--json",action="store_const",const="json",dest="format",default=argparse.SUPPRESS,help=argparse.SUPPRESS)
    # Parent output flags remain effective when a child supplies no format.
    for action in parser._actions:
        if action.dest=='format' and action.default is None:action.default=argparse.SUPPRESS
        if isinstance(action,argparse._SubParsersAction):
            visible=[k for k in action.choices if not root or k not in COMPATIBILITY]
            action.metavar='{'+','.join(visible)+'}'
            action._choices_actions=[a for a in action._choices_actions if not root or a.dest not in COMPATIBILITY]
            for child in action.choices.values():finalize(child,False)

def validate(args,raw,parser):
    for name in ('limit','offset','depth'):
        value=getattr(args,name,None)
        if value is not None and value<0:parser.error('--'+name+' must be nonnegative')
    interval=getattr(args,'interval',None)
    if interval is not None and (not math.isfinite(interval) or interval<0):parser.error('--interval must be finite and nonnegative')
    # Reject explicit controls that otherwise silently disappear in list/status paths.
    flags={s.split('=',1)[0] for s in raw if s.startswith('--')}
    if args.command=='product' and getattr(args,'improvement_product_id',None) is not None and args.action!='improvements':parser.error('Extra product positional argument requires product improvements')
    if args.command=='product' and getattr(args,'all_products',False) and args.action!='improvements':parser.error('--all-products requires product improvements list')
    if args.command=='product' and args.action!='work' and flags & {'--project','--template','--executor','--execution-mode','--max-seconds','--run-id','--adaptive'}:parser.error('project work options require product work')
    if args.command=='product' and flags & {'--id','--data'} and args.action!='value':parser.error('value evidence options require product value')
    rules={
        'decision':{'--forecast':{'assess'}},
        'goal':{'--priority':{'prioritize'},'--floor':{'prioritize'},'--ceiling':{'prioritize'},'--until':{'prioritize','defer'},'--deadline':{'schedule'},'--not-before':{'schedule'},'--clear-deadline':{'schedule'},'--clear-not-before':{'schedule'},'--estimate-min-hours':{'schedule'},'--estimate-max-hours':{'schedule'},'--estimate-confidence':{'schedule'},'--depends-on':{'schedule'},'--clear-dependencies':{'schedule'},'--decision':{'resolve-update'}},
        'executor':{**{k:{'attach'} for k in ('--command','--adapter','--priority','--capability','--capability-priority','--max-calls-24h','--max-calls-30d')},**{k:{'retry-policy'} for k in ('--retry-mode','--retry-delay-ms','--retry-fallback-seconds')}},
        'resource':{k:{'report'} for k in ('--since','--until','--limit','--offset')},
        'feedback':{'--signal':{'submit','list'},'--detail':{'submit'},'--evidence':{'submit'},'--input-json':{'submit'},'--target':{'list'},'--limit':{'list'},'--offset':{'list'}},
        'report':{'--output':{'export'},'--xlsx':{'export'}},
    }
    for flag,actions in rules.get(args.command,{}).items():
        if flag in flags and getattr(args,'action',None) not in actions:parser.error(flag+' is not applicable to '+args.command+' '+str(getattr(args,'action','')))
    if getattr(args,'clear_deadline',False) and getattr(args,'deadline',None):parser.error('--deadline conflicts with --clear-deadline')
    if getattr(args,'clear_not_before',False) and getattr(args,'not_before',None):parser.error('--not-before conflicts with --clear-not-before')
    if getattr(args,'clear_dependencies',False) and getattr(args,'depends_on',None):parser.error('--depends-on conflicts with --clear-dependencies')

def validate_budget(daily,monthly,parser):
    if (daily is not None and daily<2) or (monthly is not None and monthly<2) or (daily is not None and monthly is not None and monthly<daily):parser.error('budget requires daily >= 2 and monthly >= daily; both must be configured')

def validate_evaluation(config,action,component,value,parser):
    settings=config.get('evaluation_system',{})
    if value is None or not math.isfinite(value):parser.error('evaluation value must be finite')
    if action=='set-minimum':
        if value<1 or int(value)!=value:parser.error('evaluation minimum must be a positive integer')
        return int(value)
    weights=settings.get('weights',{})
    if component not in weights or not 0<=value<=1:parser.error('evaluation weight requires an existing component and value between 0 and 1')
    if value==0 and not any(v>0 for k,v in weights.items() if k!=component):parser.error('at least one evaluation weight must remain positive')
    return value

# These groups describe learning paths, not additional dispatch roots.
GROUPS={
 'Observe':{'status','watch'},
 'Lifecycle':{'init','auto','plan','pause','resume','onboard'},
 'Work and input':{'add','context','goal','source','metric','vital','feedback'},
 'Inspection and evidence':{'check','vitals','change','why','explain','decision','trace','evidence','quality','compliance','milestone','integrity-signal','resource'},
 'Persistent settings':{'configuration','evaluation'},
 'Execution and products':{'executor','product','fleet','portfolio','data','trial'},
 'Governance':{'rules','intent','constraint','blocker','govern'},
 'Maintenance and design':{'update','derive','compact','decompact','amend','crc'},
 'Help and integration':{'help','commands','schema','api','report'},
}
def catalog(parser):
    # Generated grammar supplements the stable effect contract instead of guessing effects.
    groups={k:[] for k in GROUPS}
    for name,p in child_parsers(parser).items():
        if name in COMPATIBILITY:continue
        group=next((k for k,names in GROUPS.items() if name in names),'Other')
        actions=[a for a in p._actions if not a.option_strings and a.choices and not isinstance(a,argparse._SubParsersAction)]
        nested=list(child_parsers(p))
        groups.setdefault(group,[]).append({'command':name,'actions':nested or (list(actions[0].choices) if actions else []),'usage':p.format_usage().strip(),'help':'urace help '+name})
    return groups


def status(sub):
    """Read-only subject views; no arbitrary downstream action forwarding."""
    import copy
    root=sub.add_parser('status',help='read-only operational views; defaults to runtime')
    output_options(root)
    children=root.add_subparsers(dest='status_subject',metavar='SUBJECT')
    specifications={
      'runtime':('check',None,{'--fail-on','--migration-dry-run'}),
      'improvements':('watch','dashboard',set()),
      'vitals':('vitals',None,{'--since','--until','--limit','--fail-on'}),
      'executors':('executor','status',set()),
      'resources':('resource','status',set()),
      'products':('product','list',set()),
      'fleet':('fleet','status',set()),
      'data':('data','status',set()),
      'quality':('quality',None,{'--scope'}),
      'compliance':('compliance',None,{'--domain','--history'}),
      'milestones':('milestone',None,{'--scope'}),
      'blockers':('blocker','list',{'--resolved','--scope'}),
      'integrity':('integrity-signal','list',{'--type','--severity','--resolved'}),
      'onboarding':('onboard','status',set()),
      'configuration':('configuration',None,set()),
      'inbox':('inbox','list',{'--kind','--status','--limit'}),
      'goals':('goal','list',{'--status','--limit'}),
      'evaluation':('evaluation','show',set()),
    }
    def install(target,source_name,action,allowed):
        source=sub.choices[source_name]
        defaults={a.dest:a.default for a in source._actions if not isinstance(a,argparse._SubParsersAction) and a.dest!='help' and a.default is not argparse.SUPPRESS}
        defaults.update(source._defaults)
        defaults['command']=source_name
        if action is not None:defaults['watch_action' if source_name=='watch' else 'action']=action
        if source_name=='data':defaults['data_action']='status'
        target.set_defaults(**defaults)
        for a in source._actions:
            if a.option_strings and set(a.option_strings)&allowed:
                cloned=copy.copy(a);cloned.option_strings=list(a.option_strings);target._add_action(cloned)
        output_options(target)
    for subject,(source,action,options) in specifications.items():
        p=children.add_parser(subject,help='read-only '+subject+' view')
        install(p,source,action,options)
        if subject == 'resources':
            select=p.add_mutually_exclusive_group()
            select.add_argument('--product');select.add_argument('--all-products',action='store_true')
            p.add_argument('--executor',choices=['codex','claude','all'])
            p.add_argument('--scope',choices=['trial','epoch','lifetime'])
    v=children.add_parser('value',help='project value evidence, unknowns and research status');v.set_defaults(command='value-status');output_options(v)
    from .trial_cli import score_arguments
    scores=children.add_parser('scores',help='executable workflow scores and version deltas')
    score_arguments(scores);scores.set_defaults(command='check')
    # No subject means runtime; install defaults without adding output options twice.
    check=sub.choices['check']
    root.set_defaults(command='check',fail_on=None,migration_dry_run=False)
    return root

def match_quoted_command(parser,text):
    """Match complete quoted command syntax, never infer from a partial prefix."""
    import contextlib,io,shlex
    try:tokens=shlex.split(text)
    except ValueError:return None
    if not tokens:return None
    tokens[0]=tokens[0].removeprefix('/')
    if tokens[0] not in child_parsers(parser) or tokens[0]=='classify':return None
    with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
        try:parser.parse_args(tokens)
        except SystemExit as e:
            if e.code:return None
    return tokens

def forward(command,cwd):
    """Forward subprocess output through Python streams, including API capture."""
    import subprocess,sys,threading
    child=subprocess.Popen(command,cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,bufsize=1)
    def copy(source,sink):
        try:
            for line in source:sink.write(line);sink.flush()
        finally:source.close()
    threads=[threading.Thread(target=copy,args=(child.stdout,sys.stdout),daemon=True),threading.Thread(target=copy,args=(child.stderr,sys.stderr),daemon=True)]
    for t in threads:t.start()
    try:return child.wait()
    except KeyboardInterrupt:
        child.terminate()
        try:child.wait(timeout=5)
        except subprocess.TimeoutExpired:child.kill();child.wait()
        return 130
    finally:
        for t in threads:t.join(timeout=5)

def read_only(argv):
    command=argv[0];action=argv[1] if len(argv)>1 else ''
    if command=='watch':return True
    if argv[:2]==['product','exchange']:
        return argv[2:3] in (['status'],['audit'],['rank']) or argv[2:4] in (['bundle','inspect'],['settings','show'],['peer','list'],['feature','catalog'])
    if argv[:2]==['product','improvements']:return len(argv)==2 or argv[2] in ('list','--json','--all-products')
    if argv[:2]==['product','value']:return len(argv)>2 and argv[2] in {'list','inspect','rank'}
    if argv[:2]==['configuration','executor-skills']:return not any(x.split('=')[0] in {'--enabled','--mode','--max-selected','--max-instruction-bytes','--catalog-file'} for x in argv[2:])
    if argv[:2]==['configuration','context-guard']:return not any(x.split('=')[0]=='--enabled' for x in argv[2:])
    if argv[:2]==['configuration','runtime-improvement']:return not any(x.split('=')[0] in {'--enabled','--auto-deploy','--interval-seconds'} for x in argv[2:])
    if argv[:2]==['configuration','auto-milestones']:return not any(x.split('=')[0]=='--enabled' for x in argv[2:])
    if argv[:2]==['configuration','decision-feedback']:return not any(x.split('=')[0] in {'--enabled','--mode','--executor','--cache-seconds'} for x in argv[2:])
    if argv[:2]==['configuration','value-discovery']:return not any(x.split('=')[0] in {'--enabled','--external-research','--ranking','--freshness-seconds','--research-seconds','--research-sources'} for x in argv[2:])
    if argv[:3]==['product','work','status'] or argv[:4]==['trial','study','benefit','status']:return True
    if command=='trial':
        if action=='status' or argv[:3]==['trial','study','status']:return True
        if argv[:3]==['trial','config','efficiency']:
            return not any(a in {'--file','--disable'} or a.startswith('--file=') for a in argv[3:])
        return argv[:4]==['trial','data','metrics','show']
    if command in {'status','help','commands','check','vitals','quality','compliance','milestone','integrity-signal','why','explain'}:return True
    if command=='configuration':
        if not action or action=='show':return True
        if action in {'effort','auto-goals'}:return len(argv)<=2 or (len(argv)>2 and argv[2]=='status')
        if action=='executor':return not any(x in argv for x in ('--model','--native-effort','--inherit-model'))
        return len(argv)<=2 or (len(argv)>2 and argv[2]=='status')
    actions={'goal':{'list','inspect','forecast'},'context':{'list','graph','attention'},'source':{'list'},'metric':{'list'},'vital':{'list'},'executor':{'status'},'product':{'list','status'},'fleet':{'status'},'onboard':{'status'},'data':{'list','inspect','status'},'trace':{'list','inspect'},'decision':{'list','inspect'},'evidence':{'list'},'rules':{'list','inspect','graph','conflicts','changes'},'inbox':{'list','status'},'report':{'status'},'resource':{'status','report'},'schema':{'list','inspect'},'api':{'help','commands','version','protocols'},'portfolio':{'status','feedback','explain','rank','agora-show','commands','policy-status','accepted-state-source-status'}}
    return action in actions.get(command,set())
