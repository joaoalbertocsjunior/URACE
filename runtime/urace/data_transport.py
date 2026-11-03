"""Bounded, real local JSON/CSV/SQLite I/O; unsupported transports stay explicit."""
from pathlib import Path
import csv,hashlib,io,json,os,re,shutil,sqlite3,tempfile,uuid
from urllib.parse import quote
SUPPORTED={'json','json_file','csv','sqlite','sqlite3'}
class TransportError(ValueError):pass

def input_rows(raw,config,stdin):
    """Bound push input before decoding; never load an arbitrarily large file."""
    if not raw:return None
    limit=int(config.get('data_limits',{}).get('max_bytes',5242880))
    if limit<1:raise TransportError('invalid data byte limit')
    if raw=='-':
        stream=getattr(stdin,'buffer',stdin);data=stream.read(limit+1)
    else:
        with Path(raw).open('rb') as stream:data=stream.read(limit+1)
    if isinstance(data,str):data=data.encode('utf-8')
    if len(data)>limit:raise TransportError('data byte limit exceeded')
    return json.loads(data.decode('utf-8-sig'))

def path_of(record):
    raw=record.get('connection_metadata',{}).get('dsn','')
    if not isinstance(raw,str) or not raw or '://' in raw:raise TransportError('ADAPTER_REQUIRED')
    path=Path(raw).expanduser()
    if path.is_symlink():raise TransportError('symlink data targets require an explicit resolved path')
    return path.resolve()

def validate_rows(rows,config):
    limit=int(config.get('data_limits',{}).get('max_rows',10000))
    if isinstance(rows,dict):rows=[rows]
    if not isinstance(rows,list) or any(not isinstance(r,dict) or any(not isinstance(k,str) for k in r) for r in rows):raise TransportError('data must be an object or an array of objects')
    if len(rows)>limit:raise TransportError('data row limit exceeded')
    data=json.dumps(rows,sort_keys=True,allow_nan=False).encode()
    if len(data)>int(config.get('data_limits',{}).get('max_bytes',5242880)):raise TransportError('data byte limit exceeded')
    return rows,data

def table(record):
    name=record.get('schema_hint')
    if not isinstance(name,str) or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',name):raise TransportError('SQLite requires a simple table name in --schema')
    return name

def read(record,config):
    if record.get('adapter_kind') not in SUPPORTED:raise TransportError('ADAPTER_REQUIRED')
    path=path_of(record);kind=record['adapter_kind']
    if kind in {'sqlite','sqlite3'}:
        with sqlite3.connect('file:'+quote(str(path))+'?mode=ro',uri=True,timeout=2) as db:
            limit=int(config.get('data_limits',{}).get('max_bytes',5242880))
            # Bound a single native SQLite value before Python materializes it,
            # then stop aggregate row transfer as soon as the JSON budget is spent.
            db.setlimit(sqlite3.SQLITE_LIMIT_LENGTH,max(4096,limit))
            db.row_factory=sqlite3.Row;rows=[];used=2
            for value in db.execute('SELECT * FROM "'+table(record)+'" LIMIT ?', (int(config.get('data_limits',{}).get('max_rows',10000))+1,)):
                row=dict(value)
                try:encoded=json.dumps(row,sort_keys=True,allow_nan=False).encode()
                except (TypeError,ValueError) as error:raise TransportError('SQLite rows must contain JSON-compatible values') from error
                used+=len(encoded)+(2 if rows else 0)
                if used>limit:raise TransportError('data byte limit exceeded')
                rows.append(row)
    else:
        with path.open('rb') as stream:raw=stream.read(int(config.get('data_limits',{}).get('max_bytes',5242880))+1)
        if len(raw)>int(config.get('data_limits',{}).get('max_bytes',5242880)):raise TransportError('data byte limit exceeded')
        text=raw.decode('utf-8-sig')
        if kind in {'json','json_file'}:rows=json.loads(text)
        else:
            reader=csv.DictReader(io.StringIO(text))
            if not reader.fieldnames or len(set(reader.fieldnames))!=len(reader.fieldnames):raise TransportError('CSV requires unique column names')
            rows=list(reader)
            if any(None in row or any(v is None for v in row.values()) for row in rows):raise TransportError('CSV row width does not match headers')
    return validate_rows(rows,config)

def verify(record):
    if record.get('adapter_kind') not in SUPPORTED:raise TransportError('ADAPTER_REQUIRED')
    path=path_of(record)
    if not path.is_file():raise TransportError('local data source does not exist')
    with path.open('rb') as stream:stream.read(0)
    if record['adapter_kind'] in {'sqlite','sqlite3'}:
        with sqlite3.connect('file:'+quote(str(path))+'?mode=ro',uri=True,timeout=2) as db:
            exists=db.execute('SELECT name FROM sqlite_master WHERE type="table" AND name=?',(table(record),)).fetchone()
            if exists is None:raise TransportError('SQLite table does not exist')
    return {'transport':'local','connectivity_verified':True,'rows_transferred':0}

