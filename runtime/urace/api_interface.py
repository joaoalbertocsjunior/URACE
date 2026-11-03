"""Typed adapter over the installed CLI grammar, with explicit streaming transport."""
import argparse,contextlib,io,json,shlex
from contextvars import ContextVar
_DEPTH=ContextVar('urace_api_depth',default=0)
from .command_surface import child_parsers

class RequestError(ValueError):pass

def metadata_for_parser(p):
    args=[]
    for a in p._actions:
        if a.dest=='help' or isinstance(a,argparse._SubParsersAction):continue
        args.append({'name':a.dest,'flags':a.option_strings,'choices':list(a.choices) if a.choices else None,'required':a.required,'nargs':a.nargs,'type':getattr(a.type,'__name__','string') if a.type else 'string','action':type(a).__name__,'default':a.default if isinstance(a.default,(str,int,float,bool,list,dict,type(None))) else str(a.default)})
    return args

class BoundedCapture(io.StringIO):
    def __init__(self,allowance):super().__init__();self.allowance=allowance
    def write(self,text):
        self.allowance[0]-=len(text.encode('utf-8'))
        if self.allowance[0]<0:raise RequestError('API capture allowance exceeded')
        return super().write(text)

def metadata(parser):
    def visit(p,path):
        args=metadata_for_parser(p)
        return {'command':' '.join(path),'arguments':args,'children':[visit(c,[*path,n]) for n,c in child_parsers(p).items()]}
    from . import portfolio
    catalog=visit(parser,[])['children']
    for entry in catalog:
        if entry['command']=='portfolio':entry['children']=visit(portfolio.parser(),['portfolio'])['children']
    return {'schema_version':'1.0','transport':'CLI-equivalent typed params or exact argv; persistent operations require stream','commands':catalog}

def scalar(value):
    if isinstance(value,bool):return 'true' if value else 'false'
    if isinstance(value,(str,int,float)):return str(value)
    raise RequestError('argument values must be scalar, or arrays where the CLI supports repeated arguments')

