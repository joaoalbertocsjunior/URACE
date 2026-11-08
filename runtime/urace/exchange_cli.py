"""CLI grammar shared by direct CLI and typed machine clients."""
from pathlib import Path
import json
import hashlib
import time as _time_mod

# ── Crypto network readiness ──────────────────────────────────────────────────
# Features marked CRYPTO_PENDING are implemented but not connected to any
# blockchain network. They will activate when `exchange settings set --crypto-network <id>`
# is configured. Gas fees are accounted for when present.
# Currently: token_settlement, cross-chain-transfer
CRYPTO_PENDING_FEATURES = frozenset({
    'token_settlement',      # mainnet settlement — disabled until blockchain configured
    'cross_chain_transfer',  # future: bridge to ETH/SOL — gas fee aware
})


def _check_auto_delist(feature_id: str, exchange) -> dict:
    """Check if a feature should be auto-delisted due to sustained negative outcomes.

    Rule: negative_count >= 3 AND (negative_count - positive_count) >= 3.
    If triggered, writes FEATURE_AUTO_DELISTED to ledger and returns auto_delisted=True.
    """
    try:
        rows = exchange.audit_rows()
    except Exception:
        return {"auto_delisted": False, "reason": "audit_unavailable"}
    positive = 0
    negative = 0
    for r in rows:
        if r.get("kind") == "FEATURE_RATING" and r.get("feature_id") == feature_id:
            outcome = r.get("outcome", "")
            if outcome == "positive":
                positive += 1
            elif outcome == "negative":
                negative += 1
    if negative >= 3 and (negative - positive) >= 3:
        import time as _t
        exchange.append_audit_row({
            "kind": "FEATURE_AUTO_DELISTED",
            "feature_id": feature_id,
            "reason": "sustained_negative_outcomes",
            "negative_count": negative,
            "positive_count": positive,
            "at_unix": _t.time(),
        })
        return {"auto_delisted": True, "reason": "sustained_negative_outcomes",
                "negative_count": negative, "positive_count": positive}
    return {"auto_delisted": False, "negative_count": negative, "positive_count": positive}


def _listing_expired(listing: dict, settings: dict) -> bool:
    """Return True if a listing's listed_at age exceeds listing_ttl_days (default 90)."""
    ttl_days = int(settings.get("listing_ttl_days", 90))
    listed_at = listing.get("listed_at", "")
    if not listed_at:
        return False
    try:
        from datetime import datetime, timezone, timedelta
        age = datetime.now(timezone.utc) - datetime.fromisoformat(listed_at)
        return age > timedelta(days=ttl_days)
    except (ValueError, TypeError):
        return False


def _validate_freeform_query(q, max_bytes=4096):
    """Validate a freeform search/query string.

    Returns the cleaned query or raises ValueError with a clear message.
    Accepts None (blank = return all) and passes it through unchanged.
    """
    if q is None:
        return q
    if not isinstance(q, str):
        raise ValueError("Query must be a string")
    if "\x00" in q:
        raise ValueError("Query must not contain null bytes")
    if len(q.encode("utf-8")) > max_bytes:
        raise ValueError(f"Query exceeds maximum length of {max_bytes} bytes")
    return q

def grammar(children):
 from .command_surface import output_options,boolean
 root=children.add_parser('exchange',help='opt-in signed peer artifacts; default off, incoming content quarantined');root.set_defaults(action='exchange');output_options(root);groups=root.add_subparsers(dest='exchange_group',required=True)
 for name in ('status','audit'):
  p=groups.add_parser(name);output_options(p)
  if name=='audit':
   p.add_argument('--detail',action='store_true');p.add_argument('--limit',type=int,default=50);p.add_argument('--offset',type=int,default=0);p.add_argument('--peer-id');p.add_argument('--feature-id')
 p=groups.add_parser('rank');p.add_argument('--want',action='append');output_options(p)
 settings=groups.add_parser('settings');settings_v=settings.add_subparsers(dest='exchange_verb',required=True);output_options(settings_v.add_parser('show'));p=settings_v.add_parser('set');output_options(p)
 for name in ('enabled','network','advertise','auto-select'):p.add_argument('--'+name,type=boolean)
 for name in ('max-transfers-per-day','max-transfers-per-peer-per-day','max-bytes-per-day','max-rpc-per-day','max-rpc-per-peer-per-day'):p.add_argument('--'+name,type=int)
 p.add_argument('--min-peer-version',type=int)
 # Granular P2P capability controls
 for name in ('feature-borrow-enabled','p2p-mint-enabled','p2p-sell-enabled','compress-enabled','decompress-enabled','compress-wire'):p.add_argument('--'+name,type=boolean,default=None)
 p.add_argument('--bundle-max-age-seconds',type=int,default=None,dest='bundle_max_age_seconds',help='max age in seconds for accepted bundles (default 604800)')
 p.add_argument('--bandwidth-profile',choices=('auto','low','high'),default=None,dest='bandwidth_profile',help='wire transfer profile: low=1KB chunks+compress, high=64KB chunks, auto=default (default: auto)')
 p.add_argument('--transfer-chunk-size',type=int,default=None,dest='transfer_chunk_size',help='override wire read chunk size in bytes (512–131072; overrides bandwidth-profile default)')
 p.add_argument('--relay-only',type=boolean,default=None,dest='relay_only',help='hide IP from peers by routing all traffic through relays')
 p.add_argument('--crypto-network',default=None,dest='crypto_network',help='blockchain network id for future token settlement (informational; activates CRYPTO_PENDING features)')
 p.add_argument('--consensus-min-threshold',type=int,default=None,dest='consensus_min_threshold',help='minimum consensus peer threshold for corpus updates (default 2)')
 p.add_argument('--baseline-grant-tokens',type=int,default=None,dest='baseline_grant_tokens',help='baseline token grant for new peers (default 3)')
 p.add_argument('--network-mode',choices=('intranet','internet','hybrid'),default=None,dest='network_mode',help='network scope: intranet=LAN-only, internet=standard, hybrid=LAN+internet (default: hybrid)')
 p.add_argument('--internet-gateway',default=None,dest='internet_gateway',help='peer-id of the internet bridge peer for intranet→internet upgrade')
 peers=groups.add_parser('peer');peers_v=peers.add_subparsers(dest='exchange_verb',required=True)
 for name in ('list','identity','add','block','unblock'):
  p=peers_v.add_parser(name);output_options(p)
  if name=='add':p.add_argument('--certificate',required=True);p.add_argument('--endpoint');p.add_argument('--post-quantum-identity')
  elif name not in ('list','identity'):p.add_argument('peer_id')
 p=peers_v.add_parser('rotate',help='rotate peer identity (block old, pin new cert, migrate rules)');output_options(p);p.add_argument('old_peer_id');p.add_argument('--new-certificate',required=True,dest='new_certificate')
 p=peers_v.add_parser('role',help='set or show peer role (admin|operator|readonly)');output_options(p);p.add_argument('peer_id',nargs='?',default=None);p.add_argument('--set',dest='role_value',choices=('admin','operator','readonly'),default=None)
 bootstrap=groups.add_parser('bootstrap',help='manage bootstrap peers for zero-config P2P discovery');bootstrap_v=bootstrap.add_subparsers(dest='exchange_verb',required=True)
 for name in ('list','add','remove'):
  p=bootstrap_v.add_parser(name,help=name+' bootstrap peer endpoints');output_options(p)
  if name in ('add','remove'):p.add_argument('endpoint',help='HTTPS endpoint of bootstrap peer (e.g. https://peer.example.com:8443)')
 f=groups.add_parser('feature');verbs=f.add_subparsers(dest='exchange_verb',required=True);p=verbs.add_parser('define');p.add_argument('feature_id');p.add_argument('--depends-on',action='append',default=[]);p.add_argument('--wanted',type=boolean,default=False);p.add_argument('--offered',type=boolean,default=False);p.add_argument('--wants',action='append',default=[]);p.add_argument('--language',default=None,help='optional language tag for filtering (e.g. python, javascript, language-agnostic)');output_options(p)
 p=verbs.add_parser('policy');p.add_argument('feature_id');p.add_argument('--access',choices=('reviewed-direct','open'));p.add_argument('--license-id');p.add_argument('--essential',type=boolean);p.add_argument('--open-after-unix',type=float);p.add_argument('--resale',type=boolean);output_options(p)
 p=verbs.add_parser('catalog');output_options(p)
 p=verbs.add_parser('declare');p.add_argument('feature_id');p.add_argument('--manifest',required=True);output_options(p)
 p=verbs.add_parser('lifecycle');p.add_argument('atom_id');p.add_argument('status',choices=('active','deprecated','obsolete'));p.add_argument('--replacement');output_options(p)
 p=verbs.add_parser('rate',help='record borrower outcome for a feature');p.add_argument('feature_id');p.add_argument('--outcome',choices=('positive','negative','neutral'),required=True);p.add_argument('--score',type=float,default=None,help='optional quality delta observed');output_options(p)
 p=verbs.add_parser('recommend',help='recommend top ledger features for current project context');p.add_argument('--limit',type=int,default=5);output_options(p)
 rules=groups.add_parser('rule');rules_v=rules.add_subparsers(dest='exchange_verb',required=True)
 p=rules_v.add_parser('set');p.add_argument('peer_id');p.add_argument('feature_id');p.add_argument('direction',choices=('send','receive'));p.add_argument('--allow',type=boolean,required=True);output_options(p)
 p=rules_v.add_parser('export',help='export all rules to JSON for backup or migration');output_options(p);p.add_argument('--file',default=None,dest='export_file')
 p=rules_v.add_parser('import',help='import rules from a JSON file');output_options(p);p.add_argument('--file',required=True,dest='import_file')
 ledger=groups.add_parser('ledger');ledger_v=ledger.add_subparsers(dest='exchange_verb',required=True)
 p=ledger_v.add_parser('summary');output_options(p)
 p=ledger_v.add_parser('balance');p.add_argument('peer_id');output_options(p)
 p=ledger_v.add_parser('history');p.add_argument('peer_id');p.add_argument('--limit',type=int,default=50);output_options(p)
 p=ledger_v.add_parser('earned',help='show earned_balance (REP_SOURCE_WORK only) for a peer');p.add_argument('peer_id');output_options(p)
 p=ledger_v.add_parser('transfer',help='manually transfer tokens to a peer for settlement');p.add_argument('peer_id');p.add_argument('amount_units',type=int);p.add_argument('--yes',action='store_true',help='skip spend confirmation prompt');output_options(p)
 p=ledger_v.add_parser('supply-calc',help='derive P2P-optimal token supply from network physics');output_options(p);p.add_argument('--peers',type=int,default=1000,dest='max_network_peers');p.add_argument('--ledger-mb',type=float,default=50.0,dest='target_ledger_mb');p.add_argument('--bandwidth-kbps',type=int,default=1000,dest='sync_bandwidth_kbps');p.add_argument('--sync-secs',type=float,default=30.0,dest='target_sync_seconds');p.add_argument('--row-bytes',type=int,default=400,dest='avg_row_bytes');p.add_argument('--rows-per-feature',type=int,default=20);p.add_argument('--adoption-rate',type=float,default=0.10,dest='adoption_rate')
 cmp=groups.add_parser('compact',help='P2P ledger compaction, sync optimization and search');cmp_v=cmp.add_subparsers(dest='exchange_verb',required=True)
 p=cmp_v.add_parser('contracts',help='compact closed work contracts into summary rows');output_options(p);p.add_argument('--older-than-days',type=float,default=7.0,dest='older_than_days')
 p=cmp_v.add_parser('checkpoint',help='write a ledger checkpoint for P2P bootstrap');output_options(p)
 p=cmp_v.add_parser('search',help='search or query the P2P audit ledger (freeform or structured)');output_options(p);p.add_argument('query',nargs='?',default=None,help='freeform text query, field=value filter, or leave blank for summary');p.add_argument('--kind',help='filter by audit row kind',default=None);p.add_argument('--peer',help='filter by peer id',default=None);p.add_argument('--feature',help='filter by feature id',default=None,dest='search_feature');p.add_argument('--since-unix',type=float,default=None,dest='since_unix');p.add_argument('--limit',type=int,default=50)
 p=cmp_v.add_parser('sync-tail',help='show checkpoint + tail rows needed for fast sync');output_options(p)
 p=cmp_v.add_parser('sync-state',help='show ledger sliding-window sync state (v3 light-peer readiness)');output_options(p)
 p=cmp_v.add_parser('light-balance',help='compute balance from seal snapshot + tail (light-peer mode, no full history needed)');output_options(p);p.add_argument('peer_id')
 p=cmp_v.add_parser('depletion',help='check depletion status of a feature equity');output_options(p);p.add_argument('feature_id');p.add_argument('--network-size',type=int,default=1,dest='network_size')
 p=cmp_v.add_parser('balance-fast',help='O(tail) credit balance using latest sealed block');output_options(p);p.add_argument('peer_id')
 p=cmp_v.add_parser('compress',help='compress old P2P audit rows to local archive (local only — no network impact)');output_options(p);p.add_argument('--older-than-days',type=float,default=30.0,dest='older_than_days');p.add_argument('--dry-run',action='store_true',dest='dry_run')
 p=cmp_v.add_parser('decompress',help='decompress a local P2P audit archive for inspection');output_options(p);p.add_argument('archive_id',nargs='?',default=None,help='archive id to decompress; omit to list archives');p.add_argument('--limit',type=int,default=200)
 bundles=groups.add_parser('bundle');verbs=bundles.add_subparsers(dest='exchange_verb',required=True)
 for name in ('prepare','inspect','send','import','review','evaluate','manifest'):
  p=verbs.add_parser(name);output_options(p)
  if name=='prepare':p.add_argument('peer_id');p.add_argument('feature_id');p.add_argument('--file',required=True);p.add_argument('--reviewed',action='store_true')
  elif name=='import':p.add_argument('--file',required=True)
  elif name=='manifest':p.add_argument('peer_id');p.add_argument('--baseline-evaluation-id',required=True);p.add_argument('--failures',action='append',default=[])
  else:p.add_argument('bundle_id')
  if name=='review':p.add_argument('review_status',choices=('approved-for-evaluation','rejected','blocked'));p.add_argument('--note',default='')
 p=verbs.add_parser('fetch-artifact',help='fetch artifact bytes for a bundle from peer');output_options(p);p.add_argument('bundle_id');p.add_argument('--out',default=None,dest='out_path',help='write artifact bytes to this file path (default: print sha256 and size only)')
 chunk=groups.add_parser('chunk',help='erasure-coded artifact chunk store (v2 DHT path)');chunk_v=chunk.add_subparsers(dest='exchange_verb',required=True)
 p=chunk_v.add_parser('status',help='show chunk store status for an artifact sha256');output_options(p);p.add_argument('artifact_sha256')
 p=chunk_v.add_parser('store',help='manually store an artifact in the chunk store');output_options(p);p.add_argument('artifact_sha256');p.add_argument('--input',required=True,dest='input_path',help='path to artifact file')
 p=chunk_v.add_parser('find-holders',help='Kademlia DHT lookup: find peers closest to chunk routing key (v3)');output_options(p);p.add_argument('artifact_sha256');p.add_argument('chunk_idx',type=int)
 market=groups.add_parser('market',help='live token velocity, supply ratio and network health snapshot');market_v=market.add_subparsers(dest='exchange_verb',required=True)
 p=market_v.add_parser('stats',help='mint/burn velocity, supply ratio, peer count, feature stats');output_options(p);p.add_argument('--window-hours',type=int,default=24,dest='window_hours',help='velocity window in hours (default 24)')
 network=groups.add_parser('network');verbs=network.add_subparsers(dest='exchange_verb',required=True)
 for name in ('discover','probe','refresh','serve'):
  p=verbs.add_parser(name);output_options(p)
  if name=='discover':p.add_argument('--seconds',type=int,default=3)
  if name=='refresh':p.add_argument('--limit',type=int,default=3)
  if name=='probe':p.add_argument('peer_id')
  if name=='serve':p.add_argument('--host',default='127.0.0.1');p.add_argument('--port',type=int,default=0)
 p=verbs.add_parser('assets',help='search authenticated peer catalogs; paid asks are discovery-only');output_options(p);p.add_argument('query',nargs='?',default='');p.add_argument('--peer-limit',type=int,default=3,dest='peer_limit')
 p=verbs.add_parser('fetch-asset',help='fetch a declared open-use asset into quarantine; never executes it');output_options(p);p.add_argument('peer_id');p.add_argument('asset_id')
 p=verbs.add_parser('consensus-status',help='show P2P consensus threshold and mismatch state');output_options(p)
 p=verbs.add_parser('public-address',help='probe STUN to discover public IP:port for intranet→internet bridge');output_options(p);p.add_argument('--stun-host',default='stun.l.google.com',dest='stun_host',help='STUN server hostname (default: stun.l.google.com)');p.add_argument('--stun-port',type=int,default=19302,dest='stun_port',help='STUN server port (default: 19302)')
 p=verbs.add_parser('disconnect',help='temporarily pause P2P networking (reconnects on next serve)');output_options(p);p.add_argument('--duration-minutes',type=int,default=60,dest='duration_minutes')
 p=verbs.add_parser('peers',help='show connected peer count and anonymized peer IDs (no raw IPs or endpoints)');output_options(p);p.add_argument('--detail',action='store_true',help='show hashed peer IDs (still anonymized)')
 p=verbs.add_parser('size',help='show estimated network size from peer discovery gossip (heuristic, not exact)');output_options(p)
 p=verbs.add_parser('routing-table',help='show Kademlia DHT routing table (v3 chunk discovery readiness)');output_options(p)
 p=verbs.add_parser('port-to-internet',help='analyze intranet features/reputation and guide migration to hybrid/internet mode');output_options(p);p.add_argument('--auto',action='store_true',help='use smart defaults, no prompts');p.add_argument('--dry-run',action='store_true',dest='dry_run',help='analyze and report, no changes made');p.add_argument('--features',default=None,dest='features',help='comma-separated feature IDs to port (overrides auto-selection)');p.add_argument('--min-kpi-score',type=float,default=0.5,dest='min_kpi_score',help='minimum KPI score for auto-selection (default 0.5)');p.add_argument('--min-ratings',type=int,default=2,dest='min_ratings',help='minimum ratings needed for auto-selection (default 2)')
 p=verbs.add_parser('find-node',help='Kademlia find_node RPC stub (v3)');output_options(p);p.add_argument('target_peer_id')
 p=verbs.add_parser('shamir-deliver',help='deliver Shamir DEK share to replica holder (v3 stub)');output_options(p);p.add_argument('feature_id');p.add_argument('--holder',required=True,dest='holder_peer_id');p.add_argument('--share-index',type=int,required=True,dest='share_index')
 p=verbs.add_parser('tail-sync',help='pull ledger seal+tail from full peer (v3 stub)');output_options(p);p.add_argument('--from-peer',required=True,dest='from_peer_id')
 # ── Work market ──────────────────────────────────────────────────────────────
 wm=groups.add_parser('work',help='P2P work request market and escrow');wm_v=wm.add_subparsers(dest='exchange_verb',required=True)
 p=wm_v.add_parser('list',help='list work requests');output_options(p);p.add_argument('--state',default=None)
 p=wm_v.add_parser('status',help='show state of a work request');output_options(p);p.add_argument('request_id')
 p=wm_v.add_parser('create',help='create work request');output_options(p);p.add_argument('spec');p.add_argument('--budget',type=int,required=True);p.add_argument('--min-rep',type=float,default=0.3,dest='min_rep');p.add_argument('--nodes',type=int,default=1);p.add_argument('--complexity',type=float,default=0.5);p.add_argument('--mode',choices=('agora','cohort'),default='agora',dest='work_mode',help='agora: open marketplace (default); cohort: trusted group only (pinned + reputation >= floor)');p.add_argument('--cohort-reputation-floor',type=float,default=0.5,dest='cohort_rep_floor',help='minimum reputation for cohort mode (default 0.5)')
 p=wm_v.add_parser('bid',help='bid on a work request');output_options(p);p.add_argument('request_id');p.add_argument('--rep',type=float,required=True,dest='combined_rep')
 p=wm_v.add_parser('accept',help='accept a bid');output_options(p);p.add_argument('request_id');p.add_argument('--bidder',required=True,dest='bidder_id')
 p=wm_v.add_parser('deliver',help='submit delivery');output_options(p);p.add_argument('request_id');p.add_argument('--hash',required=True,dest='delivery_hash')
 p=wm_v.add_parser('verify',help='verify a delivery');output_options(p);p.add_argument('request_id');p.add_argument('--approve',type=boolean,required=True);p.add_argument('--reason',default='');p.add_argument('--dispute-kind',choices=('quality','gibberish','timeout','other'),default='quality',dest='dispute_kind')
 p=wm_v.add_parser('review',help='submit peer review for quorum');output_options(p);p.add_argument('request_id');p.add_argument('--approve',type=boolean,required=True)
 p=wm_v.add_parser('merge',help='merge as co-requester');output_options(p);p.add_argument('request_id');p.add_argument('--budget',type=int,required=True,dest='co_budget')
 p=wm_v.add_parser('arbitrate',help='trigger neutral arbitrator selection for disputed request');output_options(p);p.add_argument('request_id');p.add_argument('--count',type=int,default=3,dest='n')
 p=wm_v.add_parser('claim',help='claim ownership of delivered work within 30-day window');output_options(p);p.add_argument('request_id');p.add_argument('--mint-value',type=int,default=0,dest='mint_value')
 p=wm_v.add_parser('decompose',help='auto-decompose high-complexity request into parallel sub-requests');output_options(p);p.add_argument('spec');p.add_argument('--budget',type=int,required=True);p.add_argument('--complexity',type=float,default=0.8)
 p=wm_v.add_parser('chain-root',help='compute tamper-evident audit chain hash root');output_options(p)
 # ── Equity ───────────────────────────────────────────────────────────────────
 eq=groups.add_parser('equity',help='feature ownership equity trading');eq_v=eq.add_subparsers(dest='exchange_verb',required=True)
 p=eq_v.add_parser('holdings',help='show equity holdings for a feature');output_options(p);p.add_argument('feature_id')
 p=eq_v.add_parser('grant',help='grant initial equity (creator only)');output_options(p);p.add_argument('feature_id');p.add_argument('--creator',required=False,default=None,dest='creator_id',help='creator peer_id (default: local node identity)');p.add_argument('--description',default='',help='human-readable feature description for P2P discovery');p.add_argument('--tags',default='',help='comma-separated tags for search/routing');p.add_argument('--include-context',default=None,dest='include_context',help='comma-separated context kinds to include as mint metadata (objectives,evidence,decisions); omit or leave empty to include none');p.add_argument('--isolate-context',action='store_true',dest='isolate_context',help='snapshot context per-feature (isolated, not combined)');p.add_argument('--skip-pii-check',action='store_true',dest='skip_pii_check',help='suppress PII warning scan on context snapshot');p.add_argument('--spec-context',default=None,dest='spec_context',help='behavior specification — what this feature does (not how); stored in bundle so executor implements to spec (reduces C2 spin cost)');p.add_argument('--artifact-path',default=None,dest='artifact_path',help='path to artifact file (zip bundle or single file); auto-detects sub-feature composition');p.add_argument('--visibility',choices=('private','org','public'),default='public',dest='visibility',help='feature visibility: private=creator only, org=same org, public=anyone (default: public)')
 p=eq_v.add_parser('sell',help='sell equity tranche');output_options(p);p.add_argument('feature_id');p.add_argument('--to',required=True,dest='buyer_id');p.add_argument('--bp',type=int,required=True,dest='basis_points');p.add_argument('--price',type=int,default=0,dest='price_units')
 p=eq_v.add_parser('price',help='current market price for a feature');output_options(p);p.add_argument('feature_id')
 p=eq_v.add_parser('transfers',help='list equity transfer history for a feature');output_options(p);p.add_argument('feature_id')
 p=eq_v.add_parser('list-for-sale',help='list equity for sale on the open market');output_options(p);p.add_argument('feature_id');p.add_argument('--bp',type=int,required=False,default=None,dest='basis_points');p.add_argument('--price',type=int,required=False,default=None,dest='ask_price')
 p=eq_v.add_parser('listings',help='show open equity listings (all or for a feature)');output_options(p);p.add_argument('--feature',default=None,dest='feature_id')
 p=eq_v.add_parser('cancel-listing',help='cancel an open equity listing');output_options(p);p.add_argument('listing_id')
 p=eq_v.add_parser('fill-listing',help='buy a specific open listing');output_options(p);p.add_argument('listing_id');p.add_argument('--yes',action='store_true',help='skip spend confirmation prompt');p.add_argument('--skip-quality-check',action='store_true',dest='skip_quality_check',help='suppress borrow history quality summary');p.add_argument('--skip-trust-check',action='store_true',dest='skip_trust_check',help='suppress seller trust score warning')
 p=eq_v.add_parser('deprecate',help='mark a feature as deprecated (no new borrows allowed)');output_options(p);p.add_argument('feature_id');p.add_argument('--reason',default='',help='reason for deprecation');p.add_argument('--creator',required=True,dest='creator_id')
 p=eq_v.add_parser('register-replica',help='register self as delivery replica holder for a feature bundle');output_options(p);p.add_argument('feature_id');p.add_argument('--artifact-hash',default='',dest='artifact_hash',help='sha256 of the bundle artifact you hold (for verification)');p.add_argument('--chunk-indices',default=None,dest='chunk_indices',help='comma-separated chunk indices this replica holds (default: all)')
 p=eq_v.add_parser('auto-buy',help='run one auto-buy pass against configured thresholds');output_options(p)
 p=eq_v.add_parser('auto-sell',help='run one auto-sell pass, listing qualifying equity');output_options(p)
 p=eq_v.add_parser('challenge',help='file a provenance challenge against a minted feature');output_options(p);p.add_argument('feature_id');p.add_argument('--challenger',required=True,dest='challenger_id');p.add_argument('--reference-feature',default='',dest='reference_feature_id',help='feature_id this asset was derived from');p.add_argument('--evidence',default='',help='supporting evidence text');p.add_argument('--stake',type=int,default=None,dest='challenger_stake',help='challenger stake units (default: challenger_stake_units from policy)')
 p=eq_v.add_parser('resolve-challenge',help='resolve a pending provenance challenge');output_options(p);p.add_argument('challenge_id');p.add_argument('--verdict',required=True,choices=['upheld','rejected']);p.add_argument('--resolver',default='local',dest='resolver_id')
 p=eq_v.add_parser('release-stake',help='release mint stake after challenge window expires');output_options(p);p.add_argument('feature_id')
 p=eq_v.add_parser('challenge-status',help='show staking and challenge status for a feature');output_options(p);p.add_argument('feature_id')
 p=eq_v.add_parser('cost',help='show operation cost breakdown');output_options(p);p.add_argument('operation',choices=['mint_feature','borrow_feature','list_for_sale','challenge','vs_executor']);p.add_argument('--price',type=int,default=0,dest='ask_price_units');p.add_argument('--artifact-size',type=int,default=0,dest='artifact_size_bytes');p.add_argument('--executor-calls',type=int,default=1,dest='executor_calls_saved')
 p=eq_v.add_parser('dek-unwrap',help='unwrap a session-bound DEK using buyer private key');output_options(p);p.add_argument('--listing-id',required=True,dest='listing_id');p.add_argument('--private-key-hex',required=True,dest='private_key_hex',help='buyer X25519 private key as hex (raw 32 bytes)')
 p=eq_v.add_parser('escrow-status',help='show pending escrow items and timeout status');output_options(p)
 tc=eq_v.add_parser('trade-config',help='show or update auto-trade thresholds');tc_v=tc.add_subparsers(dest='trade_verb',required=True)
 output_options(tc_v.add_parser('show'))
 p=tc_v.add_parser('set');output_options(p)
 p.add_argument('--auto-buy-enabled',type=boolean,dest='auto_buy_enabled',default=None)
 p.add_argument('--min-quality',type=float,dest='min_quality_wilson',default=None)
 p.add_argument('--min-adoption',type=int,dest='min_adoption_count',default=None)
 p.add_argument('--max-price-mult',type=float,dest='max_price_multiplier',default=None)
 p.add_argument('--max-bp',type=int,dest='max_bp_per_feature',default=None)
 p.add_argument('--max-spend',type=int,dest='max_spend_per_run_units',default=None)
 p.add_argument('--max-adoption-rate',type=float,dest='max_adoption_rate',default=None)
 p.add_argument('--min-supply-pressure',type=float,dest='min_supply_pressure',default=None)
 p.add_argument('--min-remaining-adopters',type=int,dest='min_remaining_adopters',default=None)
 p.add_argument('--min-lucrativity',type=float,dest='min_lucrativity_score',default=None)
 p.add_argument('--lucrativity-window',type=float,dest='lucrativity_window_days',default=None)
 p.add_argument('--auto-sell-enabled',type=boolean,dest='auto_sell_enabled',default=None)
 p.add_argument('--min-return-mult',type=float,dest='min_return_multiplier',default=None)
 p.add_argument('--bp-to-sell',type=int,dest='bp_to_sell_per_trigger',default=None)
 p.add_argument('--min-hold-bp',type=int,dest='min_hold_bp_to_trigger',default=None)
 p.add_argument('--sell-on-near-depleted',type=boolean,dest='sell_on_near_depleted',default=None)
 p.add_argument('--sell-on-slowing',type=boolean,dest='sell_on_slowing',default=None)
 p.add_argument('--preset',choices=('conservative','balanced','aggressive'),dest='preset',default=None,help='apply a named auto-trade preset')
 p.add_argument('--auto-tune',action='store_true',dest='auto_tune',default=False,help='auto-derive optimal settings from network conditions')
 p.add_argument('--roi-preference',choices=('short_term','medium_term','long_term'),dest='roi_preference',default=None,help='select preset by ROI preference')
 p_show_presets=tc_v.add_parser('show-presets',help='list available auto-trade presets with descriptions');output_options(p_show_presets)
 p=eq_v.add_parser('visibility',help='show visibility setting for a feature');output_options(p);p.add_argument('--feature-id',required=True,dest='feature_id',help='feature id to query')
 # ── On-chain bridge stubs ─────────────────────────────────────────────────────
 br=groups.add_parser('bridge',help='optional on-chain attestation bridge stubs');br_v=br.add_subparsers(dest='exchange_verb',required=True)
 p=br_v.add_parser('nft-mint',help='request NFT attestation mint (stub)');output_options(p);p.add_argument('--feature-id',required=True,dest='feature_id');p.add_argument('--creator',default=None,dest='creator_id')
 p=br_v.add_parser('on-ramp',help='request crypto on-ramp (stub)');output_options(p);p.add_argument('--amount',type=int,required=True,dest='amount_units');p.add_argument('--address',required=True,dest='crypto_address')
 p=br_v.add_parser('off-ramp',help='request crypto off-ramp (stub)');output_options(p);p.add_argument('--amount',type=int,required=True,dest='amount_units');p.add_argument('--address',required=True,dest='crypto_address')
 p=br_v.add_parser('on-chain-verify',help='request on-chain feature verification (stub)');output_options(p);p.add_argument('--feature-id',required=True,dest='feature_id')
 # ── Reputation ───────────────────────────────────────────────────────────────
 rp=groups.add_parser('reputation',help='earned vs market reputation');rp_v=rp.add_subparsers(dest='exchange_verb',required=True)
 p=rp_v.add_parser('show',help='reputation breakdown for a peer');output_options(p);p.add_argument('peer_id')
 p=rp_v.add_parser('leaderboard',help='top peers by earned reputation');output_options(p);p.add_argument('--limit',type=int,default=10)
 p=rp_v.add_parser('history',help='reputation event trend for a peer');output_options(p);p.add_argument('peer_id');p.add_argument('--days',type=int,default=30,dest='window_days')
 # ── Network audit ─────────────────────────────────────────────────────────────
 na=groups.add_parser('network-audit',help='view P2P network events (discover, consensus, RPC)');na_v=na.add_subparsers(dest='exchange_verb',required=True)
 p=na_v.add_parser('list',help='list P2P network audit events');output_options(p);p.add_argument('--kind',help='filter by event kind',default=None);p.add_argument('--peer',help='filter by peer id',default=None);p.add_argument('--limit',type=int,default=100)
 rst=groups.add_parser('reset',help='clear all exchange data for a clean release build');rst_v=rst.add_subparsers(dest='exchange_verb',required=True)
 p=rst_v.add_parser('all',help='delete all exchange audit rows (balances, listings, work history)');output_options(p);p.add_argument('--yes',action='store_true')
 return root