def atomic_file(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():
        if path.read_bytes()==data:return None
        backup=path.with_name(path.name+'.urace-backup-'+uuid.uuid4().hex)
        shutil.copy2(path,backup)
    else:backup=None
    with tempfile.NamedTemporaryFile('wb',dir=path.parent,delete=False) as stream:
        stream.write(data);stream.flush();os.fsync(stream.fileno());name=stream.name
    os.replace(name,path)
    return str(backup) if backup else None

def push(record,rows,config):
    rows,data=validate_rows(rows,config);path=path_of(record);kind=record['adapter_kind']
    if kind not in SUPPORTED:raise TransportError('ADAPTER_REQUIRED')
    if kind in {'sqlite','sqlite3'}:
        if not path.is_file():raise TransportError('SQLite target must exist; push appends transactionally')
        columns=list(rows[0]) if rows else []
        if any(set(r)!=set(columns) for r in rows) or any(not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',c) for c in columns):raise TransportError('SQLite push requires consistent simple column names')
        with sqlite3.connect('file:'+quote(str(path))+'?mode=rw',uri=True,timeout=2) as db:
            if rows:db.executemany('INSERT INTO "'+table(record)+'" ('+','.join('"'+c+'"' for c in columns)+') VALUES ('+','.join('?' for _ in columns)+')',[[r[c] for c in columns] for r in rows])
        backup=None
    elif kind=='csv':
        columns=list(rows[0]) if rows else []
        if any(set(r)!=set(columns) for r in rows):raise TransportError('CSV requires a consistent row schema')
        stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=columns);writer.writeheader();writer.writerows(rows);backup=atomic_file(path,stream.getvalue().encode())
    else:backup=atomic_file(path,data+b'\n')
    return {'rows_affected':len(rows),'records_written':[str(path)],'backup':backup,'content_sha256':hashlib.sha256(data).hexdigest()}

def perform(action,record,state,config,state_directory,input_rows=None):
    before_sync=record.get('last_sync_cycle');before_push=record.get('last_push_cycle')
    identifier='dsync-'+uuid.uuid4().hex
    try:
        if action=='verify':result=verify(record)
        elif action=='sync':
            rows,data=read(record,config);snapshot=Path(state_directory)/'data-snapshots'/(hashlib.sha256(data).hexdigest()+'.json')
            if not snapshot.exists():
                used=sum(p.stat().st_size for p in snapshot.parent.glob('*.json')) if snapshot.parent.exists() else 0
                if used+len(data)>int(config.get('data_limits',{}).get('max_snapshot_storage_bytes',104857600)):raise TransportError('snapshot storage budget exceeded; historical snapshots preserved')
                atomic_file(snapshot,data+b'\n')
            evidence_id='evidence-'+uuid.uuid4().hex
            state.setdefault('evidence',[]).append({'id':evidence_id,'kind':'data-source-observed','at':__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),'source_id':record['id'],'rows':len(rows),'snapshot':str(snapshot),'content_sha256':hashlib.sha256(data).hexdigest()})
            record['snapshot_path']=str(snapshot)
            result={'rows_affected':len(rows),'records_written':[str(snapshot)],'evidence_ids_produced':[evidence_id],'content_sha256':hashlib.sha256(data).hexdigest()};record['last_sync_cycle']=state.get('cycle',0)
        else:
            if input_rows is None:raise TransportError('data push requires --input-json with explicit records')
            result=push(record,input_rows,config);record['last_push_cycle']=state.get('cycle',0)
        record.update(status='CONNECTED',adapter_status='IMPLEMENTED')
        if action!='verify':state.setdefault('data_sync_records',[]).append({'id':identifier,'data_source_id':record['id'],'cycle':state.get('cycle',0),'direction':'PULL' if action=='sync' else 'PUSH','status':'SUCCESS','evidence_ids_produced':[],**result})
        return 0,{'action':'data-'+action,'status':'CONNECTED',**result}
    except (OSError,ValueError,UnicodeError,sqlite3.Error) as error:
        record['status']='DISCONNECTED';record['last_sync_cycle']=before_sync;record['last_push_cycle']=before_push
        reason='ADAPTER_REQUIRED' if str(error)=='ADAPTER_REQUIRED' else 'TRANSPORT_FAILED'
        record['adapter_status']=reason
        # Native exception details can contain credential-bearing connection strings.
        if action!='verify':state.setdefault('data_sync_records',[]).append({'id':identifier,'data_source_id':record['id'],'cycle':state.get('cycle',0),'direction':'PULL' if action=='sync' else 'PUSH','status':'FAILED','rows_affected':0,'records_written':[],'evidence_ids_produced':[],'error_msg':reason})
        return 1,{'action':'data-'+action,'status':'DISCONNECTED','error':reason,'reason':str(error) if isinstance(error,TransportError) else type(error).__name__}

def public_record(value):
    if isinstance(value,list):return [public_record(v) for v in value]
    if isinstance(value,dict):return {k:('<redacted remote connection>' if k=='dsn' and isinstance(v,str) and '://' in v else public_record(v)) for k,v in value.items()}
    return value

def auto_sync(state,config,state_directory):
    import time
    now=time.time();results=[]
    for rec in state.get('data_source_records',[]):
        if not rec.get('auto',True) or rec.get('direction')=='WRITE' or rec.get('adapter_kind') not in SUPPORTED:continue
        if now-rec.get('auto_checked_unix',0)<float(config.get('data_limits',{}).get('auto_poll_seconds',60)):continue
        rec['auto_checked_unix']=now
        try:
            stat=path_of(rec).stat();fingerprint=[stat.st_mtime_ns,stat.st_size,rec.get('schema_hint')]
        except (OSError,ValueError):fingerprint=['unavailable',rec.get('connection_metadata',{}).get('dsn')]
        if rec.get('status')=='CONNECTED' and rec.get('auto_observed_fingerprint')==fingerprint:continue
        code,result=perform('sync',rec,state,config,state_directory)
        if code==0:rec['auto_observed_fingerprint']=fingerprint
        results.append(result)
    return results
