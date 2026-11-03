"""Immutable derivation artifacts and verifiable saved references."""
from __future__ import annotations
import copy,hashlib,json,os,re,stat
from pathlib import Path
from ._common import atomic_write_json,state_path
from .outcome_verification import _open_beneath

def content_hash(value):
    return hashlib.sha256(json.dumps({k:v for k,v in value.items() if k!='content_hash'},sort_keys=True,allow_nan=False).encode()).hexdigest()

def reference_hash(ref):
    return hashlib.sha256(json.dumps({k:v for k,v in ref.items() if k not in {'id','reference_sha256'}},sort_keys=True,allow_nan=False).encode()).hexdigest()

def seal(ref,artifact,config):
    artifact=copy.deepcopy(artifact);digest=content_hash(artifact);artifact['content_hash']=digest;relative='derived-artifacts/'+digest+'.json';root=state_path(config).parent;path=root/relative
    if path.exists():
        if path.is_symlink() or json.loads(path.read_text())!=artifact:raise ValueError('Existing immutable derivation artifact conflicts')
    else:atomic_write_json(path,artifact)
    result={**ref,'content_hash':digest,'artifact':relative};result['reference_sha256']=reference_hash(result);return result

def verify(ref,config):
    expected=ref.get('content_hash');result={'id':ref.get('manifest_id') or ref.get('construct_set_id'),'expected_hash':expected}
    if not expected:return {**result,'status':'UNVERIFIABLE','reason':'Legacy reference has no retained content hash'}
    if not isinstance(expected,str) or not re.fullmatch('[0-9a-f]{64}',expected):return {**result,'status':'MISMATCH','reason':'Invalid stored SHA-256'}
    relative=ref.get('artifact')
    if not relative:return {**result,'status':'UNVERIFIABLE','reason':'Legacy reference does not retain the original artifact; refresh to produce a verifiable reference'}
    if relative!='derived-artifacts/'+expected+'.json' or ref.get('reference_sha256')!=reference_hash(ref):return {**result,'status':'MISMATCH','reason':'Saved reference metadata changed'}
    try:
        with os.fdopen(_open_beneath(state_path(config).parent,Path(relative)),'rb') as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):raise ValueError('Regular artifact required')
            data=stream.read(2097153)
        if len(data)>2097152:raise ValueError('Artifact exceeds2MiB')
        artifact=json.loads(data)
        if not isinstance(artifact,dict):raise ValueError("Artifact must be a JSON object")
        actual=content_hash(artifact)
        if actual!=expected or artifact.get('content_hash')!=expected:raise ValueError('Artifact content changed')
        for field in ['manifest_id','construct_set_id','intent','spec_version','generated_at']:
            if field in ref and ref[field]!=artifact.get(field):raise ValueError('Reference and artifact disagree on '+field)
    except (OSError,ValueError,TypeError,KeyError) as error:return {**result,'status':'MISMATCH','reason':str(error)}
    return {**result,'status':'VERIFIED','computed_hash':actual,'artifact':relative}

def saved_refs(state):
    refs=[];seen=set()
    for row in state.get('derivation_refs',[])+state.get('derived_manifest_refs',[])+state.get('construct_set_refs',[]):
        key=row.get('manifest_id') or row.get('construct_set_id')
        if key not in seen:refs.append(row);seen.add(key)
    return refs
