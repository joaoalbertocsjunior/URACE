"""Canonical declared feature atoms and immutable lineage; no semantic-minimality claim.

The signed block stream is authoritative; its JSON index is only a validated cache.
Payload bytes stay in the private artifact store, never in this catalogue ledger.

Rules versioning: RULES_V1 is the original schema. RULES_V2 adds SET_QUALITY_PROVEN.
Both are accepted on read so existing ledgers keep working.
New events use RULES_ID (v2).

Propagation-based rewards:
  feature_score() — propagation_score = distinct_borrowers × mean_outcome_delta
  borrow()        — emits FEATURE_BORROWED in the exchange audit log; credits creator
  Token earn from FEATURE_BORROWED is read by token_ledger.balance() via creator_peer_id.
  With token_settlement=True, only receipt_verified=True borrows credit the creator —
  a gibberish feature cannot pass a real trial and therefore cannot earn borrow credits.
"""
import hashlib,json,re,time
from pathlib import Path
from .ledger_crypto import canonical
from .signed_ledger import Ledger

MIN_PROPAGATION_SCORE = 2.0  # distinct_borrowers * mean_outcome_delta threshold
_BORROW_CREDIT_PER_PEER = 1.0  # tokens earned by creator per unique borrower

RULES_V1={"schema":"urace-feature-catalog-rules-v1","operations":["DECLARE_ATOM","SET_LIFECYCLE"],"content":"sha384-reference-only","credit_from_declaration":False,"ownership_from_declaration":False}
RULES_V2={"schema":"urace-feature-catalog-rules-v1","operations":["DECLARE_ATOM","SET_LIFECYCLE","SET_QUALITY_PROVEN"],"content":"sha384-reference-only","credit_from_declaration":False,"ownership_from_declaration":False}
RULES_V1_ID=hashlib.sha384(canonical(RULES_V1)).hexdigest()
RULES_V2_ID=hashlib.sha384(canonical(RULES_V2)).hexdigest()
RULES_ID=RULES_V2_ID  # current; written into new events
RULES=RULES_V2        # kept for back-compat with code that references RULES directly
HEX=re.compile(r"^[a-f0-9]{96}$")

def descriptor(value):
 if not isinstance(value,dict) or set(value)!={"capability","interface_sha384","acceptance_sha384","content_sha384","dependencies","publisher_id","license_id"}:raise ValueError("Exact feature atom contract required")
 if not isinstance(value["capability"],str) or not 1<=len(value["capability"].encode())<=2048:raise ValueError("One bounded observable capability required")
 for key in ("interface_sha384","acceptance_sha384","content_sha384"):
  if not isinstance(value[key],str) or not HEX.fullmatch(value[key]):raise ValueError("Frozen interface, acceptance and content references required")
 for key in ("publisher_id","license_id"):
  if not isinstance(value[key],str) or not 1<=len(value[key])<=160 or any(ord(c)<32 for c in value[key]):raise ValueError("Publisher and explicit license reference required")
 deps=value["dependencies"]
 if not isinstance(deps,list) or len(deps)>32 or len(deps)!=len(set(deps)) or any(not isinstance(k,str) or not HEX.fullmatch(k) for k in deps):raise ValueError("Distinct bounded canonical dependencies required")
 return {**value,"dependencies":sorted(deps)}

def atom_id(value):return hashlib.sha384(canonical(descriptor(value))).hexdigest()