def bounded_file(name,limit,artifact=False):
 path=Path(name)
 if '..' in path.parts:raise ValueError('Parent traversal prohibited')
 for candidate in (path,path.resolve()):
  if any(part.startswith('.') for part in candidate.parts if part!='.'):raise ValueError('Protected file path prohibited')
 probe=Path(path.anchor or '.')
 for part in path.parts[1:] if path.is_absolute() else path.parts:
  probe=probe/part
  if probe.is_symlink():raise ValueError('Symlink path prohibited')
 if artifact:
  _BLOCKED = ('credential','secret','.env','password','private_key','id_rsa','id_ed25519')
  if any(word in path.name.lower() for word in _BLOCKED):raise ValueError('Artifact filename matches sensitive file pattern — excluded for safety')
  from ._common import SYSTEM_ROOT
  path.resolve().relative_to(SYSTEM_ROOT.resolve())
 if not path.is_file() or path.stat().st_size>limit:raise ValueError('Bounded regular file required')
 return path.read_text()

def _port_to_internet_analysis(exchange, settings):
    """Analyze intranet state and return what's worth porting."""
    from . import stun_client as _stun
    result = {
        "public_address": None,
        "stun_available": False,
        "features": [],
        "network_mode": settings.get("network_mode", "intranet"),
        "already_internet": False,
    }
    if result["network_mode"] in ("internet", "hybrid"):
        result["already_internet"] = True
        return result
    addr = _stun.get_public_address()
    if addr:
        result["public_address"] = addr
        result["stun_available"] = True
    try:
        rows = exchange.audit_rows()
    except Exception:
        rows = []
    minted = {}
    for row in rows:
        if row.get("kind") == "FEATURE_MINTED" or row.get("kind") == "EQUITY_GRANT":
            fid = row.get("feature_id") or row.get("id", "")
            if fid and fid not in minted:
                minted[fid] = {"feature_id": fid, "description": row.get("description", ""), "positive": 0, "negative": 0, "neutral": 0}
        if row.get("kind") == "FEATURE_RATING":
            fid = row.get("feature_id", "")
            if fid in minted:
                outcome = row.get("outcome", "neutral")
                minted[fid][outcome] = minted[fid].get(outcome, 0) + 1
    for fid, info in minted.items():
        total = info["positive"] + info["negative"] + info["neutral"]
        kpi_score = (info["positive"] - info["negative"]) / max(total, 1)
        result["features"].append({
            "feature_id": fid,
            "description": info["description"][:80],
            "kpi_score": round(kpi_score, 3),
            "total_ratings": total,
            "positive": info["positive"],
            "negative": info["negative"],
        })
    result["features"].sort(key=lambda f: f["kpi_score"], reverse=True)
    return result


def _select_features_for_port(analysis, args):
    """Select which features to port based on args."""
    if getattr(args, "features", None):
        ids = {f.strip() for f in args.features.split(",") if f.strip()}
        return [f for f in analysis["features"] if f["feature_id"] in ids]
    min_kpi = float(getattr(args, "min_kpi_score", 0.5))
    min_ratings = int(getattr(args, "min_ratings", 2))
    return [
        f for f in analysis["features"]
        if f["kpi_score"] >= min_kpi and f["total_ratings"] >= min_ratings
    ]