def build_argv(parser,command=None,params=None,argv=None):
    if argv is not None:
        if command or params:raise RequestError('argv is mutually exclusive with command/params')
        if not isinstance(argv,list) or not argv or not all(isinstance(x,str) for x in argv):raise RequestError('argv must be a nonempty array of strings')
        result=list(argv);result[0]=result[0].removeprefix('/')
    else:
        if not isinstance(command,str) or not command.strip():raise RequestError('command must be a nonempty installed command path')
        try:tokens=shlex.split(command)
        except ValueError as error:raise RequestError(str(error)) from error
        tokens[0]=tokens[0].removeprefix('/')
        if not isinstance(params if params is not None else {},dict):raise RequestError('params must be an object')
        result=list(tokens);current=parser;index=0
        while child_parsers(current) and index<len(tokens) and tokens[index] in child_parsers(current):
            current=child_parsers(current)[tokens[index]];index+=1
        if current is parser:raise RequestError('unknown installed command: '+tokens[0])
        if tokens[0]=='portfolio':
            from . import portfolio
            current=portfolio.parser();index=1
            while child_parsers(current) and index<len(tokens) and tokens[index] in child_parsers(current):current=child_parsers(current)[tokens[index]];index+=1
        tail=tokens[index:]
        if any(x.startswith('-') for x in tail):raise RequestError('use params for flags, or argv for an exact CLI invocation')
        positional=[a for a in current._actions if not a.option_strings and not isinstance(a,argparse._SubParsersAction)]
        consumed=len(tail)
        if any(a.nargs in ('*','+') for a in positional[:consumed]):
            # Exact argv is unambiguous for unusual mixtures of variadic and named input.
            if params:raise RequestError('use argv to combine inline variadic arguments with params')
        remaining=positional[consumed:];options={}
        for a in current._actions:
            if a.option_strings:
                options.setdefault(a.dest,a)
                for flag in a.option_strings:options[flag.lstrip('-').replace('-','_')]=a
        values=dict(params or {})
        # Compatibility for old product selector params; canonical clients use leaf paths.
        if tokens[0]=='product' and index==len(tokens) and child_parsers(current):
            selector='action' if len(tokens)==1 else 'name' if tokens[-1] in ('work','value','improvements') else None
            if selector and selector in values:
                selected=values.pop(selector)
                if selected not in child_parsers(current):raise RequestError('Unknown product operation selector')
                result.append(selected);current=child_parsers(current)[selected];tokens.append(selected);index+=1
                if child_parsers(current) and 'name' in values:
                    selected=values.pop('name')
                    if selected not in child_parsers(current):raise RequestError('Unknown product operation')
                    result.append(selected);current=child_parsers(current)[selected];tokens.append(selected);index+=1
                positional=[a for a in current._actions if not a.option_strings and not isinstance(a,argparse._SubParsersAction)]
                remaining=positional;options={}
                for a in current._actions:
                    if a.option_strings:
                        options.setdefault(a.dest,a)
                        for flag in a.option_strings:options[flag.lstrip('-').replace('-','_')]=a

        for a in remaining:
            if a.dest not in values:continue
            value=values.pop(a.dest)
            if value is None:continue
            if isinstance(value,list):
                if a.nargs not in ('*','+'):raise RequestError(a.dest+' does not accept an array')
                result.extend(scalar(v) for v in value)
            else:result.append(scalar(value))
        for key,value in values.items():
            if not isinstance(key,str):raise RequestError('parameter names must be strings')
            action=options.get(key.replace('-','_'))
            if action is None:raise RequestError('unknown parameter: '+key)
            flag=next((f for f in action.option_strings if f.startswith('--')),action.option_strings[0])
            if isinstance(action,(argparse._StoreTrueAction,argparse._StoreFalseAction)):
                if not isinstance(value,bool):raise RequestError(key+' must be boolean')
                if value==action.const:result.append(flag)
                elif action.default!=value:raise RequestError(key+' cannot represent that boolean value')
            elif isinstance(action,argparse._StoreConstAction):
                if not isinstance(value,bool):raise RequestError(key+' must be boolean')
                if value:result.append(flag)
            elif value is None:continue
            elif isinstance(value,list):
                if isinstance(action,argparse._AppendAction):
                    for item in value:result.extend([flag,scalar(item)])
                elif action.nargs in ('*','+') or isinstance(action.nargs,int):result.extend([flag,*[scalar(item) for item in value]])
                else:raise RequestError(key+' does not accept an array')
            else:result.extend([flag,scalar(value)])
    # Never classify a typo or prose implicitly through the machine interface.
    root_index=0
    while root_index<len(result) and (result[root_index]=='--json' or result[root_index].startswith('--format')):
        root_index+=2 if result[root_index]=='--format' else 1
    if root_index>=len(result) or result[root_index].removeprefix('/') not in child_parsers(parser):raise RequestError('unknown installed command')
    result[root_index]=result[root_index].removeprefix('/')
    return result

def _infinite_cycles(value):
    text=str(value).strip().lower()
    if text in {'infinity','infinite','inf','forever'}:return True
    try:return int(text)==0
    except ValueError:return False

def persistent(argv):
    if '--help' in argv or '-h' in argv:return False
    if argv[:4]==['product','exchange','network','serve']:return True
    if argv[0] in {'auto','autonomous'} and '--dry-run' not in argv:
        for i,v in enumerate(argv):
            if v=='--cycles' and i+1<len(argv):return _infinite_cycles(argv[i+1])
            if v.startswith('--cycles='):return _infinite_cycles(v.split('=',1)[1])
        return True
    if argv[:2]==['api','watch']:return '--follow' in argv
    if argv[0]=='watch':return '--follow' in argv or '-f' in argv
    if argv[0]=='portfolio' and len(argv)>1 and argv[1] in {'auto','autonomous'}:
        for i,value in enumerate(argv):
            if value=='--cycles' and i+1<len(argv):return _infinite_cycles(argv[i+1])
            if value.startswith('--cycles='):return _infinite_cycles(value.split('=',1)[1])
        return True
    return False