class Catalog:
 def __init__(self,root):self.root=Path(root);self.ledger=Ledger(self.root/"blocks")
 def _apply(self,state,event):
  if not isinstance(event,dict) or event.get("rules_sha384") not in (RULES_V1_ID,RULES_V2_ID):raise ValueError("Unaccepted catalogue rules")
  kind=event.get("operation")
  if kind=="SET_QUALITY_PROVEN":
   if event.get("rules_sha384")!=RULES_V2_ID:raise ValueError("SET_QUALITY_PROVEN requires rules v2")
   if set(event)!={"rules_sha384","operation","atom","qualification_evidence"}:raise ValueError("Unexpected quality proof fields")
   atom=event["atom"]
   if atom not in state["atoms"]:raise ValueError("Unknown atom in quality proof")
   ev=event["qualification_evidence"]
   if not isinstance(ev,dict):raise ValueError("Qualification evidence dict required")
   if not isinstance(ev.get("peer_count"),int) or ev["peer_count"]<2:raise ValueError("Quality proof requires at least 2 independent peer confirmations")
   state["atoms"][atom].update(quality_proven=True,reward_eligible=True,qualification_evidence=ev)
   return state
  if kind=="DECLARE_ATOM":
   if set(event)!={"rules_sha384","operation","alias","atom","descriptor"}:raise ValueError("Unexpected declaration fields")
   value=descriptor(event["descriptor"]);key=atom_id(value);alias=event["alias"]
   if not isinstance(alias,str) or not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,95}",alias) or key!=event["atom"]:raise ValueError("Invalid canonical declaration")
   if any(dep not in state["atoms"] for dep in value["dependencies"]):raise ValueError("Dependencies must already exist; forward cycles denied")
   if alias in state["aliases"] and state["aliases"][alias]!=key:raise ValueError("Alias already names an immutable version; use a distinct version alias")
   if key in state["atoms"] and state["atoms"][key]["descriptor"]!=value:raise ValueError("Conflicting canonical atom")
   state["atoms"].setdefault(key,{"descriptor":value,"lifecycle":"active","granularity":"DECLARED_ATOMIC_REQUIRES_INDEPENDENT_REVIEW","quality_proven":False,"reward_eligible":False,"rights_proven":False})
   state["aliases"][alias]=key
   state["contents"].setdefault(value["content_sha384"],[])
   if key not in state["contents"][value["content_sha384"]]:state["contents"][value["content_sha384"]].append(key)
  elif kind=="SET_LIFECYCLE":
   if set(event)!={"rules_sha384","operation","atom","status","replacement"} or event["atom"] not in state["atoms"] or event["status"] not in ("active","deprecated","obsolete"):raise ValueError("Invalid lifecycle change")
   replacement=event["replacement"]
   if replacement is not None and (replacement not in state["atoms"] or replacement==event["atom"]):raise ValueError("Existing distinct replacement required")
   state["atoms"][event["atom"]].update(lifecycle=event["status"],replacement=replacement)
  else:raise ValueError("No catalogue maintainer override or unsupported operation")
  return state
 def state(self):
  state={"schema":"urace-feature-catalog-v1","rules_sha384":RULES_ID,"atoms":{},"aliases":{},"contents":{},"native_inference_calls":0,"globally_minimal_features_proven":False,"semantic_deduplication_proven":False,"global_monopoly_prevention_proven":False}
  if not self.ledger.root.exists():return state
  # Complete verification is intentional here: this is an explicit catalogue operation,
  # not an idle-controller poll. Large-catalogue incremental indexes need separate qualification.
  report=self.ledger.verify();offset=0
  while offset<report["blocks"]:
   page=self.ledger.page(offset,100)
   for row in page["rows"]:
    if row["payload"]["kind"]!="FEATURE_CATALOG_EVENT":raise ValueError("Unexpected ledger event in catalogue")
    self._apply(state,row["payload"]["details"])
   offset+=len(page["rows"])
  state["head"]=report["head"];return state
 def declare(self,alias,value):
  value=descriptor(value);key=atom_id(value)
  # Serialize the read/check/append transaction independently of ledger's inner lock.
  from ._common import state_lock
  self.root.mkdir(parents=True,exist_ok=True,mode=0o700)
  with state_lock(self.root/"catalog-transaction"):
   state=self.state()
   if state["aliases"].get(alias)==key:return {"status":"ALREADY_DECLARED","atom_id":key,"new_reward_units":0}
   event={"rules_sha384":RULES_ID,"operation":"DECLARE_ATOM","alias":alias,"atom":key,"descriptor":value};self._apply(state,event)
   self.ledger.append("FEATURE_CATALOG_EVENT",event)
   return {"status":"DECLARED","atom_id":key,"canonical_content_id":value["content_sha384"],"content_stored_on_ledger":False,"new_reward_units":0,"granularity":"DECLARED_ATOMIC_REQUIRES_INDEPENDENT_REVIEW","ownership_proven":False}
 def lifecycle(self,key,status,replacement=None):
  from ._common import state_lock
  with state_lock(self.root/"catalog-transaction"):
   state=self.state();event={"rules_sha384":RULES_ID,"operation":"SET_LIFECYCLE","atom":key,"status":status,"replacement":replacement};self._apply(state,event);self.ledger.append("FEATURE_CATALOG_EVENT",event)
   return {"atom_id":key,"status":status,"replacement":replacement,"history_retained":True}
 def qualify(self,atom_key_or_alias,evidence,exchange=None):
  """Promote an atom to reward_eligible based on multi-peer qualification evidence.

  evidence: {canonical_fingerprint, outcome_fingerprint[, peer_count]}
  peer_count >= 2 required — independent confirmation is the proof of quality.

  When exchange is provided, peer_count is derived from distinct peers in the
  APPLIED_AFTER_LOCAL_QUALIFICATION audit rows matching the canonical_fingerprint.
  Caller-supplied peer_count is ignored — audit-derived count cannot be faked.
  When exchange is None, peer_count must be supplied in evidence (legacy/test path).

  Appends a SET_QUALITY_PROVEN event to the signed ledger.
  """
  if not isinstance(evidence,dict):raise ValueError("Evidence dict required")
  canon_fp=str(evidence.get("canonical_fingerprint",""))[:64]
  if exchange is not None:
   rows=exchange.audit_rows()
   qualified_peers={r.get("peer") for r in rows if r.get("kind")=="APPLIED_AFTER_LOCAL_QUALIFICATION" and r.get("canonical_fingerprint")==canon_fp and r.get("peer")}
   peer_count=len(qualified_peers)
  else:
   peer_count=evidence.get("peer_count")
  if not isinstance(peer_count,int) or peer_count<2:raise ValueError("Quality proof requires at least 2 independent peer confirmations (peer_count >= 2)")
  from ._common import state_lock
  with state_lock(self.root/"catalog-transaction"):
   state=self.state()
   atom=state["aliases"].get(atom_key_or_alias,atom_key_or_alias)
   if atom not in state["atoms"]:raise ValueError(f"Unknown atom: {atom_key_or_alias!r}")
   if state["atoms"][atom].get("quality_proven"):return {"atom_id":atom,"status":"ALREADY_QUALIFIED","reward_eligible":True}
   ev={"peer_count":peer_count,"canonical_fingerprint":canon_fp,"outcome_fingerprint":str(evidence.get("outcome_fingerprint",""))[:64],"at_unix":float(evidence.get("at_unix",time.time()))}
   event={"rules_sha384":RULES_V2_ID,"operation":"SET_QUALITY_PROVEN","atom":atom,"qualification_evidence":ev}
   self._apply(state,event);self.ledger.append("FEATURE_CATALOG_EVENT",event)
   return {"atom_id":atom,"status":"QUALIFIED","reward_eligible":True,"peer_count":peer_count}
 def feature_score(self,atom_key_or_alias,exchange,canonical_fp:str|None=None):
  """Propagation-weighted quality score: distinct_borrowers * mean_outcome_delta.

  Scans APPLIED_AFTER_LOCAL_QUALIFICATION audit rows matching canonical_fp.
  Each distinct peer who applied the artifact = one unique borrower.

  canonical_fp: SHA256/384 hex of the artifact's canonical source delta.
                When None, aggregates ALL APPLIED events (coarse — use for exploration only).

  Returns reward_threshold_met=True when distinct_borrowers >= 2 and
  propagation_score >= MIN_PROPAGATION_SCORE.
  """
  state=self.state()
  atom=state["aliases"].get(atom_key_or_alias,atom_key_or_alias)
  if atom not in state["atoms"]:raise ValueError(f"Unknown atom: {atom_key_or_alias!r}")
  rows=exchange.audit_rows()
  matching=[r for r in rows if r.get("kind")=="APPLIED_AFTER_LOCAL_QUALIFICATION" and (canonical_fp is None or r.get("canonical_fingerprint")==canonical_fp)]
  distinct_borrowers={r.get("peer") for r in matching if r.get("peer")}
  deltas=[float(r.get("score_delta",0.0)) for r in matching if r.get("score_delta") is not None]
  mean_delta=sum(deltas)/len(deltas) if deltas else 0.0
  propagation_score=round(len(distinct_borrowers)*mean_delta,4)
  return {"atom":atom,"canonical_fingerprint":canonical_fp,"distinct_borrowers":len(distinct_borrowers),"mean_outcome_delta":round(mean_delta,4),"propagation_score":propagation_score,"reward_threshold_met":len(distinct_borrowers)>=2 and propagation_score>=MIN_PROPAGATION_SCORE,"min_propagation_score":MIN_PROPAGATION_SCORE}
 def borrow(self,atom_key_or_alias,exchange,canonical_fp:str,outcome_delta:float=0.0,receipt_verified:bool=False):
  """Record that this node is adopting a peer's feature artifact.

  Emits FEATURE_BORROWED in the exchange audit log.
  The creator_peer_id is inferred from APPLIED_AFTER_LOCAL_QUALIFICATION rows
  whose canonical_fingerprint matches — the peer who sent the qualifying artifact.
  When multiple senders match (relay chains), the earliest APPLIED event wins.

  outcome_delta: improvement delta observed after adopting this feature.
  receipt_verified: True only when backed by a signed trial receipt
                    (required for creator token earn when token_settlement=True).

  The FEATURE_BORROWED event IS the borrow record — token_ledger.balance() reads
  it directly from the tamper-evident audit chain to credit the creator.
  """
  import re as _re
  if not isinstance(canonical_fp,str) or not _re.fullmatch(r"[a-f0-9]{64}",canonical_fp):raise ValueError("canonical_fp must be a 64-char hex SHA256")
  state=self.state()
  atom=state["aliases"].get(atom_key_or_alias,atom_key_or_alias)
  if atom not in state["atoms"]:raise ValueError(f"Unknown atom: {atom_key_or_alias!r}")
  rows=exchange.audit_rows()
  applied=[r for r in rows if r.get("kind")=="APPLIED_AFTER_LOCAL_QUALIFICATION" and r.get("canonical_fingerprint")==canonical_fp and r.get("peer")]
  creator_peer_id=applied[0]["peer"] if applied else "unknown"
  borrower_peer_id=exchange.identity()["peer_id"]
  with exchange.lock():
   exchange.event("FEATURE_BORROWED",atom=atom,canonical_fingerprint=canonical_fp,creator_peer_id=creator_peer_id,borrower_peer_id=borrower_peer_id,outcome_delta=round(float(outcome_delta),4),receipt_verified=bool(receipt_verified))
  return {"status":"BORROWED","atom":atom,"creator_peer_id":creator_peer_id,"borrower_peer_id":borrower_peer_id,"outcome_delta":outcome_delta,"receipt_verified":receipt_verified}