def _format_port_report(report):
    addr = report.get("public_address", {}) or {}
    print("\nPort-to-internet analysis:")
    print(f"  Public address : {addr.get('ip')}:{addr.get('port')}")
    print(f"  Recommended mode: {report.get('recommended_mode', 'hybrid')}")
    print(f"\n  Features to port ({len(report['features_to_port'])}):")
    for f in report["features_to_port"]:
        print(f"    \u2022 {f['feature_id'][:16]} \u2014 kpi={f['kpi_score']:+.2f} ({f['positive']}\u2191/{f['negative']}\u2193) \u2014 {f['description'][:50]}")
    if report["features_skipped"]:
        print(f"\n  Features skipped ({len(report['features_skipped'])}) \u2014 below quality threshold:")
        for f in report["features_skipped"]:
            print(f"    \u25cb {f['feature_id'][:16]} \u2014 kpi={f['kpi_score']:+.2f} ({f['total_ratings']} ratings)")


def run(args,config):
 from . import peer_exchange as pe
 exchange=pe.Exchange(pe.directory(config));group=args.exchange_group;verb=getattr(args,'exchange_verb',None);result=None
 if group in ('status','audit'):
  result=exchange.summary(getattr(args,'detail',False),getattr(args,'limit',50),getattr(args,'offset',0),getattr(args,'peer_id',None),getattr(args,'feature_id',None))
  if group=='status':
   from .credit_ledger import summary as cl_summary
   try:result['credits']=cl_summary(exchange.root)
   except (OSError,ValueError):result['credits']=None
 elif group=='rank':
  from .peer_selection import rank
  result=rank(exchange,args.want)
 elif group=='settings':
  SETTINGS_KEYS=('enabled','network','advertise','auto_select','max_transfers_per_day','max_transfers_per_peer_per_day','max_bytes_per_day','max_rpc_per_day','max_rpc_per_peer_per_day','min_peer_version','feature_borrow_enabled','p2p_mint_enabled','p2p_sell_enabled','compress_enabled','decompress_enabled','bundle_max_age_seconds','relay_only','crypto_network','compress_wire','bandwidth_profile','transfer_chunk_size')
  changes={k:getattr(args,k) for k in SETTINGS_KEYS if getattr(args,k,None) is not None}
  if verb=='set':
   if getattr(args,'consensus_min_threshold',None) is not None:
    cfg2=exchange.load();cfg2.setdefault('p2p',{})['consensus_trigger_min_peers']=args.consensus_min_threshold
    from ._common import atomic_write_json;atomic_write_json(exchange.root/'policy.json',cfg2)
   if getattr(args,'baseline_grant_tokens',None) is not None:
    cfg2=exchange.load();cfg2.setdefault('p2p',{})['baseline_grant_tokens']=args.baseline_grant_tokens
    from ._common import atomic_write_json;atomic_write_json(exchange.root/'policy.json',cfg2)
   if getattr(args,'network_mode',None) is not None:
    cfg2=exchange.load();cfg2['network_mode']=args.network_mode
    from ._common import atomic_write_json;atomic_write_json(exchange.root/'policy.json',cfg2)
   if getattr(args,'internet_gateway',None) is not None:
    cfg2=exchange.load();cfg2['internet_gateway']=args.internet_gateway
    from ._common import atomic_write_json;atomic_write_json(exchange.root/'policy.json',cfg2)
  result=exchange.configure(**changes) if verb=='set' else exchange.summary()
 elif group=='peer':
  if verb=='list':result=exchange.summary()['peers']
  elif verb=='identity':
   if not exchange.load()['enabled']:raise ValueError('Sharing disabled; enable explicitly before creating an identity')
   result=exchange.identity()
  elif verb=='add':result=exchange.peer(bounded_file(args.certificate,8192),args.endpoint,json.loads(bounded_file(args.post_quantum_identity,16384)) if args.post_quantum_identity else None)
  elif verb=='rotate':
   import hashlib,ssl
   new_cert_pem=bounded_file(args.new_certificate,8192)
   new_result=exchange.peer(new_cert_pem)
   new_peer_id=new_result.get('peer_id','')
   cfg=exchange.load()
   old_rules={k:v for k,v in cfg.get('rules',{}).items() if k.startswith(args.old_peer_id+':')}
   for rule_key,allow in old_rules.items():
    parts=rule_key.split(':')
    if len(parts)==3 and parts[0]==args.old_peer_id:
     exchange.rule(new_peer_id,parts[2],parts[1],allow)
   exchange.block(args.old_peer_id,True)
   result={'status':'rotated','old_peer_id':args.old_peer_id,'new_peer_id':new_peer_id,'rules_migrated':len(old_rules)}
  elif verb=='role':
   pid=getattr(args,'peer_id',None);role_val=getattr(args,'role_value',None)
   p2p_cfg=exchange.load();peers_map=p2p_cfg.get('peers',{})
   if role_val is not None:
    if pid not in peers_map:result={'status':'error','error':f'Unknown peer: {pid!r}'}
    else:
     peers_map[pid]['role']=role_val
     from ._common import atomic_write_json;atomic_write_json(exchange.root/'policy.json',p2p_cfg)
     result={'status':'ok','peer_id':pid,'role':role_val}
   else:
    if pid:result={'peer_id':pid,'role':peers_map.get(pid,{}).get('role','operator')}
    else:result={'peers':{p:peers_map[p].get('role','operator') for p in peers_map}}
  else:result=exchange.block(args.peer_id,verb=='block')
 elif group=='feature':
  if verb in ('catalog','declare','lifecycle'):
   from .feature_catalog import Catalog
   catalog=Catalog(exchange.root/'feature-catalog')
   if verb=='catalog':result=catalog.state()
   elif verb=='declare':result=catalog.declare(args.feature_id,json.loads(bounded_file(args.manifest,16384)))
   else:result=catalog.lifecycle(args.atom_id,args.status,args.replacement)
  elif verb=='policy':result=exchange.feature_policy(args.feature_id,{k:getattr(args,k) for k in ('access','license_id','essential','open_after_unix','resale') if getattr(args,k,None) is not None})
  elif verb=='rate':
   import time as _t
   local_id=config.get('peer_id',exchange.identity().get('peer_id','local'))
   outcome_row={'kind':'FEATURE_RATING','feature_id':args.feature_id,'outcome':args.outcome,'score':getattr(args,'score',None),'at_unix':_t.time(),'at':str(_t.time()),'peer':local_id}
   exchange.append_audit_row(outcome_row)
   # Phase 2a: check auto-delist after every rating write
   _delist_result=_check_auto_delist(args.feature_id,exchange)
   # Phase 2c: reputation decay/boost on feature ratings
   try:
    from .credit_ledger import feature_creator_id as _fcid
    _creator=_fcid(args.feature_id,exchange) if hasattr(__import__('urace.credit_ledger',fromlist=['feature_creator_id']),'feature_creator_id') else None
   except Exception:_creator=None
   if _creator:
    _rep_delta=0.3 if args.outcome=='positive' else (-0.5 if args.outcome=='negative' else 0.0)
    if _rep_delta!=0.0:
     exchange.append_audit_row({'kind':'REPUTATION_DELTA','peer':_creator,'delta':_rep_delta,'reason':f'feature_rating_{args.outcome}','feature_id':args.feature_id,'at_unix':_t.time()})
   result={'status':'ok','feature_id':args.feature_id,'outcome':args.outcome,'recorded':True,'auto_delist':_delist_result}
  elif verb=='recommend':
   from ._common import SYSTEM_ROOT
   import json as _json
   _ledger_jsonl=SYSTEM_ROOT/'exchange'/'initial_ledger'/'initial_ledger.jsonl'
   # Build KPI scores from FEATURE_RATING audit rows
   _rating_pos: dict[str,int]={}
   _rating_neg: dict[str,int]={}
   _rating_tot: dict[str,int]={}
   try:
    for _rr in exchange.audit_rows():
     if _rr.get('kind')=='FEATURE_RATING':
      _fid=_rr.get('feature_id','')
      _oc=_rr.get('outcome','')
      _rating_tot[_fid]=_rating_tot.get(_fid,0)+1
      if _oc=='positive':_rating_pos[_fid]=_rating_pos.get(_fid,0)+1
      elif _oc=='negative':_rating_neg[_fid]=_rating_neg.get(_fid,0)+1
   except Exception:pass
   features=[]
   if _ledger_jsonl.exists():
    lines=[l for l in _ledger_jsonl.read_text().splitlines() if l.strip()][1:]
    _candidates=[]
    for line in lines[:getattr(args,'limit',5)*10]:
     try:
      f=_json.loads(line)
      if f.get('borrow_price_units',0)==0:
       _fid2=f.get('feature_id','')
       _pos=_rating_pos.get(_fid2,0);_neg=_rating_neg.get(_fid2,0);_tot=_rating_tot.get(_fid2,1)
       kpi_score=(_pos-_neg)/max(_tot,1)
       _kpi_mult=0.5 if kpi_score<-0.3 else 1.0
       _entry={'feature_id':_fid2,'kind':f.get('kind_label',''),'tags':f.get('tags',[]),'borrow_price_units':0,'kpi_score':round(kpi_score,3)}
       _candidates.append((_kpi_mult*kpi_score,_entry))
     except Exception:continue
    _candidates.sort(key=lambda x:x[0],reverse=True)
    features=[e for _,e in _candidates[:getattr(args,'limit',5)]]
   result={'status':'ok','recommended':features,'count':len(features)}
  else:
   _lang=getattr(args,'language',None)
   _feat_result=exchange.feature(args.feature_id,args.depends_on,wanted=args.wanted,offered=args.offered,wants=args.wants)
   if _lang is not None:
    with exchange.lock():
     _p=exchange.load();_p['features'][args.feature_id]['language']=_lang
     from ._common import atomic_write_json as _awj;_awj(exchange.root/'policy.json',_p)
    _feat_result['language']=_lang
   result=_feat_result
 elif group=='rule':
  if verb=='set':result=exchange.rule(args.peer_id,args.feature_id,args.direction,args.allow)
  elif verb=='export':
   cfg=exchange.load();rules=cfg.get('rules',{})
   payload=json.dumps(rules,indent=2,sort_keys=True)
   if getattr(args,'export_file',None):Path(args.export_file).write_text(payload);result={'status':'exported','rule_count':len(rules),'file':args.export_file}
   else:result={'rules':rules,'rule_count':len(rules)}
  elif verb=='import':
   import os
   src=Path(args.import_file)
   if not src.is_file() or src.stat().st_size>65536:raise ValueError('Invalid import file')
   new_rules=json.loads(src.read_text())
   if not isinstance(new_rules,dict):raise ValueError('Rules file must be a JSON object')
   applied=0
   for rule_key,allow in new_rules.items():
    parts=rule_key.split(':')
    if len(parts)==3:exchange.rule(parts[0],parts[2],parts[1],bool(allow));applied+=1
   result={'status':'imported','rules_applied':applied}
  else:raise ValueError(f'Unknown rule verb: {verb!r}')
 elif group=='ledger':
  from .credit_ledger import summary as cl_summary,balance as cl_balance,history as cl_history,earned_balance as cl_earned
  if verb=='summary':result=cl_summary(exchange.root)
  elif verb=='balance':result={'peer':args.peer_id,'balance':cl_balance(exchange.root,args.peer_id)}
  elif verb=='earned':result={'peer':args.peer_id,'earned_balance':cl_earned(exchange.root,args.peer_id)}
  elif verb=='supply-calc':
   from . import ledger_compaction as _lc
   result=_lc.p2p_optimal_supply(max_network_peers=args.max_network_peers,target_ledger_mb=args.target_ledger_mb,sync_bandwidth_kbps=args.sync_bandwidth_kbps,target_sync_seconds=args.target_sync_seconds,avg_row_bytes=args.avg_row_bytes if args.avg_row_bytes!=400 else None,rows_per_feature=args.rows_per_feature if args.rows_per_feature!=20 else None,adoption_rate=args.adoption_rate,exchange=exchange)
  elif verb=='transfer':
   import time as _t,sys as _sys2
   from datetime import datetime,timezone
   if args.amount_units<=0:raise ValueError('Transfer amount must be positive')
   cfg=exchange.load()
   if args.peer_id not in cfg.get('peers',{}):raise ValueError(f'Peer {args.peer_id!r} not pinned — add peer first')
   if cfg.get('peers',{}).get(args.peer_id,{}).get('blocked'):raise ValueError(f'Peer {args.peer_id!r} is blocked')
   # Item 5: spend confirmation threshold
   _thresh=config.get('p2p',{}).get('confirm_spend_threshold_units',0)
   if _thresh>0 and args.amount_units>_thresh and not getattr(args,'yes',False):
    print(f'Transfer of {args.amount_units} units exceeds confirmation threshold {_thresh}. Add --yes to confirm.',file=_sys2.stderr);return 2
   local_id=config.get('peer_id',exchange.identity().get('peer_id','local'))
   # Circular transfer detection: if peer_B has transferred to peer_A within the window, reject
   _circ_window_h=config.get('p2p',{}).get('circular_transfer_window_hours',24)
   _circ_window_s=_circ_window_h*3600
   _now_t=_t.time()
   _audit_rows=exchange.audit_rows()
   _reverse_transfers=[r for r in _audit_rows if r.get('kind')=='CREDIT_DELTA' and r.get('direction')=='send' and r.get('local_peer')==args.peer_id and r.get('peer')==local_id and isinstance(r.get('at_unix'),( int,float)) and _now_t-r['at_unix']<=_circ_window_s]
   if _reverse_transfers:
    exchange.append_audit_row({'kind': 'WASH_TRADE_BLOCKED', 'sender': local_id, 'attempted_receiver': args.peer_id, 'amount_units': args.amount_units, 'reverse_transfer_at_unix': float(_reverse_transfers[0].get('at_unix', 0)), 'window_secs': _circ_window_s, 'at_unix': _now_t, 'at': datetime.now(timezone.utc).isoformat(), 'auditable': True, 'note': 'Circular transfer blocked: reverse transfer detected within wash window'})
    raise ValueError('circular transfer detected — potential wash cycle')
   # Large-transfer flag: emit WARNING gap event but allow
   _large_flag_thresh=config.get('p2p',{}).get('large_transfer_flag_threshold',500)
   if args.amount_units>_large_flag_thresh:
    exchange.append_audit_row({'kind':'GAP','severity':'WARNING','gap_type':'large-transfer-flagged','peer':args.peer_id,'local_peer':local_id,'amount_units':args.amount_units,'at_unix':_now_t,'at':datetime.now(timezone.utc).isoformat()})
   import hashlib as _hl,json as _jj
   _new_row={'kind':'CREDIT_DELTA','direction':'send','peer':args.peer_id,'local_peer':local_id,'amount_units':args.amount_units,'reason':'manual_transfer','at_unix':_t.time(),'at':datetime.now(timezone.utc).isoformat(),'sender_peer_id':local_id,'receiver_peer_id':args.peer_id,'auditable':True,'wash_window_secs':_circ_window_s}
   # PoQ ledger block chaining: on by default for transfers (sha256 overhead is negligible; tamper evidence)
   if config.get('p2p',{}).get('ledger_block_mode',True):
    _prev_rows=[r for r in _audit_rows if r.get('previous_hash') is not None or r.get('kind')=='CREDIT_DELTA']
    _prev_entry=_prev_rows[-1] if _prev_rows else None
    _prev_hash=_hl.sha256(_jj.dumps(_prev_entry,sort_keys=True,default=str).encode()).hexdigest() if _prev_entry else '0'*64
    _new_row['previous_hash']=_prev_hash
   exchange.append_audit_row(_new_row)
   result={'status':'transferred','to':args.peer_id,'amount_units':args.amount_units}
   if not exchange.load().get('crypto_network'):result['crypto_network_note']='Token settlement over blockchain is CRYPTO_PENDING — tokens are reputation scores in closed network until crypto_network is configured'
  else:result={'peer':args.peer_id,'history':cl_history(exchange.root,args.peer_id,args.limit)}
 elif group=='bundle':
  if verb=='prepare':result=exchange.prepare(args.peer_id,args.feature_id,bounded_file(args.file,pe.LIMIT//2,True),args.reviewed)
  elif verb=='inspect':result=exchange.inspect(args.bundle_id)
  elif verb=='send':result=pe.send(exchange,args.bundle_id)
  elif verb=='evaluate':
   from ._common import SYSTEM_ROOT
   import sys
   sys.path.insert(0,str(SYSTEM_ROOT/'trial'))
   from peer_runtime import enqueue
   result=enqueue(SYSTEM_ROOT/'trial',args.bundle_id)
  elif verb=='import':result=exchange.receive(json.loads(bounded_file(args.file,pe.LIMIT)))
  elif verb=='manifest':
   from ._common import SYSTEM_ROOT
   import sys as _sys
   _sys.path.insert(0,str(SYSTEM_ROOT/'trial'))
   import runtime_evaluation as _ev
   receipt=_ev.load_receipt(SYSTEM_ROOT/'trial',args.baseline_evaluation_id,public=True)
   result=pe.request(exchange,args.peer_id,'exchange.manifest',{'baseline_engine_sha256':receipt['engine_sha256'],'observed_failures':[c for c,p in receipt['case_results'].items() if not p]+args.failures,'session_start_unix':__import__('time').time()})
  elif verb=='fetch-artifact':
   _fa_rec=exchange.inspect(args.bundle_id)
   _fa_sha=_fa_rec.get('bundle',{}).get('payload',{}).get('artifact_ref') or _fa_rec.get('bundle',{}).get('payload',{}).get('sha256','')
   _fa_size=_fa_rec.get('artifact_size_bytes',0)
   _fa_stored=_fa_rec.get('artifact_stored',False)
   if not _fa_sha:raise ValueError(f'Bundle {args.bundle_id!r} has no artifact reference')
   if getattr(args,'out_path',None):
    _fa_bytes=exchange.artifact_bytes(_fa_sha)
    if _fa_bytes is None:raise ValueError(f'Artifact {_fa_sha[:16]}... not in local store — request from peer first')
    import pathlib as _fap
    _fap.Path(args.out_path).write_bytes(_fa_bytes)
    result={'status':'written','sha256':_fa_sha,'size_bytes':len(_fa_bytes),'path':args.out_path}
   else:
    result={'sha256':_fa_sha,'size_bytes':_fa_size,'stored_locally':_fa_stored,'bundle_id':args.bundle_id}
  else:result=exchange.review(args.bundle_id,args.review_status,args.note)
 elif group=='chunk':
  from .chunk_store import ChunkStore as _CS
  _cs=_CS(exchange.root)
  if verb=='status':
   _cs_mf=_cs.manifest(args.artifact_sha256)
   if _cs_mf is None:result={'artifact_sha256':args.artifact_sha256,'stored':False}
   else:result={'artifact_sha256':args.artifact_sha256,'stored':True,'n_data':_cs_mf['n_data'],'n_total':_cs_mf['n_total'],'chunks_held':_cs.has_chunks(args.artifact_sha256),'is_reconstructable':_cs.is_reconstructable(args.artifact_sha256),'artifact_size_bytes':_cs_mf.get('artifact_size_bytes',0)}
  elif verb=='store':
   import pathlib as _csp
   _cs_raw=_csp.Path(args.input_path).read_bytes()
   import hashlib as _csh
   _cs_actual=_csh.sha256(_cs_raw).hexdigest()
   if _cs_actual!=args.artifact_sha256:raise ValueError(f'SHA256 mismatch: file={_cs_actual}, expected={args.artifact_sha256}')
   _cs_mf2=_cs.store(args.artifact_sha256,_cs_raw)
   result={'status':'stored','artifact_sha256':args.artifact_sha256,'n_total':_cs_mf2['n_total'],'size_bytes':len(_cs_raw)}
  elif verb=='find-holders':
   _rt2=exchange.routing_table()
   _holders=[{'peer_id':n.peer_id,'endpoint':n.endpoint,'last_seen':n.last_seen} for n in _rt2.chunk_holders(args.artifact_sha256,args.chunk_idx)]
   result={'artifact_sha256':args.artifact_sha256,'chunk_idx':args.chunk_idx,'closest_peers':_holders,'routing_table_size':_rt2.size(),'note':'Peers closest to chunk routing key; actual holder confirmation requires network RPC (v3 stub)'}
 elif group=='market':
  if verb=='stats':
   def _escrow_stats(exchange, rows, window_sec, now_unix):
    import time as _te
    from . import peer_work_market as _pwm
    try:
     all_reqs = _pwm.list_requests(exchange)
    except Exception:
     all_reqs = []
    active = [r for r in all_reqs if r.get('state') in ('OPEN','ACCEPTED')]
    pending_units = sum(int(r.get('budget_units',0)) for r in active if r.get('state')=='ACCEPTED')
    completed_window = [r for r in all_reqs if r.get('state')=='COMPLETED' and r.get('completed_at_unix',0)>now_unix-window_sec]
    p2p_cfg = exchange.load()
    peers_map = p2p_cfg.get('peers',{})
    # Peers capable of escrow: pinned, unblocked, with evidence of work activity
    workers = {r.get('assigned_peer') for r in all_reqs if r.get('assigned_peer')}
    known_unblocked = [pid for pid,v in peers_map.items() if not v.get('blocked')]
    escrow_capable_estimate = max(len(workers), len(known_unblocked))
    return {
     'active_escrows': len(active),
     'pending_settlement_units': pending_units,
     'completed_in_window': len(completed_window),
     'escrow_capable_peers_estimate': escrow_capable_estimate,
     'note': 'escrow_capable_peers_estimate counts unblocked pinned peers; actual escrow capability requires token balance and mutual rules',
    }
   import time as _t
   from . import ledger_compaction as _lc
   from .credit_ledger import summary as cl_summary
   window_hours = getattr(args, 'window_hours', 24)
   window_sec = window_hours * 3600
   now_unix = _t.time()
   rows = exchange.audit_rows()
   # Velocity: events in window
   recent = [r for r in rows if r.get('at_unix', 0) > now_unix - window_sec]
   mint_events = [r for r in recent if r.get('kind') == 'QUALIFY_RECEIPT']
   # Trend: compare current window vs prior window
   prior_start = now_unix - 2 * window_sec
   prior = [r for r in rows if prior_start < r.get('at_unix', 0) <= now_unix - window_sec]
   prior_mints = len([r for r in prior if r.get('kind') == 'QUALIFY_RECEIPT'])
   curr_mints = len(mint_events)
   if prior_mints == 0:
    trend = 'accelerating' if curr_mints > 0 else 'stable'
    trend_delta = 100.0 if curr_mints > 0 else 0.0
   else:
    delta_pct = (curr_mints - prior_mints) / prior_mints * 100
    trend = 'accelerating' if delta_pct > 10 else ('decelerating' if delta_pct < -10 else 'stable')
    trend_delta = round(delta_pct, 1)
   burn_events = [r for r in recent if r.get('kind') == 'CREDIT_DELTA' and r.get('direction') in ('spend', 'burn', 'send') or (r.get('kind') == 'CREDIT_DELTA' and int(r.get('amount_units', 0)) < 0)]
   equity_sells = [r for r in recent if r.get('kind') == 'EQUITY_SELL']
   work_released = [r for r in recent if r.get('kind') == 'WORK_RELEASED']
   # Supply stats
   supply_summary = cl_summary(exchange.root)
   total_peers = len(supply_summary.get('peers', {}))
   # Feature counts from initial ledger
   from ._common import SYSTEM_ROOT
   import json as _json
   _ledger_jsonl = SYSTEM_ROOT / 'exchange' / 'initial_ledger' / 'initial_ledger.jsonl'
   _ledger_json = SYSTEM_ROOT / 'exchange' / 'initial_ledger' / 'initial_ledger.json'
   total_features = 0
   if _ledger_jsonl.exists():
    lines = [l for l in _ledger_jsonl.read_text().splitlines() if l.strip()]
    if lines:
     try:
      header = _json.loads(lines[0])
      total_features = header.get('feature_count', len(lines) - 1)
     except Exception:
      total_features = len(lines) - 1
   elif _ledger_json.exists():
    try:
     total_features = len(_json.loads(_ledger_json.read_text()).get('features', []))
    except Exception:
     pass
   from . import ledger_compaction as _lc2
   revenue_fraction = 0.65
   revenue_features = max(1, int(total_features * revenue_fraction))
   free_features = total_features - revenue_features
   # Network size
   p2p_cfg = exchange.load()
   network_peer_count = len(p2p_cfg.get('peers', {}))
   result = {
    'status': 'ok',
    'window_hours': window_hours,
    'velocity': {
     'mint_events': len(mint_events),
     'burn_events': len(burn_events),
     'equity_sells': len(equity_sells),
     'work_released': len(work_released),
     'total_recent_events': len(recent),
     'trend': trend,
     'trend_delta_pct': trend_delta,
    },
    'supply': {
     'total_peers_with_balance': total_peers,
     'total_ledger_events': supply_summary.get('total_events', 0),
     'baseline_grant_units': supply_summary.get('baseline_grant_units', 0),
    },
    'features': {
     'total': total_features,
     'revenue_generating': revenue_features,
     'free_no_token_flow': free_features,
     'revenue_fraction': revenue_fraction,
    },
    'network': {
     'pinned_peers': network_peer_count,
     'exchange_enabled': p2p_cfg.get('enabled', False),
     'network_mode': p2p_cfg.get('network', False),
    },
    'escrow': _escrow_stats(exchange, rows, window_sec, now_unix),
   }
 elif group=='network':
  local_id=config.get('peer_id',exchange.identity().get('peer_id','local'))
  if verb=='refresh':
   from .peer_selection import refresh
   result=refresh(exchange,args.limit)
   if isinstance(result,dict):
    result['price_consensus']={'status':'NOT_COMPUTED','enforced':False,'reason':'No receipt-backed, task-matched executor cost observations are exchanged; reputation and market prices are not cost evidence.'}
  elif verb=='discover':
   _disc=pe.discover(exchange,args.seconds)
   # Annotate features with language tag if present
   _feat_cfg=exchange.load().get('features',{})
   if isinstance(_disc,dict) and 'features' in _disc:
    for _fd in _disc['features']:
     _fid=_fd.get('id') or _fd.get('feature_id') or _fd.get('name','')
     _flang=_feat_cfg.get(_fid,{}).get('language')
     if _flang:_fd['language']=_flang
   result=_disc
  elif verb=='probe':result=pe.request(exchange,args.peer_id,'exchange.info',{})
  elif verb=='assets':
   from .remote_assets import discover
   result=discover(exchange,query=args.query,peer_limit=args.peer_limit)
  elif verb=='fetch-asset':
   from .remote_assets import fetch_open_asset
   result=fetch_open_asset(exchange,args.peer_id,args.asset_id)
  elif verb=='consensus-status':
   import math,time as _t
   cfg=exchange.load()
   network_est=cfg.get('estimated_network_size',1)
   persistent_max=cfg.get('max_observed_network_size',network_est)
   effective=max(network_est,persistent_max)
   threshold=max(2,min(10,math.ceil(0.10*effective)))
   try:rows=exchange.audit_rows()
   except Exception:rows=[]
   mismatches=[r for r in rows if r.get('kind')=='P2P_CORPUS_MISMATCH']
   result={'consensus_threshold':threshold,'network_estimate':network_est,'persistent_max_observed':persistent_max,'total_mismatch_events':len(mismatches),'unique_remote_fingerprints':len({r.get('remote_fingerprint') for r in mismatches if r.get('remote_fingerprint')})}
  elif verb=='public-address':
   from . import stun_client as _stun
   _addr=_stun.get_public_address(getattr(args,'stun_host','stun.l.google.com'),getattr(args,'stun_port',19302))
   if _addr:result={**_addr,'status':'ok','note':'Register this address as a bootstrap peer endpoint to expose your node to the internet: urace exchange bootstrap add --address https://<ip>:<port>'}
   else:result={'status':'error','error':'STUN probe failed — check network connectivity or try a different STUN server'}
  elif verb=='disconnect':
   import time as _t
   cfg=exchange.load();until=_t.time()+args.duration_minutes*60
   cfg['network_disconnected_until']=until
   from ._common import atomic_write_json
   atomic_write_json(exchange.root/'policy.json',cfg)
   result={'status':'disconnected','reconnects_after_unix':until,'duration_minutes':args.duration_minutes}
  elif verb=='peers':
   import hashlib as _h
   rows=exchange.audit_rows()
   pinned=[r for r in rows if r.get('kind')=='PEER_ADDED' and not any(
    b.get('peer')==r.get('peer_id') and b.get('kind')=='PEER_BLOCKED'
    for b in rows)]
   count=len({r.get('peer_id') for r in pinned if r.get('peer_id')})
   anon_ids=[_h.sha256(r.get('peer_id','').encode()).hexdigest()[:12] for r in pinned[:20]]
   result={'peer_count':count,'note':'peer IDs are anonymized SHA-256 hashes — no raw identities exposed','privacy':'IP addresses and certificates never included in this output'}
   if args.detail:result['anonymized_peer_ids']=anon_ids
  elif verb=='size':
   cfg=exchange.load()
   est=cfg.get('estimated_network_size',cfg.get('max_observed_network_size',1))
   result={'estimated_network_size':est,'all_time_max_observed':cfg.get('max_observed_network_size',1),'note':'heuristic estimate from DHT gossip — not cryptographically precise','security_note':'exact network topology is never exposed; this is a statistical estimate','use_for':'supply-calc calibration and epoch adjustment'}
  elif verb=='routing-table':
   _rt=exchange.routing_table()
   _rt_nodes=[{'peer_id':n.peer_id,'endpoint':n.endpoint,'last_seen':n.last_seen} for b in _rt.buckets for n in b.nodes]
   result={'schema':'urace-kademlia-v1','own_peer_id':_rt.own_peer_id,'size':_rt.size(),'nodes':_rt_nodes}
  elif verb=='port-to-internet':
   _use_json=getattr(args,'json',False)
   _settings=exchange.load()
   analysis=_port_to_internet_analysis(exchange,_settings)
   if analysis['already_internet']:
    msg={'status':'already_internet','network_mode':analysis['network_mode']}
    print(json.dumps(msg) if _use_json else f"Already on {analysis['network_mode']} network. No action needed.")
    return 0
   if not analysis['stun_available']:
    msg={'status':'stun_unavailable','reason':'Could not resolve public address via STUN. Check network connectivity or configure manually.'}
    print(json.dumps(msg) if _use_json else f"Cannot port to internet: {msg['reason']}")
    return 1
   selected=_select_features_for_port(analysis,args)
   _pub=analysis['public_address'] or {}
   report={
    'public_address':analysis['public_address'],
    'features_to_port':selected,
    'features_skipped':[f for f in analysis['features'] if f not in selected],
    'recommended_mode':'hybrid',
    'steps':['Switch network mode to hybrid',f"Register bootstrap address: {_pub.get('ip')}:{_pub.get('port')}"]+[f"Mint feature {f['feature_id']} to public network" for f in selected],
   }
   if getattr(args,'dry_run',False):
    report['status']='dry_run'
    if _use_json:print(json.dumps(report,indent=2))
    else:_format_port_report(report)
    return 0
   if not getattr(args,'auto',False) and not _use_json:
    _format_port_report(report)
    try:confirm=input('\nProceed with porting to internet? [y/N] ').strip().lower()
    except(EOFError,KeyboardInterrupt):confirm='n'
    if confirm not in('y','yes'):print('Aborted. No changes made.');return 0
   # Execute: switch network mode to hybrid via policy.json
   from ._common import atomic_write_json
   _cfg2=exchange.load();_cfg2['network_mode']='hybrid'
   atomic_write_json(exchange.root/'policy.json',_cfg2)
   report['status']='applied'
   report['network_mode_set']='hybrid'
   print(json.dumps(report,indent=2) if _use_json else f"Ported to hybrid network.\nPublic address: {_pub.get('ip')}:{_pub.get('port')}\nFeatures queued for minting: {len(selected)}")
   return 0
  elif verb=='find-node':
   import time as _tfn
   exchange.append_audit_row({'kind':'FIND_NODE_REQUESTED','target_peer_id':args.target_peer_id,'requester_peer_id':local_id,'at_unix':_tfn.time(),'note':'v3 stub — Kademlia find_node RPC not yet wired to network transport'})
   result={'status':'stub','note':'v3 — Kademlia find_node network RPC not yet implemented; routing table lookup is local only'}
  elif verb=='shamir-deliver':
   import time as _tsd
   exchange.append_audit_row({'kind':'SHAMIR_DELIVER_REQUESTED','feature_id':args.feature_id,'holder_peer_id':args.holder_peer_id,'share_index':args.share_index,'requester_peer_id':local_id,'at_unix':_tsd.time()})
   result={'status':'stub','note':'v3 — Shamir share delivery RPC not yet implemented; share commitment recorded in LISTING_DEK_SHARE rows'}
  elif verb=='tail-sync':
   from . import ledger_sync as _ls
   result=_ls.request_tail_payload(exchange)
   result['status']='local_only'
   result['note']='v3 — cross-node tail sync RPC not yet implemented; returned local tail payload'
  else:
   if not 0<=args.port<=65535:raise ValueError('Port must be 0–65535')
   with pe.server(exchange,args.host,args.port) as server:
    with advertise(exchange,args.host,server.server_port):
     print(json.dumps({'status':'LISTENING','host':args.host,'port':server.server_port,'peer_id':exchange.identity()['peer_id']}),flush=True)
     with selection_worker(exchange):
      try:server.serve_forever(poll_interval=.5)
      except KeyboardInterrupt:pass
   return 0
 elif group=='work':
  from . import peer_work_market as _wm
  local_id=config.get('peer_id',exchange.identity().get('peer_id','local'))
  if verb=='list':
   rows=exchange.audit_rows()
   requests=[r for r in rows if r.get('kind')=='WORK_REQUEST']
   if getattr(args,'state',None):
    requests=[r for r in requests if _wm.escrow_state(r['request_id'],exchange)['state']==args.state]
   result={'work_requests':requests,'count':len(requests)}
  elif verb=='status':result=_wm.escrow_state(args.request_id,exchange)
  elif verb=='create':
   # Optional owner estimate bound; this does not prove economic savings.
   _ref_price=config.get('p2p',{}).get('executor_reference_price_per_unit',None)
   if _ref_price is not None and args.budget>_ref_price:raise ValueError('work budget exceeds configured executor reference estimate')
   result={'request_id':_wm.create_work_request(exchange,local_id,args.spec,args.budget,args.min_rep,args.nodes,complexity=args.complexity,work_mode=getattr(args,'work_mode','agora'),cohort_rep_floor=getattr(args,'cohort_rep_floor',0.5))}
  elif verb=='bid':
   # Bids are reputation scores, not prices; request budget is set at creation.
   _wm.submit_bid(exchange,args.request_id,local_id,args.combined_rep);result={'status':'bid_submitted'}
  elif verb=='accept':_wm.accept_bid(exchange,exchange.root,args.request_id,args.bidder_id);result={'status':'bid_accepted'}
  elif verb=='deliver':_wm.submit_delivery(exchange,args.request_id,local_id,args.delivery_hash);result={'status':'delivery_submitted'}
  elif verb=='verify':_wm.verify_delivery(exchange,exchange.root,args.request_id,local_id,args.approve,args.reason,args.dispute_kind);result={'status':'verified' if args.approve else 'disputed'}
  elif verb=='review':_wm.submit_peer_review(exchange,args.request_id,local_id,args.approve);result={'status':'review_submitted','quorum':_wm.quorum_reached(args.request_id,exchange)}
  elif verb=='merge':result=_wm.merge_work_requests(exchange,exchange.root,args.request_id,local_id,args.co_budget)
  elif verb=='arbitrate':result={'request_id':args.request_id,'arbitrators':_wm.select_arbitrators(exchange,args.request_id,args.n)}
  elif verb=='claim':_wm.claim_ownership(exchange,exchange.root,args.request_id,local_id,args.mint_value);result={'status':'ownership_claimed','request_id':args.request_id}
  elif verb=='decompose':result={'sub_requests':_wm.auto_decompose_request(exchange,local_id,args.spec,args.budget,args.complexity,exchange.root)}
  elif verb=='chain-root':result={'audit_chain_root':_wm.audit_chain_root(exchange)}
  else:raise ValueError(f'Unknown work verb: {verb!r}')
 elif group=='equity':
  from . import feature_equity as _fe
  local_id=config.get('peer_id',exchange.identity().get('peer_id','local'))
  from . import equity_auto_trade as _eat
  if verb=='holdings':result=_fe.equity_holdings(args.feature_id,exchange)
  elif verb=='grant':
   if not getattr(args,'creator_id',None):args.creator_id=local_id
   # Item 1: equity overwrite protection
   _audit_rows=exchange.audit_rows()
   _existing_grants=[r for r in _audit_rows if r.get('kind')=='EQUITY_GRANT' and r.get('feature_id')==args.feature_id]
   if _existing_grants:raise ValueError('Feature already has equity — use equity sell to transfer, not grant')
   _grant_meta={'description':getattr(args,'description',''),'tags':[t.strip() for t in (getattr(args,'tags','') or '').split(',') if t.strip()]}
   # Attach non-sensitive context snapshot if requested and permitted
   _ctx_kinds=[k.strip() for k in (getattr(args,'include_context',None) or '').split(',') if k.strip()]
   _PROTECTED_CTX={'authority','self_evolution_policy','config','executor','p2p','rule_ledger'}
   _ALLOWED_CTX={'objectives','operations','evidence','decisions','checkpoints','blockers'}
   if _ctx_kinds:
    # Check capability_flags.context_mint_enabled (default True if p2p_mint_enabled)
    _caps=config.get('capability_flags',{})
    if not _caps.get('context_mint_enabled',_caps.get('p2p_mint_enabled',False)):
     raise ValueError('Context minting is disabled; enable with: urace controls set --context-mint-enabled true')
    _safe_kinds=[k for k in _ctx_kinds if k in _ALLOWED_CTX and k not in _PROTECTED_CTX
                 and _caps.get(f'context_mint_{k}', False)]
    _blocked=[k for k in _ctx_kinds if k not in _safe_kinds]
    if _blocked:raise ValueError(
        f'Context kinds blocked (authority-protected, unknown, or per-kind flag disabled): {_blocked}. '
        f'Enable with: urace controls set --context-mint-<kind> true')
    # Load state for context snapshot
    try:
     from pathlib import Path as _PP
     import json as _jj
     _state_files=list((_PP(config.get('state_path','state')) if config.get('state_path') else _PP('state')).glob('*.json'))
     _state=_jj.loads(_state_files[0].read_text()) if _state_files else {}
    except Exception:_state={}
    _STATE_KEY_MAP={'objectives':'objectives','operations':'operations','evidence':'evidence','decisions':'decision_records','checkpoints':'checkpoints','blockers':'blockers'}
    _ctx_snapshot={}
    for _ck in _safe_kinds:
     _items=_state.get(_STATE_KEY_MAP.get(_ck,_ck),[])
     # Per-feature isolation: store as tagged isolated snapshot
     _ctx_snapshot[_ck]=_items if not getattr(args,'isolate_context',False) else {'isolated':True,'feature_id':args.feature_id,'items':_items}
    _grant_meta['context_snapshot']=_ctx_snapshot
    _grant_meta['context_kinds_included']=_safe_kinds
    _grant_meta['context_isolated']=bool(getattr(args,'isolate_context',False))
    # Item 2: PII warning for context snapshot
    if not getattr(args,'skip_pii_check',False):
     import re as _re,sys as _sys
     _PII_KEY_SIGNALS={'email','password','token','key','secret','ssn','phone'}
     _EMAIL_RE=_re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}')
     _pii_fields=[]
     def _scan_val(path,val):
      if isinstance(val,str):
       if _EMAIL_RE.search(val):_pii_fields.append(f'{path} (email-like value)')
      elif isinstance(val,dict):
       for k,v in val.items():
        _lk=str(k).lower()
        if any(sig in _lk for sig in _PII_KEY_SIGNALS):_pii_fields.append(f'{path}.{k} (key name)')
        _scan_val(f'{path}.{k}',v)
      elif isinstance(val,list):
       for i,v in enumerate(val):_scan_val(f'{path}[{i}]',v)
     for _ck2,_snap in _ctx_snapshot.items():_scan_val(_ck2,_snap)
     if _pii_fields:
      print(f'WARNING: possible PII detected in context snapshot — fields: {", ".join(_pii_fields[:10])}. Pass --skip-pii-check to suppress.',file=_sys.stderr)
   # spec_context (urace-peer-bundle-v1 optional field): behavior spec scaffolding for executor — reduces C2' spin cost
   _spec_ctx=getattr(args,'spec_context',None)
   if _spec_ctx is not None:_grant_meta['spec_context']=_spec_ctx
   # --- artifact intake + pre-grant composition detection ---
   _art_path=getattr(args,'artifact_path',None)
   _art_raw=None;_art_sha=None;_decomp_components=[];_decomp_weights={}
   if _art_path:
    import hashlib as _hlib,mimetypes as _mt2
    from pathlib import Path as _PP2
    _art_raw=_PP2(_art_path).read_bytes()
    if len(_art_raw)==0:raise ValueError('Empty artifact not allowed — asset must contain content')
    _art_sha=_hlib.sha256(_art_raw).hexdigest()
    _art_ct=_mt2.guess_type(_art_path)[0] or 'application/octet-stream'
    from .tokenomics import artifact_fingerprint as _afp_fn,bundle_decompose as _bdc,dhash_int as _dhi_m,hamming_distance as _hd_m,winnow_fingerprint as _wfp_m,winnow_similarity as _ws_m
    _art_fp=_afp_fn(_art_ct,_art_raw)
    # Fingerprint index: existing grants that stored artifact_fingerprint
    _fp_index={r['artifact_fingerprint']:r.get('feature_id','') for r in _audit_rows if r.get('kind')=='EQUITY_GRANT' and r.get('artifact_fingerprint','') and r.get('feature_id','')!=args.feature_id}
    # Per-member similarity indexes (for pack abuse detection)
    _dhash_index={r.get('feature_id',''): int(r['artifact_dhash_int']) for r in _audit_rows if r.get('kind')=='EQUITY_GRANT' and r.get('artifact_dhash_int') is not None and r.get('feature_id','')!=args.feature_id}
    _winnow_index={r.get('feature_id',''): frozenset(r['artifact_winnow_fp']) for r in _audit_rows if r.get('kind')=='EQUITY_GRANT' and r.get('artifact_winnow_fp') and r.get('feature_id','')!=args.feature_id}
    # Decompose bundle members
    _members=_bdc(_art_raw)
    _total_bundle_size=max(1,sum(len(_mb) for _,_mb,_ in _members))
    _comp_size_acc: dict={}
    _PACK_HAMMING=10;_PACK_WINNOW=0.60
    for _mname,_mbytes,_mct in _members:
     if len(_mbytes)==0:continue  # skip empty members
     _mfp=_afp_fn(_mct,_mbytes)
     if _mfp in _fp_index:
      # Layer 1: exact member match
      _fid2=_fp_index[_mfp]
      _decomp_components.append(_fid2)
      _comp_size_acc[_fid2]=_comp_size_acc.get(_fid2,0)+len(_mbytes)
     else:
      # Layer 2+3: per-member similarity against all known features (pack abuse detection)
      # This catches dilution attacks where each stolen file is <60% of whole bundle
      _mbest_fid='';_mbest_sim=0.0
      if _mct.startswith('image/'):
       _mdhi=_dhi_m(_mbytes)
       if _mdhi is not None:
        for _fid3,_fdhi in _dhash_index.items():
         if _hd_m(_mdhi,_fdhi)<=_PACK_HAMMING and _fid3 not in _decomp_components:
          _mbest_fid=_fid3;_mbest_sim=1.0;break
      else:
       _mwfp=_wfp_m(_mbytes)
       if _mwfp:
        for _fid3,_fwfp in _winnow_index.items():
         _msim=_ws_m(_mwfp,_fwfp)
         if _msim>=_PACK_WINNOW and _msim>_mbest_sim:
          _mbest_fid=_fid3;_mbest_sim=_msim
      if _mbest_fid:
       _decomp_components.append(_mbest_fid)
       _comp_size_acc[_mbest_fid]=_comp_size_acc.get(_mbest_fid,0)+len(_mbytes)
    _decomp_components=list(dict.fromkeys(_decomp_components))
    # Compute size-based weights for each matched component
    for _fid2 in _decomp_components:
     _decomp_weights[_fid2]=_comp_size_acc.get(_fid2,0)/_total_bundle_size
    # Block zero-novelty packs: >95% from known sources with no original content
    _total_known_weight=sum(_decomp_weights.values())
    if _total_known_weight>0.95 and len(_decomp_components)>0:
     raise ValueError(f'Pack contains no original content ({_total_known_weight*100:.0f}% from {len(_decomp_components)} existing feature(s)). Reference or fork those features instead of re-minting.')
    # Block exact re-mint: entire artifact matches a single existing feature
    if len(_members)==1 and _art_fp in _fp_index:
     raise ValueError(f'Artifact is identical to existing feature {_fp_index[_art_fp]!r} — cannot re-mint. Reference that feature instead.')
    # Add artifact fields to grant row
    _grant_meta['artifact_ref']=_art_sha
    _grant_meta['artifact_fingerprint']=_art_fp
    _grant_meta['artifact_size_bytes']=len(_art_raw)
    _grant_meta['content_type']=_art_ct
    # Store raw similarity data for future near-similar detection
    if _art_ct.startswith('image/'):
     from .tokenomics import dhash_int as _dhi
     _dhi_val=_dhi(_art_raw)
     if _dhi_val is not None:_grant_meta['artifact_dhash_int']=_dhi_val
    elif _art_ct.startswith('text/') or _art_ct in ('application/javascript','application/x-python','application/json'):
     from .tokenomics import winnow_fingerprint as _wfp
     _wfp_set=_wfp(_art_raw)
     if _wfp_set:_grant_meta['artifact_winnow_fp']=sorted(_wfp_set)  # list for JSON serialization
   # MIME type policy enforcement (ALE network guarantee)
   if _art_path:
    from . import mime_policy as _mp
    _mime_allowed,_mime_reason=_mp.is_allowed(_art_ct,config)
    if not _mime_allowed:
     raise ValueError(f'Asset MIME type {_art_ct!r} rejected by node MIME policy: {_mime_reason}. Configure p2p.mime_policy or p2p.allowed_asset_mime_types to override.')
    _grant_meta['ale_protection_level']=_mp.protection_level(_art_ct)
   # Asset quality validation (non-blocking warning)
   if _art_path and _art_raw is not None:
    from . import mime_validator as _mv
    _qc_ok,_qc_reason=_mv.validate_asset(_art_raw,_art_ct)
    if not _qc_ok:
     exchange.append_audit_row({'kind':'GAP','severity':'WARNING','gap_type':'asset_quality_check_failed','feature_id':args.feature_id,'content_type':_art_ct,'quality_reason':_qc_reason,'at_unix':_time_mod.time(),'at':datetime.now(timezone.utc).isoformat()})
    _grant_meta['quality_check']=_qc_reason if not _qc_ok else 'pass'
   elif _art_path is None:
    _grant_meta['quality_check']='pass'
   _grant_meta['visibility']=getattr(args,'visibility','public') or 'public'
   # Description/metadata similarity check: catch description copying (lower threshold, warning only)
   _desc_text=((_grant_meta.get('description','') or '')+' '+(_grant_meta.get('spec_context','') or '')).strip()
   if len(_desc_text)>80:  # only meaningful if description is substantial
    try:
     from .tokenomics import winnow_fingerprint as _wfp_desc,winnow_similarity as _ws_desc
     _desc_wfp=_wfp_desc(_desc_text.encode())
     if _desc_wfp:
      for _dsg in [r for r in _audit_rows if r.get('kind')=='EQUITY_GRANT' and r.get('feature_id','')!=args.feature_id and r.get('artifact_winnow_fp')]:
       _dsg_desc=((_dsg.get('description','') or '')+' '+(_dsg.get('spec_context','') or '')).strip()
       if len(_dsg_desc)>80:
        _dsg_dwfp=_wfp_desc(_dsg_desc.encode())
        if _dsg_dwfp:
         _dsim=_ws_desc(_desc_wfp,_dsg_dwfp)
         if _dsim>=0.40:  # lower threshold for text
          exchange.append_audit_row({'kind':'GAP','severity':'WARNING','gap_type':'description_similarity','feature_id':args.feature_id,'similar_to_feature':_dsg.get('feature_id',''),'similarity':round(_dsim,3),'at_unix':_time_mod.time(),'at':datetime.now(timezone.utc).isoformat(),'note':f'Feature description is {_dsim*100:.0f}% similar to existing feature — ensure this is an original description'})
    except Exception:pass
   _fe.grant_equity(exchange,args.feature_id,args.creator_id,**_grant_meta)
   if _art_raw and _art_sha:
    from .peer_exchange import _store_artifact as _sa
    _sa(exchange.root,_art_sha,_art_raw)
   if _decomp_components:
    import time as _tcomp
    exchange.append_audit_row({'kind':'FEATURE_COMPOSITION','composite_feature_id':args.feature_id,'component_feature_ids':_decomp_components,'component_weights':_decomp_weights,'creator_peer_id':args.creator_id,'auto_detected':True,'at_unix':_tcomp.time(),'at':datetime.now(timezone.utc).isoformat()})
   result={'status':'granted','creator':args.creator_id,'description':_grant_meta['description'],'tags':_grant_meta['tags'],'context_kinds':_grant_meta.get('context_kinds_included',[])}
   if _spec_ctx is not None:result['spec_context']=_spec_ctx
   if _decomp_components:result['composition_components']=_decomp_components
   # Auto-lock mint stake for provenance enforcement
   try:
    from . import provenance_stake as _ps
    _ps_cfg=config
    _ps_units=_ps.get_mint_stake_units(_ps_cfg)
    _ps_days=_ps.get_challenge_window_days(_ps_cfg)
    _ps.lock_mint_stake(exchange,args.feature_id,args.creator_id,_ps_units,_ps_days)
    result['mint_stake_locked']=_ps_units
    result['challenge_window_days']=_ps_days
    result['ale_protection_level']=_grant_meta.get('ale_protection_level','none')
   except ValueError as _ps_e:
    result['mint_stake_warning']=str(_ps_e)
   except Exception:pass
   # Near-duplicate artifact fingerprint check
   _new_grant_row = next((r for r in exchange.audit_rows() if r.get('kind') == 'EQUITY_GRANT' and r.get('feature_id') == args.feature_id), None)
   _grant_artifact_ref = _new_grant_row.get('artifact_ref', '') if isinstance(_new_grant_row, dict) else ''
   if _grant_artifact_ref:
    _raw_check = exchange.artifact_bytes(_grant_artifact_ref) if hasattr(exchange, 'artifact_bytes') else None
    if _raw_check:
     from .tokenomics import artifact_fingerprint as _afp_fn
     _all_equity_rows = exchange.audit_rows()
     _ct_check = _new_grant_row.get('content_type', 'application/octet-stream')
     _new_fp = _afp_fn(_ct_check, _raw_check)
     for _prior_grant in [r for r in _all_equity_rows if r.get('kind') == 'EQUITY_GRANT' and r.get('feature_id') != args.feature_id]:
      _prior_ref = _prior_grant.get('artifact_ref', '')
      if _prior_ref and _prior_ref != _grant_artifact_ref:
       _prior_raw = exchange.artifact_bytes(_prior_ref)
       if _prior_raw:
        _prior_fp = _afp_fn(_prior_grant.get('content_type', 'application/octet-stream'), _prior_raw)
        if _prior_fp == _new_fp:
         import time as _time_grant
         exchange.append_audit_row({'kind': 'GAP', 'severity': 'WARNING', 'gap_type': 'near-duplicate-artifact', 'feature_id': args.feature_id, 'similar_to_feature': _prior_grant.get('feature_id', ''), 'artifact_fingerprint': _new_fp, 'at_unix': _time_grant.time(), 'at': datetime.now(timezone.utc).isoformat(), 'note': 'Artifact is semantically similar to an existing feature — consider linking instead of minting a new feature'})
         # Upgrade: also emit provenance link so composition referral fires at borrow time
         _existing_comp = any(r.get('kind') == 'FEATURE_COMPOSITION' and r.get('composite_feature_id') == args.feature_id and _prior_grant.get('feature_id', '') in r.get('component_feature_ids', []) for r in exchange.audit_rows())
         if not _existing_comp:
          _l1_cid=_prior_grant.get('feature_id','')
          exchange.append_audit_row({'kind': 'FEATURE_COMPOSITION', 'composite_feature_id': args.feature_id, 'component_feature_ids': [_l1_cid], 'component_weights': {_l1_cid: 1.0}, 'creator_peer_id': args.creator_id, 'auto_detected': True, 'detection_method': 'exact_fingerprint', 'at_unix': _time_grant.time(), 'at': datetime.now(timezone.utc).isoformat()})
         break
   # Layer 2+3: similarity detection for non-exact matches (image Hamming, code Winnowing)
   if _art_raw and _art_ct:
    import time as _tsim
    from .tokenomics import dhash_int as _dhi2,hamming_distance as _hd,winnow_fingerprint as _wfp2,winnow_similarity as _ws
    _HAMMING_THRESHOLD=10
    _WINNOW_THRESHOLD=0.60
    _sim_checked_features=set()
    for _sg in [r for r in exchange.audit_rows() if r.get('kind')=='EQUITY_GRANT' and r.get('feature_id','')!=args.feature_id]:
     _sg_fid=_sg.get('feature_id','')
     if _sg_fid in _sim_checked_features:continue
     _detected=False;_method=''
     # Layer 2: image Hamming distance
     if _art_ct.startswith('image/') and _sg.get('artifact_dhash_int') is not None:
      _dist=_hd(int(_grant_meta.get('artifact_dhash_int',0)),int(_sg['artifact_dhash_int']))
      if _dist<=_HAMMING_THRESHOLD:_detected=True;_method=f'image_hamming_d{_dist}'
     # Layer 3: code/text Winnowing
     elif not _art_ct.startswith('image/') and _sg.get('artifact_winnow_fp'):
      _sg_wfp=frozenset(_sg['artifact_winnow_fp'])
      _new_wfp=_wfp2(_art_raw)
      _sim=_ws(_new_wfp,_sg_wfp)
      if _sim>=_WINNOW_THRESHOLD:_detected=True;_method=f'winnow_jaccard_{_sim:.2f}'
     if _detected:
      _sim_checked_features.add(_sg_fid)
      _already_comp=any(r.get('kind')=='FEATURE_COMPOSITION' and r.get('composite_feature_id')==args.feature_id and _sg_fid in r.get('component_feature_ids',[]) for r in exchange.audit_rows())
      if not _already_comp:
       exchange.append_audit_row({'kind':'FEATURE_COMPOSITION','composite_feature_id':args.feature_id,'component_feature_ids':[_sg_fid],'component_weights':{_sg_fid:1.0},'creator_peer_id':args.creator_id,'auto_detected':True,'detection_method':_method,'at_unix':_tsim.time(),'at':datetime.now(timezone.utc).isoformat()})
       exchange.append_audit_row({'kind':'GAP','severity':'WARNING','gap_type':'near-similar-asset','feature_id':args.feature_id,'similar_to_feature':_sg_fid,'detection_method':_method,'at_unix':_tsim.time(),'at':datetime.now(timezone.utc).isoformat(),'note':f'Asset is near-similar to existing feature {_sg_fid!r} (method: {_method}) — provenance linked, referral will apply at borrow time'})
    # Layer 4: request LLM-peer semantic similarity check (async, non-blocking)
    # LLM-peer executor sees SIMILARITY_CHECK_REQUESTED rows and responds with SIMILARITY_VERDICT
    # fill-listing checks SIMILARITY_VERDICT and emits FEATURE_COMPOSITION if confirmed
    if _art_ct.startswith('text/') or 'code' in _art_ct or 'python' in _art_ct or 'javascript' in _art_ct:
     _llm_candidates=[r.get('feature_id','') for r in exchange.audit_rows() if r.get('kind')=='EQUITY_GRANT' and r.get('feature_id','')!=args.feature_id and not r.get('artifact_dhash_int') and r.get('artifact_ref','')][:10]
     if _llm_candidates:
      exchange.append_audit_row({'kind':'SIMILARITY_CHECK_REQUESTED','feature_id':args.feature_id,'candidate_feature_ids':_llm_candidates,'artifact_ref':_grant_meta.get('artifact_ref',''),'at_unix':_tsim.time(),'at':datetime.now(timezone.utc).isoformat(),'note':'Semantic similarity check queued for LLM-peer executor — SIMILARITY_VERDICT response will trigger FEATURE_COMPOSITION if derived'})
  elif verb=='sell':_fe.sell_equity(exchange,exchange.root,args.feature_id,local_id,args.buyer_id,args.basis_points,args.price_units);result={'status':'sold','bp':args.basis_points,'to':args.buyer_id}
  elif verb=='price':
   from . import credit_ledger as _cl
   base=_cl.apply_borrow_cost()
   result={'feature_id':args.feature_id,'market_price':_cl.feature_market_price(args.feature_id,exchange,base)}
  elif verb=='transfers':
   rows=exchange.audit_rows()
   transfers=[r for r in rows if r.get('kind')=='EQUITY_SELL' and r.get('feature_id')==args.feature_id]
   grants=[r for r in rows if r.get('kind')=='EQUITY_GRANT' and r.get('feature_id')==args.feature_id]
   result={'feature_id':args.feature_id,'grants':grants,'transfers':transfers,'total_transfers':len(transfers)}
  elif verb=='list-for-sale':
   # Scaffolding completeness ceiling: max_price = executor_reference_price × completeness_score
   # completeness_score based on what bundle fields are populated (0.2 min → 1.0 full spec+tests)
   import time as _t3
   from . import cost_model as _cm_ls
   _ref_price_ls_config=config.get('p2p',{}).get('executor_reference_price_per_unit',None)
   # A marketplace ask/reward is not an executor cost baseline.
   _ref_price_ls=_ref_price_ls_config
   _ref_price_ls_source='explicit_config_estimate' if _ref_price_ls is not None else 'unknown'
   # Store configured inputs as estimates, never as an observed executor-cost oracle.
   _estimate_rows_ls=[r for r in exchange.audit_rows() if r.get('kind')=='EXECUTOR_COST_ESTIMATE_INPUT' and r.get('peer_id')==local_id and float(r.get('at_unix',0))>=_t3.time()-86400]
   if _ref_price_ls is not None and (not _estimate_rows_ls or _estimate_rows_ls[-1].get('estimate_units')!=_ref_price_ls):
    exchange.append_audit_row({'kind':'EXECUTOR_COST_ESTIMATE_INPUT','peer_id':local_id,'estimate_units':_ref_price_ls,'source':_ref_price_ls_source,'at_unix':_t3.time(),'at':datetime.now(timezone.utc).isoformat()})
   if not getattr(args,'basis_points',None):args.basis_points=10000
   if not getattr(args,'ask_price',None) and _ref_price_ls:
    # Compute completeness score early so we can use it for the default price
    _all_rows_ls0=exchange.audit_rows()
    _grant_row0=next((r for r in _all_rows_ls0 if r.get('kind')=='EQUITY_GRANT' and r.get('feature_id')==args.feature_id and r.get('peer_id')==local_id),None)
    _comp0=0.2
    if _grant_row0:
     if _grant_row0.get('description','').strip():_comp0+=0.1
     if _grant_row0.get('spec_context','').strip():_comp0+=0.2
     if _grant_row0.get('tags'):_comp0+=0.1
     if _grant_row0.get('artifact_ref','') or _grant_row0.get('artifact','').strip():_comp0+=0.3
    args.ask_price=max(1,int(_ref_price_ls*min(_comp0,1.0)))
   elif not getattr(args,'ask_price',None):
    args.ask_price=_cm_ls.minimum_viable_price(config)
   if _ref_price_ls is not None:
    _all_rows_ls=exchange.audit_rows()
    _grant_row=next((r for r in _all_rows_ls if r.get('kind')=='EQUITY_GRANT' and r.get('feature_id')==args.feature_id and r.get('peer_id')==local_id),None)
    # Completeness score: implementation artifact (actual code) is worth more than spec alone
    # Formula: P ≤ ref_price × completeness × (1-margin) - avg_saved_iterations × per_call_cost
    # Implementations skip avg N verification iterations → save N × per_call_cost → higher ceiling
    _completeness=0.2  # baseline: name+description always present
    _has_artifact=False
    _artifact_size_bytes=0
    if _grant_row:
     if _grant_row.get('description','').strip():_completeness+=0.1
     if _grant_row.get('spec_context','').strip():_completeness+=0.2
     if _grant_row.get('tags'):_completeness+=0.1
     if _grant_row.get('include_context'):_completeness+=0.1
     _art_ref=_grant_row.get('artifact_ref','')
     _art_inline=_grant_row.get('artifact','').strip()
     _artifact_size_bytes=int(_grant_row.get('artifact_size_bytes',0) or len(_art_inline.encode()) if _art_inline else 0)
     if _art_ref or _art_inline:_has_artifact=True;_completeness+=0.3
     if _artifact_size_bytes>102400:_completeness=min(1.0,_completeness+0.05)
    _completeness=min(_completeness,1.0)
    _margin=max(0.20,float(config.get('p2p',{}).get('price_margin_fraction',0.40)))
    # Iteration savings: verified implementation saves avg_saved_iterations executor calls
    _avg_saved_iter=float(config.get('p2p',{}).get('avg_saved_verification_iterations',2.0)) if _has_artifact else 0.0
    _per_call=float(config.get('p2p',{}).get('executor_per_call_cost',0)) if _has_artifact else 0.0
    _iter_savings=_avg_saved_iter*_per_call
    _gas_oh_ls=_cm_ls.estimate_gas_overhead(config)
    _ceiling=max(0,int(_ref_price_ls*_completeness*(1.0-_margin)-_iter_savings-_gas_oh_ls))
    if args.ask_price>_ceiling:raise ValueError(f'ask_price {args.ask_price} exceeds ceiling {_ceiling} (ref {_ref_price_ls} × completeness {_completeness:.2f} × {1.0-_margin:.2f} - iter_savings {_iter_savings:.0f} - gas {_gas_oh_ls:.0f}); add implementation artifact or spec_context to increase ceiling')
   # Fix 3: minimum viable price floor — auto-adjust up, never reject
   _min_price_ls=_cm_ls.minimum_viable_price(config,_artifact_size_bytes if '_artifact_size_bytes' in dir() else 0)
   if args.ask_price<_min_price_ls:
    _old_ask_ls=args.ask_price
    args.ask_price=_min_price_ls
    exchange.append_audit_row({'kind':'GAP','severity':'WARNING','gap_type':'price_below_production_cost','feature_id':args.feature_id,'peer':local_id,'original_ask':_old_ask_ls,'adjusted_ask':_min_price_ls,'at_unix':_t3.time(),'at':datetime.now(timezone.utc).isoformat(),'note':f'ask_price {_old_ask_ls} was below minimum viable price {_min_price_ls} (production+network+protocol costs); auto-adjusted upward'})
   # Fix 4: resale ceiling — if no explicit resale path, original listing ceiling applies
   # (EQUITY_SELL transfers are gated by sell_equity; resale inherits the ceiling from the original listing)
   # Soft warning: emit gap if creator is the only holder (replication to other peers requires network activity)
   _holdings=_fe.equity_holdings(args.feature_id,exchange)
   _other_holders=[pid for pid in _holdings if pid!=local_id and _holdings[pid]>0]
   if not _other_holders:
    exchange.append_audit_row({'kind':'GAP','severity':'WARNING','gap_type':'bundle-single-holder-risk','feature_id':args.feature_id,'peer':local_id,'at_unix':_t3.time(),'note':'Feature has no peer holders other than creator — consider replicating bundle before listing'})
   # Per-owner concentration warning: flag if this peer owns > 25% of all minted features
   _all_grants_ls = [r for r in _all_rows_ls if r.get('kind') == 'EQUITY_GRANT']
   _total_features_ls = len({r.get('feature_id') for r in _all_grants_ls if r.get('feature_id')})
   _owner_features_ls = len({r.get('feature_id') for r in _all_grants_ls if r.get('peer_id') == local_id and r.get('feature_id')})
   if _total_features_ls >= 10 and _owner_features_ls / max(_total_features_ls, 1) > 0.25:
    exchange.append_audit_row({'kind': 'GAP', 'severity': 'WARNING', 'gap_type': 'feature-concentration-risk', 'peer': local_id, 'owner_feature_count': _owner_features_ls, 'total_feature_count': _total_features_ls, 'concentration_pct': round(100 * _owner_features_ls / _total_features_ls, 1), 'at_unix': _t3.time(), 'note': f'Peer owns {round(100*_owner_features_ls/max(_total_features_ls,1),1)}% of all minted features — market concentration risk'})
   result={'listing_id':_eat.list_for_sale(exchange,args.feature_id,local_id,args.basis_points,args.ask_price,config=config)}
   # DEK escrow: record that creator holds the decryption key for this artifact
   _dek_grant_row=next((r for r in _all_rows_ls if r.get('kind')=='EQUITY_GRANT' and r.get('feature_id')==args.feature_id),None)
   _dek_art_ref=(_dek_grant_row.get('artifact_ref','') if _dek_grant_row else '') or ''
   if _dek_art_ref:
    exchange.append_audit_row({'kind':'LISTING_DEK_AVAILABLE','listing_id':result['listing_id'],'feature_id':args.feature_id,'artifact_sha256':_dek_art_ref,'holder_peer_id':local_id,'at_unix':_t3.time(),'at':datetime.now(timezone.utc).isoformat(),'note':'Creator holds artifact DEK; released to buyer on EQUITY_LISTING_FILLED'})
   # v3 Shamir: split DEK across replica holders when >= 2 replicas exist
   _replica_peers=[r.get('replica_peer_id','') for r in _all_rows_ls if r.get('kind')=='BUNDLE_REPLICA_REGISTERED' and r.get('feature_id')==args.feature_id and r.get('replica_peer_id','')]
   if _dek_art_ref and len(_replica_peers)>=2:
    try:
     from .shamir import split as _sss_split,share_commitment as _sss_sc
     from .chunk_store import get_artifact_dek as _get_dek
     _dek=_get_dek(exchange.root,_dek_art_ref)
     _k_sss=max(2,(len(_replica_peers)+1)//2)
     _shares_sss=_sss_split(_dek,_k_sss,len(_replica_peers))
     for (_x_sss,_sb_sss),_holder_sss in zip(_shares_sss,_replica_peers):
      exchange.append_audit_row({'kind':'LISTING_DEK_SHARE','listing_id':result['listing_id'],'feature_id':args.feature_id,'artifact_sha256':_dek_art_ref,'share_holder_peer_id':_holder_sss,'share_index':_x_sss,'share_commitment':_sss_sc(_sb_sss),'k_threshold':_k_sss,'n_total':len(_replica_peers),'at_unix':_t3.time(),'at':datetime.now(timezone.utc).isoformat()})
     result['dek_sharing']={'k':_k_sss,'n':len(_replica_peers),'shares_distributed':len(_replica_peers)}
    except Exception:pass
  elif verb=='listings':
   _all_listings=_eat.open_listings(exchange,getattr(args,'feature_id',None))
   _active_listings=[lst for lst in _all_listings if not _listing_expired(lst,config)]
   result={'listings':_active_listings}
  elif verb=='cancel-listing':_eat.cancel_listing(exchange,args.listing_id,local_id);result={'status':'cancelled','listing_id':args.listing_id}
  elif verb=='fill-listing':
   import sys as _sys3
   # Item 7: check for EQUITY_DEPRECATED before filling
   _fl_rows=exchange.audit_rows()
   _fl_listing=next((r for r in _fl_rows if r.get('kind')=='EQUITY_LISTING' and r.get('listing_id')==args.listing_id),None)
   if _fl_listing:
    _fl_feat=_fl_listing.get('feature_id','')
    _depr=[r for r in _fl_rows if r.get('kind')=='EQUITY_DEPRECATED' and r.get('feature_id')==_fl_feat]
    if _depr:raise ValueError(f'Feature {_fl_feat!r} is deprecated — no new borrows allowed')
    # Item 6: quality summary
    if not getattr(args,'skip_quality_check',False):
     _sell_hist=[r for r in _fl_rows if r.get('kind')=='EQUITY_LISTING_FILLED' and r.get('feature_id')==_fl_feat]
     if _sell_hist:
      _last_tx=max(_sell_hist,key=lambda r:float(r.get('at_unix',0)))
      print(f'Quality: feature {_fl_feat!r} — borrowed {len(_sell_hist)} time(s), last transacted at {_last_tx.get("at","unknown")}. Pass --skip-quality-check to suppress.',file=_sys3.stderr)
     else:
      print(f'Quality: feature {_fl_feat!r} — new feature, no borrow history. Pass --skip-quality-check to suppress.',file=_sys3.stderr)
    # Item 8: peer trust score
    if not getattr(args,'skip_trust_check',False):
     _seller=_fl_listing.get('seller_id','')
     if _seller:
      _seller_sells=[r for r in _fl_rows if r.get('kind')=='EQUITY_LISTING_FILLED' and r.get('seller_id')==_seller]
      _seller_all=[r for r in _fl_rows if r.get('kind')=='EQUITY_LISTING' and r.get('seller_id')==_seller]
      _score=len(_seller_sells)/len(_seller_all) if _seller_all else 1.0
      if _score<0.3:
       print(f'WARNING: seller {_seller!r} trust score {_score:.2f} < 0.3 (fill rate {len(_seller_sells)}/{len(_seller_all)}). Pass --skip-trust-check to suppress.',file=_sys3.stderr)
   # Item 5: spend confirmation threshold
   _fl_price=int(_fl_listing.get('ask_price_units',0)) if _fl_listing else 0
   _fl_thresh=config.get('p2p',{}).get('confirm_spend_threshold_units',0)
   if _fl_thresh>0 and _fl_price>_fl_thresh and not getattr(args,'yes',False):
    print(f'Purchase of {_fl_price} units exceeds confirmation threshold {_fl_thresh}. Add --yes to confirm.',file=_sys3.stderr);return 2
   # Block borrow of revoked features
   if _fl_listing:
    _fl_feat_check=_fl_listing.get('feature_id','')
    if _fl_feat_check:
     _revoked_check=any(r.get('kind')=='EQUITY_GRANT_REVOKED' and r.get('feature_id')==_fl_feat_check for r in exchange.audit_rows())
     if _revoked_check:raise ValueError(f'Feature {_fl_feat_check!r} equity grant has been revoked (provenance challenge upheld) — cannot borrow.')
   # Visibility enforcement
   if _fl_listing:
    _fl_vis_feat=_fl_listing.get('feature_id','')
    if _fl_vis_feat:
     _fl_grant_row=next((r for r in _fl_rows if r.get('kind')=='EQUITY_GRANT' and r.get('feature_id')==_fl_vis_feat),None)
     _fl_visibility=(_fl_grant_row.get('visibility','public') if _fl_grant_row else 'public') or 'public'
     _fl_creator=(_fl_grant_row.get('peer_id','') if _fl_grant_row else '') or ''
     if _fl_visibility=='private':
      if local_id!=_fl_creator:raise ValueError(f'Feature {_fl_vis_feat!r} is private — only creator {_fl_creator!r} can fill this listing')
     elif _fl_visibility=='org':
      _fl_buyer_org=local_id[:8] if len(local_id)>=8 else local_id
      _fl_creator_org=_fl_creator[:8] if len(_fl_creator)>=8 else _fl_creator
      if _fl_buyer_org!=_fl_creator_org:raise ValueError(f'Feature {_fl_vis_feat!r} is org-restricted — buyer {local_id!r} is not in the same org as creator {_fl_creator!r}')
   _eat.fill_listing(exchange,exchange.root,args.listing_id,local_id)
   import time as _tfl
   if _fl_listing:
    _feat_id=_fl_listing.get('feature_id','')
    _fl_all_rows=exchange.audit_rows()
    # Original creator is from EQUITY_GRANT (not necessarily the equity seller)
    _eq_grant_row=next((r for r in _fl_all_rows if r.get('kind')=='EQUITY_GRANT' and r.get('feature_id')==_feat_id),None)
    _seller_id=_fl_listing.get('seller_id') or _fl_listing.get('owner_id','')
    _original_creator=(_eq_grant_row.get('peer_id','') if _eq_grant_row else '') or _seller_id
    if _feat_id:
     # Delivery routing: multi-deliverer proportional fee distribution
     from . import delivery_graph as _dg
     from .chunk_store import DEFAULT_N_DATA as _dn,DEFAULT_N_PARITY as _dp
     _n_total_del=_dn+_dp
     _del_manifest=None
     try:
      from .chunk_store import ChunkStore as _CS2
      _del_manifest=_CS2(exchange.root).manifest(_art_ref if '_art_ref' in dir() else (_grant_row.get('artifact_ref','') if '_grant_row' in dir() else ''))
      if _del_manifest:_n_total_del=_del_manifest.get('n_total',_n_total_del)
     except Exception:pass
     _fee_alloc=_dg.delivery_fee_amounts(_feat_id,_fl_all_rows,_original_creator,_fl_price,float(config.get('p2p',{}).get('delivery_fee_fraction',0.10)),_n_total_del)
     _total_delivery_fee=sum(_fee_alloc.values())
     _deliverer=_original_creator  # for backward compat in result
     if _fee_alloc:
      _deliverer=max(_fee_alloc,key=_fee_alloc.get)  # primary deliverer = highest contributor
      for _del_peer,_del_units in _fee_alloc.items():
       exchange.append_audit_row({'kind':'DELIVERY_FEE','listing_id':args.listing_id,'feature_id':_feat_id,'deliverer_peer_id':_del_peer,'buyer_peer_id':local_id,'fee_units':_del_units,'chunk_fraction':round(_fee_alloc[_del_peer]/_total_delivery_fee,4) if _total_delivery_fee>0 else 1.0,'at_unix':_tfl.time(),'at':datetime.now(timezone.utc).isoformat()})
     _delivery_fee=_total_delivery_fee  # used below in composition referral pool
     # FEATURE_BORROWED always credits the original creator regardless of who delivered
     if _original_creator:
      # Compute network-size-aware credit amount at mint time (stored in row for audit integrity)
      from . import credit_ledger as _cl_fb
      _fl_cfg=exchange.load()
      _fl_net_size=max(int(_fl_cfg.get('estimated_network_size',1)),int(_fl_cfg.get('max_observed_network_size',1)),1)
      _prior_borrowers={r['borrower_peer_id'] for r in _fl_all_rows if r.get('kind')=='FEATURE_BORROWED' and r.get('feature_id')==_feat_id and r.get('borrower_peer_id')}
      _fl_adoption_rank=len(_prior_borrowers)+1
      _fl_loc=int(_eq_grant_row.get('loc',0)) if _eq_grant_row else 0
      _fl_dep=int(_eq_grant_row.get('dependency_count',0)) if _eq_grant_row else 0
      _fl_tests=int(_eq_grant_row.get('test_count',0)) if _eq_grant_row else 0
      _fl_total_supply=sum(int(r.get('credit_units',_cl_fb.UNIT)) for r in _fl_all_rows if r.get('kind')=='FEATURE_BORROWED' and r.get('receipt_verified',True))
      _fl_max_mint=_cl_fb.max_mintable_units(_fl_net_size)
      if local_id in _prior_borrowers:
       _fl_credit_units=0  # repeat borrow from same peer: no additional creator earn
      elif _fl_total_supply>=_fl_max_mint:
       _fl_credit_units=1  # governance ceiling hit: floor 1 base unit, never hard zero
      else:
       _fl_credit_units=_cl_fb.mint_per_adoption(loc=_fl_loc,dependency_count=_fl_dep,test_count=_fl_tests,adoption_rank=_fl_adoption_rank,network_size=_fl_net_size,estimated_network_size=_fl_net_size,total_network_supply=_fl_total_supply)
      exchange.append_audit_row({'kind':'FEATURE_BORROWED','feature_id':_feat_id,'creator_peer_id':_original_creator,'borrower_peer_id':local_id,'listing_id':args.listing_id,'outcome_delta':0.0,'receipt_verified':True,'delivered_by':_deliverer,'credit_units':_fl_credit_units,'adoption_rank':_fl_adoption_rank,'estimated_network_size':_fl_net_size,'at_unix':_tfl.time(),'at':datetime.now(timezone.utc).isoformat()})
     from . import cost_model as _cm
     _pe_cmp=_cm.vs_executor_comparison(config,_fl_price)
     exchange.append_audit_row({'kind':'PRICING_EFFICIENCY','feature_id':_feat_id,'listing_id':args.listing_id,'ask_price_units':_fl_price,'executor_reference_price':None,'net_saving':None,'cheaper_than_executor':None,'comparison_status':'UNQUALIFIED_MISSING_TASK_RECEIPTS','at_unix':_tfl.time(),'at':datetime.now(timezone.utc).isoformat()})
     result['pricing_efficiency']=_pe_cmp
     # Dynamic composition referral: proportional to provenance weights (multi-level)
     _comp_fc=[r for r in _fl_all_rows if r.get('kind')=='FEATURE_COMPOSITION' and r.get('composite_feature_id')==_feat_id]
     if _comp_fc and _fl_price>0:
      from . import provenance_graph as _pg
      _ref_rate=float(config.get('p2p',{}).get('composition_referral_rate',0.20))
      _delivery=_delivery_fee if (_deliverer and _deliverer!=_original_creator) else 0
      _net_price=max(0,_fl_price-_delivery)
      _pool=int(_net_price*min(_ref_rate,0.50))
      if _pool>0:
       _prov_alloc=_pg.composition_referral_amounts(_feat_id,_fl_all_rows,_pool)
       for _rpeer,_runits in _prov_alloc.items():
        if _rpeer and _runits>0:
         exchange.append_audit_row({'kind':'CREDIT_DELTA','direction':'composition_referral','peer':_rpeer,'local_peer':local_id,'amount_units':_runits,'composite_feature_id':_feat_id,'listing_id':args.listing_id,'at_unix':_tfl.time(),'at':datetime.now(timezone.utc).isoformat()})
     # Layer 4: apply any pending LLM-peer SIMILARITY_VERDICT rows
     _verdict_rows=[r for r in _fl_all_rows if r.get('kind')=='SIMILARITY_VERDICT' and r.get('feature_id')==_feat_id and r.get('verdict')=='derived' and r.get('reference_feature_id','')]
     _llm_peer_rewarded=set()
     for _vr in _verdict_rows:
      _vr_ref=_vr.get('reference_feature_id','')
      _already_vcomp=any(r.get('kind')=='FEATURE_COMPOSITION' and r.get('composite_feature_id')==_feat_id and _vr_ref in r.get('component_feature_ids',[]) for r in _fl_all_rows)
      if not _already_vcomp:
       exchange.append_audit_row({'kind':'FEATURE_COMPOSITION','composite_feature_id':_feat_id,'component_feature_ids':[_vr_ref],'creator_peer_id':_original_creator,'auto_detected':True,'detection_method':'llm_peer_semantic','at_unix':_tfl.time(),'at':datetime.now(timezone.utc).isoformat()})
      # Maintainer reward: LLM peer earns for running similarity check work
      _llm_checker=_vr.get('checker_peer_id','') or _vr.get('peer_id','')
      _llm_reward=int(config.get('p2p',{}).get('llm_peer_reward_units',2))
      if _llm_checker and _llm_reward>0 and _llm_checker not in _llm_peer_rewarded:
       exchange.append_audit_row({'kind':'CREDIT_DELTA','direction':'llm_peer_reward','peer':_llm_checker,'amount_units':_llm_reward,'feature_id':_feat_id,'check_id':_vr.get('check_id',''),'reason':'similarity_verdict','at_unix':_tfl.time(),'at':datetime.now(timezone.utc).isoformat()})
       _llm_peer_rewarded.add(_llm_checker)
     # Fix 5: protocol fee — funds treasury that covers seal_reward + llm_peer_reward emissions
     _proto_fee=int(_fl_price*float(config.get('p2p',{}).get('protocol_fee_fraction',0.02)))
     if _proto_fee>0:
      exchange.append_audit_row({'kind':'CREDIT_DELTA','direction':'protocol_fee','peer':'__protocol__','amount_units':_proto_fee,'listing_id':args.listing_id,'feature_id':_feat_id,'funded_by':local_id,'at_unix':_tfl.time(),'at':datetime.now(timezone.utc).isoformat()})
   # DEK grant: creator issues session-bound artifact decryption key to buyer after EQUITY_LISTING_FILLED
   _dek_escrow=next((r for r in _fl_all_rows if r.get('kind')=='LISTING_DEK_AVAILABLE' and r.get('listing_id')==args.listing_id),None)
   if _dek_escrow and _feat_id:
    from . import session_dek as _sdek
    _buyer_priv_pem,_buyer_pub_pem=_sdek.generate_buyer_keypair()
    _buyer_priv_hex=_buyer_priv_pem.hex()
    _buyer_pub_hex=_buyer_pub_pem.hex()
    _art_sha=_dek_escrow.get('artifact_sha256','')
    _wrapped_dek_hex=''
    try:
     from .chunk_store import get_artifact_dek as _get_dek2
     _raw_dek=_get_dek2(exchange.root,_art_sha)
     _wrapped=_sdek.wrap_dek(_raw_dek,_buyer_pub_pem)
     _wrapped_dek_hex=_wrapped.hex()
    except Exception:pass
    _grant_row_data={'kind':'ARTIFACT_KEY_GRANT','listing_id':args.listing_id,'feature_id':_feat_id,'artifact_sha256':_art_sha,'grantee_peer_id':local_id,'grantor_peer_id':_original_creator,'buyer_pubkey_hex':_buyer_pub_hex,'at_unix':_tfl.time(),'at':datetime.now(timezone.utc).isoformat(),'note':'DEK released to buyer after EQUITY_LISTING_FILLED; buyer can decrypt artifact chunks'}
    if _wrapped_dek_hex:_grant_row_data['wrapped_dek_hex']=_wrapped_dek_hex
    exchange.append_audit_row(_grant_row_data)
    result_dek_info={'buyer_private_key_hex':_buyer_priv_hex,'buyer_public_key_hex':_buyer_pub_hex,'wrapped_dek_available':bool(_wrapped_dek_hex)}
   else:
    result_dek_info={}
   result={'status':'filled','listing_id':args.listing_id,'delivered_by':(_deliverer if _fl_listing and _feat_id else ''),'dek_info':result_dek_info}
  elif verb=='deprecate':
   import time as _tdep
   from datetime import datetime as _dtdep,timezone as _tzdep
   _dep_rows=exchange.audit_rows()
   _already=[r for r in _dep_rows if r.get('kind')=='EQUITY_DEPRECATED' and r.get('feature_id')==args.feature_id]
   if _already:raise ValueError(f'Feature {args.feature_id!r} is already deprecated')
   exchange.append_audit_row({'kind':'EQUITY_DEPRECATED','feature_id':args.feature_id,'creator_id':args.creator_id,'reason':getattr(args,'reason',''),'at_unix':_tdep.time(),'at':_dtdep.now(_tzdep.utc).isoformat()})
   result={'status':'deprecated','feature_id':args.feature_id,'creator_id':args.creator_id,'reason':getattr(args,'reason','')}
  elif verb=='register-replica':
   import time as _trep
   from datetime import datetime as _dtrep,timezone as _tzrep
   _rep_rows=exchange.audit_rows()
   _has_grant=any(r.get('kind')=='EQUITY_GRANT' and r.get('feature_id')==args.feature_id for r in _rep_rows)
   if not _has_grant:raise ValueError(f'Feature {args.feature_id!r} has no equity grant — register equity first')
   _already_rep=any(r.get('kind')=='BUNDLE_REPLICA_REGISTERED' and r.get('feature_id')==args.feature_id and r.get('replica_peer_id')==local_id for r in _rep_rows)
   if _already_rep:result={'status':'already_registered','feature_id':args.feature_id,'replica_peer_id':local_id}
   else:
    try:
     from . import cartel_guard as _cg
     _cg.register_replica_guard(exchange,args.feature_id,local_id,chunk_indices=getattr(args,'chunk_indices',None))
    except ValueError as _cg_err:
     exchange.append_audit_row({'kind':'GAP','severity':'WARNING','gap_type':'cartel_chunk_concentration','feature_id':args.feature_id,'replica_peer_id':local_id,'at_unix':_trep.time(),'at':_dtrep.now(_tzrep.utc).isoformat(),'note':str(_cg_err)})
    except Exception:pass
    exchange.append_audit_row({'kind':'BUNDLE_REPLICA_REGISTERED','feature_id':args.feature_id,'replica_peer_id':local_id,'artifact_hash':getattr(args,'artifact_hash',''),'chunk_indices':getattr(args,'chunk_indices',''),'at_unix':_trep.time(),'at':_dtrep.now(_tzrep.utc).isoformat()})
    try:
     from . import cartel_guard as _cg2
     _cg2.apply_chunk_concentration_penalty(exchange,args.feature_id)
    except Exception:pass
    result={'status':'registered','feature_id':args.feature_id,'replica_peer_id':local_id}
    try:
     from . import mime_priority as _mpr
     _mpr.emit_mime_calibration_event(exchange)
    except Exception:pass
  elif verb=='auto-buy':
   cfg=_eat.load_config(str(exchange.root));result=_eat.auto_buy(exchange,str(exchange.root),local_id,cfg)
  elif verb=='auto-sell':
   cfg=_eat.load_config(str(exchange.root));result=_eat.auto_sell(exchange,str(exchange.root),local_id,cfg)
  elif verb=='trade-config':
   tv=getattr(args,'trade_verb',None)
   if tv=='show':result=_eat.load_config(str(exchange.root))
   elif tv=='show-presets':
    result={'presets':{name:{'description':p.get('description',''),'roi_preference':p.get('roi_preference',''),'auto_buy':p.get('auto_buy',{}),'auto_sell':p.get('auto_sell',{})} for name,p in _eat.AUTO_CONFIG_PRESETS.items()}}
   elif tv=='set':
    cfg=_eat.load_config(str(exchange.root))
    # --roi-preference: map to preset name
    _preset_name=getattr(args,'preset',None)
    _roi_pref=getattr(args,'roi_preference',None)
    if _roi_pref and not _preset_name:
     _roi_map={p.get('roi_preference'):n for n,p in _eat.AUTO_CONFIG_PRESETS.items()}
     _preset_name=_roi_map.get(_roi_pref)
     if not _preset_name:raise ValueError(f'No preset found for roi_preference={_roi_pref!r}')
    # --preset: apply named preset first, then apply individual overrides on top
    if _preset_name:cfg=_eat.apply_preset(cfg,_preset_name)
    # --auto-tune: derive optimal settings from network conditions
    if getattr(args,'auto_tune',False):cfg=_eat.auto_tune_config(exchange,cfg)
    buy_keys={'min_quality_wilson','min_adoption_count','max_price_multiplier','max_bp_per_feature','max_spend_per_run_units','max_adoption_rate','min_supply_pressure','min_remaining_adopters','min_lucrativity_score','lucrativity_window_days'}
    sell_keys={'min_return_multiplier','bp_to_sell_per_trigger','min_hold_bp_to_trigger','sell_on_near_depleted','sell_on_slowing'}
    if getattr(args,'auto_buy_enabled',None) is not None:cfg['auto_buy']['enabled']=args.auto_buy_enabled
    if getattr(args,'auto_sell_enabled',None) is not None:cfg['auto_sell']['enabled']=args.auto_sell_enabled
    for key in buy_keys:
     v=getattr(args,key,None)
     if v is not None:cfg['auto_buy'][key]=v
    for key in sell_keys:
     v=getattr(args,key,None)
     if v is not None:cfg['auto_sell'][key]=v
    _eat.save_config(str(exchange.root),cfg);result=cfg
   else:raise ValueError(f'Unknown trade-config verb: {tv!r}')
  elif verb=='challenge':
   from . import provenance_stake as _ps
   _ch_stake=getattr(args,'challenger_stake',None) or int(config.get('p2p',{}).get('challenger_stake_units',_ps.CHALLENGER_STAKE_DEFAULT))
   result=_ps.file_challenge(exchange,args.feature_id,args.challenger_id,getattr(args,'evidence',''),getattr(args,'reference_feature_id',''),_ch_stake)
  elif verb=='resolve-challenge':
   from . import provenance_stake as _ps
   result=_ps.resolve_challenge(exchange,args.challenge_id,args.verdict,getattr(args,'resolver_id','local'))
  elif verb=='release-stake':
   from . import provenance_stake as _ps
   released=_ps.release_mint_stake(exchange,args.feature_id)
   result={'status':'released' if released else 'already_released','feature_id':args.feature_id}
  elif verb=='challenge-status':
   from . import provenance_stake as _ps
   result=_ps.challenge_status(exchange,args.feature_id)
  elif verb=='cost':
   from . import cost_model as _cm
   if args.operation=='vs_executor':result=_cm.vs_executor_comparison(config,args.ask_price_units,args.executor_calls_saved)
   elif args.operation=='borrow_feature':result=_cm.borrow_feature_cost(config,args.ask_price_units,args.artifact_size_bytes)
   else:result=_cm.total_operation_cost(args.operation,config,artifact_size_bytes=args.artifact_size_bytes)
  elif verb=='dek-unwrap':
   _dku_rows=exchange.audit_rows()
   _dku_grant=next((r for r in _dku_rows if r.get('kind')=='ARTIFACT_KEY_GRANT' and r.get('listing_id')==args.listing_id),None)
   if _dku_grant is None:raise ValueError(f'No ARTIFACT_KEY_GRANT found for listing_id {args.listing_id!r}')
   _wrapped_hex=_dku_grant.get('wrapped_dek_hex','')
   if not _wrapped_hex:raise ValueError('ARTIFACT_KEY_GRANT row has no wrapped_dek_hex field (listing predates session-bound DEK feature)')
   from . import session_dek as _sdek_u
   _priv_hex=args.private_key_hex
   try:_priv_pem=bytes.fromhex(_priv_hex)
   except ValueError:_priv_pem=_priv_hex.encode()
   _wrapped_bytes=bytes.fromhex(_wrapped_hex)
   _dek_plain=_sdek_u.unwrap_dek(_wrapped_bytes,_priv_pem)
   result={'listing_id':args.listing_id,'dek_hex':_dek_plain.hex(),'artifact_sha256':_dku_grant.get('artifact_sha256','')}
  elif verb=='escrow-status':
   from . import escrow_timeout as _et
   _pending=_et.check_escrow_timeouts(exchange)
   _all_filled=[r for r in exchange.audit_rows() if r.get('kind')=='EQUITY_LISTING_FILLED']
   _all_granted={r.get('listing_id') for r in exchange.audit_rows() if r.get('kind')=='ARTIFACT_KEY_GRANT'}
   _all_refunded={r.get('listing_id') for r in exchange.audit_rows() if r.get('kind')=='ESCROW_REFUND'}
   import time as _et_t
   _now_et=_et_t.time()
   _timeout_s=_et.DEFAULT_ESCROW_TIMEOUT_HOURS*3600
   _in_progress=[]
   for _fr in _all_filled:
    _lid=_fr.get('listing_id','')
    if _lid in _all_granted or _lid in _all_refunded:continue
    _elapsed=_now_et-float(_fr.get('at_unix',0))
    if _elapsed<_timeout_s:_in_progress.append({'listing_id':_lid,'feature_id':_fr.get('feature_id',''),'buyer_peer_id':_fr.get('buyer_peer_id',_fr.get('peer_id','')),'elapsed_hours':round(_elapsed/3600,2),'timeout_hours':_et.DEFAULT_ESCROW_TIMEOUT_HOURS,'status':'waiting_dek'})
   result={'pending_escrow':_in_progress,'overdue':_pending,'timeout_hours':_et.DEFAULT_ESCROW_TIMEOUT_HOURS,'total_in_escrow':len(_in_progress),'total_overdue':len(_pending)}
  elif verb=='visibility':
   _vis_rows=exchange.audit_rows()
   _vis_grant=next((r for r in _vis_rows if r.get('kind')=='EQUITY_GRANT' and r.get('feature_id')==args.feature_id),None)
   if _vis_grant is None:raise ValueError(f'Feature {args.feature_id!r} has no equity grant')
   result={'feature_id':args.feature_id,'visibility':_vis_grant.get('visibility','public') or 'public'}
  else:raise ValueError(f'Unknown equity verb: {verb!r}')
 elif group=='bridge':
  local_id=config.get('peer_id',exchange.identity().get('peer_id','local'))
  from . import integration_bridge as _ib
  if verb=='nft-mint':
   _br_creator=getattr(args,'creator_id',None) or local_id
   result=_ib.stub_nft_mint(exchange,args.feature_id,_br_creator)
  elif verb=='on-ramp':
   result=_ib.stub_crypto_on_ramp(exchange,local_id,args.amount_units,args.crypto_address)
  elif verb=='off-ramp':
   result=_ib.stub_crypto_off_ramp(exchange,local_id,args.amount_units,args.crypto_address)
  elif verb=='on-chain-verify':
   result=_ib.stub_on_chain_verify(exchange,args.feature_id)
  else:raise ValueError(f'Unknown bridge verb: {verb!r}')
 elif group=='reputation':
  from . import credit_ledger as _cl
  if verb=='show':
   pid=args.peer_id;earned=_cl.earned_balance(exchange.root,pid);total=_cl.balance(exchange.root,pid)
   result={'peer_id':pid,'earned_balance':earned,'total_balance':total,'market_balance':total-earned,'earned_display':_cl.to_display(earned),'total_display':_cl.to_display(total)}
  elif verb=='leaderboard':
   try:rows=exchange.audit_rows()
   except Exception:rows=[]
   peers={r.get('peer') for r in rows if r.get('kind')=='CREDIT_DELTA' and r.get('peer')}
   board=sorted([{'peer_id':p,'earned_balance':_cl.earned_balance(exchange.root,p)} for p in peers],key=lambda x:-x['earned_balance'])
   result={'leaderboard':board[:args.limit]}
  elif verb=='history':
   import time as _t
   try:rows=exchange.audit_rows()
   except Exception:rows=[]
   cutoff=_t.time()-args.window_days*86400
   REP_KINDS={'QUALIFY_RECEIPT','CREDIT_DELTA','EQUITY_SELL','EQUITY_LISTING_FILLED','WORK_RELEASED'}
   events=[r for r in rows if r.get('kind') in REP_KINDS and (r.get('peer')==args.peer_id or r.get('buyer_id')==args.peer_id or r.get('seller_id')==args.peer_id) and float(r.get('at_unix',0))>cutoff]
   result={'peer_id':args.peer_id,'days':args.window_days,'events':events,'event_count':len(events)}
  else:raise ValueError(f'Unknown reputation verb: {verb!r}')
 elif group=='network-audit':
  P2P_KINDS={'CATALOG_CHECK','P2P_CORPUS_MISMATCH','RPC_ADMITTED','RPC_REJECTED','RPC_FLOOD_BLOCKED','HOLE_PUNCH_ATTEMPTED','DHT_BOOTSTRAP','PEER_CONNECTED','DHT_BOOTSTRAP_SKIPPED'}
  try:rows=exchange.audit_rows()
  except Exception:rows=[]
  rows=[r for r in rows if r.get('kind') in P2P_KINDS]
  if getattr(args,'kind',None):rows=[r for r in rows if r.get('kind')==args.kind]
  if getattr(args,'peer',None):rows=[r for r in rows if r.get('peer')==args.peer]
  result=rows[-args.limit:]
 elif group=='reset':
  if verb=='all':
   if not getattr(args,'yes',False):
    try:confirm=input('Delete ALL exchange data (balances, listings, work history)? [y/N] ').strip().lower()
    except(EOFError,KeyboardInterrupt):confirm='n'
    if confirm not in('y','yes'):print(json.dumps({'status':'aborted'},indent=2,sort_keys=True));return 0
   import datetime as _dt
   try:
    rows=exchange.audit_rows()
    row_count=len(rows)
   except Exception:row_count=0
   try:
    if hasattr(exchange,'_rows'):exchange._rows.clear()
    exchange.append_audit_row({'kind':'EXCHANGE_RESET','reason':'release_clean','reset_at':_dt.datetime.now(_dt.timezone.utc).isoformat()})
    result={'status':'reset','rows_cleared':row_count,'note':'fresh exchange state ready for release build'}
   except Exception as _e:print(json.dumps({'error':str(_e)},indent=2,sort_keys=True));return 2
  else:raise ValueError(f'Unknown reset verb: {verb!r}')
 elif group=='compact':
  from . import ledger_compaction as _lc
  if verb=='contracts':result=_lc.compact_closed_contracts(exchange,args.older_than_days)
  elif verb=='checkpoint':
   _ckpt_id=_lc.ledger_checkpoint(exchange,str(exchange.root))
   _block_result={}
   if config.get('p2p',{}).get('ledger_block_mode',True):
    _block_result=_lc.seal_ledger_block(exchange,str(exchange.root))
   _escrow_refunds=[]
   if config.get('p2p',{}).get('run_escrow_checks',True):
    from . import escrow_timeout as _et_ckpt
    try:_escrow_refunds=_et_ckpt.process_escrow_refunds(exchange)
    except Exception:pass
   result={'checkpoint_id':_ckpt_id,'block_seal':_block_result,'escrow_refunds_processed':len(_escrow_refunds)}
  elif verb=='sync-tail':
   ckpt,tail=_lc.sync_tail_rows(exchange)
   result={'checkpoint':ckpt,'tail_row_count':len(tail),'full_sync_required':ckpt is None}
  elif verb=='balance-fast':
   _bf=_lc.balance_fast(str(exchange.root),args.peer_id,exchange)
   from . import credit_ledger as _cl_bf
   result={'peer':args.peer_id,'balance_fast_units':_bf,'balance_fast_tokens':round(_bf/_cl_bf.UNIT,8)}
  elif verb=='sync-state':
   from . import ledger_sync as _ls
   result=_ls.sync_summary(exchange.audit_rows())
  elif verb=='light-balance':
   from . import ledger_sync as _ls
   _ls_rows=exchange.audit_rows()
   _ls_seal=_ls.latest_seal(_ls_rows)
   if _ls_seal is None:raise ValueError('No LEDGER_BLOCK_SEAL found — run compact seal-block first to enable light-peer balance')
   _ls_tail=_ls.tail_since_seal(_ls_rows,_ls_seal)
   _ls_bal=_ls.balance_from_seal(_ls_seal,_ls_tail,args.peer_id)
   from . import credit_ledger as _cl_lb
   result={'peer':args.peer_id,'balance_units':_ls_bal,'balance_tokens':round(_ls_bal/_cl_lb.UNIT,8),'seal_sequence':_ls_seal.get('sequence',0),'tail_rows_applied':len(_ls_tail),'method':'seal+tail (light-peer)'}
  elif verb=='depletion':
   from . import equity_auto_trade as _eat
   result=_eat.feature_depletion_status(args.feature_id,exchange,args.network_size)
  elif verb=='search':
   import re as _re
   q=getattr(args,'query',None)
   try:q=_validate_freeform_query(q,max_bytes=4096)
   except ValueError as _qerr:print(json.dumps({'error':str(_qerr)}));return 1
   _searched_at=_time_mod.strftime('%Y-%m-%dT%H:%M:%SZ',_time_mod.gmtime())
   try:rows=exchange.audit_rows()
   except Exception:rows=[]
   # also include decompressed archive rows so search is comprehensive
   try:
    _arch_dir=exchange.root/'p2p_audit_archives'
    if _arch_dir.exists():
     import zlib,base64
     for _af in sorted(_arch_dir.glob('*.json')):
      try:
       import json as _jj;_arch=_jj.loads(_af.read_text())
       _payload=_arch.get('payload')
       if _payload:
        _raw=zlib.decompress(base64.b64decode(_payload))
        rows=_jj.loads(_raw)+rows
      except Exception:pass
   except Exception:pass
   total_before=len(rows)
   if getattr(args,'kind',None):rows=[r for r in rows if r.get('kind')==args.kind]
   if getattr(args,'peer',None):rows=[r for r in rows if r.get('peer')==args.peer]
   if getattr(args,'search_feature',None):rows=[r for r in rows if r.get('feature_id')==args.search_feature]
   if getattr(args,'since_unix',None) is not None:rows=[r for r in rows if float(r.get('at_unix',0))>=args.since_unix]
   if q:
    import re as _re2
    q_lower=q.lower()
    fv_match=_re2.match(r'^(\w+)=(.+)$',q.strip())
    if fv_match:
     field,value=fv_match.group(1),fv_match.group(2)
     rows=[r for r in rows if str(r.get(field,'')).lower()==value.lower()]
    else:
     rows=[r for r in rows if q_lower in json.dumps(r,sort_keys=True).lower()]
   rows=rows[-args.limit:]
   # redact context_snapshot from equity grant rows — show only context_kinds_included
   safe_rows=[]
   for _sr in rows:
    if 'context_snapshot' in _sr and not getattr(args,'detail',False):
     _sr=dict(_sr);_sr.pop('context_snapshot',None)
    safe_rows.append(_sr)
   _qhash=hashlib.sha256(q.encode()).hexdigest() if q else None
   result={'query':q,'rows':safe_rows,'count':len(safe_rows),'total_before_limit':total_before,'searched_at':_searched_at,'traceable':True,'auditable':True,'includes_archives':True,'query_hash':_qhash}
  elif verb=='compress':
   import time as _t,zlib as _zlib,base64 as _b64
   cutoff=_t.time()-args.older_than_days*86400
   try:live=exchange.audit_rows()
   except Exception:live=[]
   old=[r for r in live if float(r.get('at_unix',0))<cutoff]
   keep=[r for r in live if float(r.get('at_unix',0))>=cutoff]
   if args.dry_run:
    result={'dry_run':True,'rows_to_compress':len(old),'rows_to_keep':len(keep),'note':'no changes written'}
   elif old:
    import json as _jc,time as _tc
    _payload=_b64.b64encode(_zlib.compress(_jc.dumps(old).encode())).decode()
    _arch_id=f'p2p_audit_{int(_tc.time())}'
    _arch_dir=exchange.root/'p2p_audit_archives';_arch_dir.mkdir(exist_ok=True)
    (_arch_dir/f'{_arch_id}.json').write_text(_jc.dumps({'archive_id':_arch_id,'compressed_at':_tc.time(),'row_count':len(old),'payload':_payload},indent=2))
    # rewrite live audit without old rows
    _audit_path=exchange.root/'p2p_audit.json'
    if _audit_path.exists():_audit_path.write_text(_jc.dumps(keep,indent=2))
    result={'archive_id':_arch_id,'rows_compressed':len(old),'rows_kept':len(keep),'note':'local only — wire protocol unchanged'}
   else:
    result={'rows_compressed':0,'rows_kept':len(keep),'note':'no rows old enough to compress'}
  elif verb=='decompress':
   _arch_dir=exchange.root/'p2p_audit_archives'
   if not _arch_dir.exists():result={'archives':[],'note':'no archives found'}
   elif not args.archive_id:
    import json as _jd
    archives=[json.loads(f.read_text()) for f in sorted(_arch_dir.glob('*.json'))]
    result={'archives':[{k:v for k,v in a.items() if k!='payload'} for a in archives],'count':len(archives)}
   else:
    import zlib as _zd,base64 as _bd,json as _jdd
    _af=_arch_dir/f'{args.archive_id}.json'
    if not _af.exists():raise ValueError(f'Archive {args.archive_id!r} not found')
    _arch=_jdd.loads(_af.read_text())
    _rows=_jdd.loads(_zd.decompress(_bd.b64decode(_arch['payload'])))
    result={'archive_id':args.archive_id,'compressed_at':_arch.get('compressed_at'),'rows':_rows[-args.limit:],'count':len(_rows)}
  else:raise ValueError(f'Unknown compact verb: {verb!r}')
 elif group=='bootstrap':
  cfg=exchange.load()
  peers_list=cfg.get('bootstrap_peers',[])
  if verb=='list':result={'bootstrap_peers':peers_list,'count':len(peers_list)}
  elif verb=='add':
   endpoint=args.endpoint.strip()
   if not endpoint.startswith('https://'):raise ValueError('Bootstrap peer endpoint must start with https://')
   if endpoint in peers_list:result={'status':'already_present','endpoint':endpoint}
   else:
    peers_list=peers_list+[endpoint]
    with exchange.lock():
     cfg=exchange.load();cfg['bootstrap_peers']=peers_list
     import json as _jsn
     (exchange.root/'policy.json').write_text(_jsn.dumps(cfg,indent=2))
    result={'status':'added','endpoint':endpoint,'total':len(peers_list)}
  elif verb=='remove':
   endpoint=args.endpoint.strip()
   if endpoint not in peers_list:result={'status':'not_found','endpoint':endpoint}
   else:
    peers_list=[p for p in peers_list if p!=endpoint]
    with exchange.lock():
     cfg=exchange.load();cfg['bootstrap_peers']=peers_list
     import json as _jsn
     (exchange.root/'policy.json').write_text(_jsn.dumps(cfg,indent=2))
    result={'status':'removed','endpoint':endpoint,'total':len(peers_list)}
  else:raise ValueError(f'Unknown bootstrap verb: {verb!r}')
 else:raise ValueError('Unknown exchange action')
 print(json.dumps(result,indent=2,sort_keys=True,default=str));return 0

from contextlib import contextmanager
@contextmanager
def advertise(exchange,host,port):
 if not exchange.load()['advertise']:yield;return
 try:from zeroconf import Zeroconf,ServiceInfo
 except ImportError:raise ValueError('Advertising requires optional python-zeroconf')
 import ipaddress,socket
 address=ipaddress.ip_address(host)
 if address.is_unspecified:raise ValueError('Advertising requires an explicit local interface address')
 identity=exchange.identity()['peer_id'];service=ServiceInfo('_urace-exchange._tcp.local.',identity[:16]+'._urace-exchange._tcp.local.',addresses=[address.packed],port=port,properties={'version':'1','identity':identity},server=identity[:16]+'.local.')
 with Zeroconf() as z:
  z.register_service(service)
  try:yield
  finally:z.unregister_service(service)


@contextmanager
def selection_worker(exchange):
 """One bounded metadata worker while the owner explicitly runs the peer server."""
 import threading
 from .peer_selection import refresh
 stop=threading.Event()
 def work():
  while not stop.is_set():
   try:
    if exchange.load().get('auto_select',True):refresh(exchange,limit=1)
   except (ValueError,OSError):pass
   stop.wait(60)
 thread=threading.Thread(target=work,name='urace-peer-metadata',daemon=True);thread.start()
 try:yield
 finally:stop.set();thread.join(timeout=12)