class EventStream(io.TextIOBase):
    def __init__(self,target,stream):self.target=target;self.stream=stream;self.pending=''
    def write(self,text):
        self.pending+=text
        while '\n' in self.pending or len(self.pending)>16384:
            if '\n' in self.pending:line,self.pending=self.pending.split('\n',1)
            else:line,self.pending=self.pending[:16384],self.pending[16384:]
            self.target.write(json.dumps({'event':'output','stream':self.stream,'text':line})+'\n');self.target.flush()
        return len(text)
    def flush(self):
        if self.pending:self.target.write(json.dumps({'event':'output','stream':self.stream,'text':self.pending})+'\n');self.pending=''
        self.target.flush()

def execute(parser,runner,command=None,params=None,argv=None,stream=False,max_output_bytes=None):
    if _DEPTH.get()>=16:return {'schema_version':'1.0','status':'error','exit_code':2,'output':None,'error':'API nesting limit reached'}
    token=_DEPTH.set(_DEPTH.get()+1)
    try:return _execute(parser,runner,command,params,argv,stream,max_output_bytes)
    finally:_DEPTH.reset(token)

def _execute(parser,runner,command=None,params=None,argv=None,stream=False,max_output_bytes=None):
    request=command.lstrip("/") if isinstance(command,str) else argv
    try:
        args=build_argv(parser,command,params,argv)
        unprefixed=list(args)
        while unprefixed and unprefixed[0].startswith('--'):
            unprefixed=unprefixed[2:] if unprefixed[0]=='--format' else unprefixed[1:]
        if unprefixed[:2]==['api','serve']:raise RequestError('Launch api serve directly; MCP owns the stdio protocol')
        if persistent(unprefixed) and not stream:raise RequestError('persistent commands require --stream; alternatively set a finite --cycles value')
        # Prefer JSON only where this grammar advertises it. Portfolio has its own per-operation flags.
        current=parser;index=0
        while child_parsers(current) and index<len(args) and args[index] in child_parsers(current):current=child_parsers(current)[args[index]];index+=1
        accepts_json=any('--json' in a.option_strings for a in current._actions)
        if not any(x=='--json' or x=='--format' or x.startswith('--format=') for x in args):args.insert(0,'--json')
        if max_output_bytes is not None and (type(max_output_bytes) is not int or max_output_bytes<1):raise RequestError('Invalid API capture allowance')
        allowance=[max_output_bytes]
        out=BoundedCapture(allowance) if max_output_bytes is not None else io.StringIO();err=BoundedCapture(allowance) if max_output_bytes is not None else io.StringIO();events_out=EventStream(__import__('sys').stdout,'stdout') if stream else out;events_err=EventStream(__import__('sys').stdout,'stderr') if stream else err
        with contextlib.redirect_stdout(events_out),contextlib.redirect_stderr(events_err):
            try:rc=runner(args)
            except SystemExit as error:rc=error.code if isinstance(error.code,int) else 2
            except KeyboardInterrupt:rc=130
            except Exception as error:rc=2;print(type(error).__name__+': '+str(error),file=events_err)
        if stream:events_out.flush();events_err.flush();output=None;errors=''
        else:
            text=out.getvalue();errors=err.getvalue()
            try:output=json.loads(text) if text.strip() else None
            except ValueError:
                lines=text.splitlines()
                try:output=[json.loads(line) for line in lines if line.strip()]
                except ValueError:output=text
        return {'schema_version':'1.0','command':request,'status':'ok' if rc in (None,0) else 'error','exit_code':rc or 0,'output':output,'stderr':errors,'streamed':stream}
    except (RequestError,ValueError,IndexError) as error:
        return {'schema_version':'1.0','command':request,'status':'error','exit_code':2,'output':None,'error':str(error),'stderr':'','streamed':False}
