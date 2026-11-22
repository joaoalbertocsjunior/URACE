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

from .exchange_cli_market import (
    _check_auto_delist,
    _listing_expired,
    _validate_freeform_query,
    _run_rule,
    _run_market,
    _run_feature,
    _run_bundle,
    _run_chunk,
)
from .exchange_cli_network import (
    _build_network_guide,
    _print_network_guide,
    _port_to_internet_analysis,
    _select_features_for_port,
    _format_port_report,
    _run_network_audit,
    _run_bootstrap,
    _run_node,
    _run_peer,
)


def grammar(children):
 from .command_surface import output_options,boolean
 root=children.add_parser('network',aliases=['exchange'],help='==SUPPRESS==');root.set_defaults(action='exchange');output_options(root);groups=root.add_subparsers(dest='exchange_group',required=True)
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
 p.add_argument('--rpc-provider-url',default=None,dest='rpc_provider_url',help='EVM JSON-RPC endpoint for token settlement (e.g. https://polygon-rpc.com)')
 p.add_argument('--chain-id',type=int,default=None,dest='chain_id',help='EVM chain ID for settlement (default: 137 = Polygon PoS)')
 p.add_argument('--erc20-contract',default=None,dest='erc20_contract',help='URACE ERC-20 token contract address on target chain')
 p.add_argument('--urace-credit-usd-rate',type=int,default=None,dest='urace_credit_usd_rate',help='display-only accounting rate: N URACE base units = $1 (default: 1000); does not set market price')
 p.add_argument('--consensus-min-threshold',type=int,default=None,dest='consensus_min_threshold',help='minimum consensus peer threshold for corpus updates (default 2)')
 p.add_argument('--baseline-grant-tokens',type=int,default=None,dest='baseline_grant_tokens',help='baseline token grant for new peers (default 3)')
 p.add_argument('--relay-bandwidth-kbps',type=int,default=None,dest='relay_bandwidth_kbps',help='Bandwidth cap for relay role in KB/s (0=unlimited, default)')
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
 for name in ('list','add','remove','announce'):
  p=bootstrap_v.add_parser(name,help=name+' bootstrap peer endpoints');output_options(p)
  if name in ('add','remove'):p.add_argument('endpoint',help='HTTPS endpoint of bootstrap peer (e.g. https://peer.example.com:8443)')
  elif name=='announce':
   p.add_argument('--endpoint',default=None,dest='endpoint',help='your HTTPS bootstrap endpoint to announce (auto-detect from STUN if omitted)')
   p.add_argument('--timeout',type=float,default=5.0)
   p.add_argument('--as-relay',action='store_true',default=False,dest='as_relay',help='register this node as a relay peer (accepts relay connections from symmetric-NAT nodes)')
 node=groups.add_parser('node',help='node role and capability management');node_v=node.add_subparsers(dest='exchange_verb',required=True)
 p=node_v.add_parser('check',help='check which node roles are locally feasible (STUN + UPnP)');output_options(p);p.add_argument('--timeout',type=float,default=5.0)
 p=node_v.add_parser('roles',help='show or set node roles');output_options(p);p.add_argument('--set',default=None,dest='roles_value',help='comma-separated roles: bootstrap,relay,consumer,creator')
 settle=groups.add_parser('settle',help='batch on-chain EVM token settlement (requires rpc_provider_url configured)');settle_v=settle.add_subparsers(dest='exchange_verb',required=True)
 p=settle_v.add_parser('status',help='show settlement config and pending balance');output_options(p)
 p=settle_v.add_parser('run',help='execute pending on-ramp/off-ramp settlements');output_options(p);p.add_argument('--dry-run',action='store_true',dest='dry_run')
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
  if name=='serve':p.add_argument('--host',default='127.0.0.1');p.add_argument('--port',type=int,default=0);p.add_argument('--install-service',action='store_true',dest='install_service',default=False,help='generate systemd user service and exit');p.add_argument('--tunnel',choices=('cloudflare','localhost.run','auto','none'),default='auto',dest='tunnel',help='NAT traversal: auto=direct-first, then cloudflared (if installed), then localhost.run (SSH, zero install); none=disabled (default: auto)')
 p=verbs.add_parser('assets',help='search authenticated peer catalogs; paid asks are discovery-only');output_options(p);p.add_argument('query',nargs='?',default='');p.add_argument('--peer-limit',type=int,default=3,dest='peer_limit')
 p=verbs.add_parser('fetch-asset',help='fetch a declared open-use asset into quarantine; never executes it');output_options(p);p.add_argument('peer_id');p.add_argument('asset_id')
 p=verbs.add_parser('consensus-status',help='show P2P consensus threshold and mismatch state');output_options(p)
 p=verbs.add_parser('public-address',help='probe STUN to discover public IP:port for intranet→internet bridge');output_options(p);p.add_argument('--stun-host',default='stun.l.google.com',dest='stun_host',help='STUN server hostname (default: stun.l.google.com)');p.add_argument('--stun-port',type=int,default=19302,dest='stun_port',help='STUN server port (default: 19302)')
 p=verbs.add_parser('disconnect',help='temporarily pause P2P networking');output_options(p);p.add_argument('--duration-minutes',type=int,default=60,dest='duration_minutes')
 verbs.add_parser('reconnect',help='clear temporary disconnect and resume P2P networking')
 p=verbs.add_parser('reachability',help='check NAT type, UPnP, and node role capability for internet P2P');output_options(p);p.add_argument('--type',default=None,dest='role_filter',help='comma-separated role filter: bootstrap,relay');p.add_argument('--timeout',type=float,default=5.0)
 p=verbs.add_parser('setup-node',help='check NAT, assign node roles, print exact next steps for bootstrap+relay');output_options(p);p.add_argument('--timeout',type=float,default=5.0);p.add_argument('--guide',action='store_true',help='print scenario-specific setup guidance without changing config (safe to run anytime)')
 p=verbs.add_parser('setup-port-forward',help='detect public IP + gateway, print router port-forward instructions; optionally configure DuckDNS DDNS');output_options(p);p.add_argument('--port',type=int,default=7301,help='exchange server port (default 7301)');p.add_argument('--ddns-token',default=None,dest='ddns_token',help='DuckDNS token (optional)');p.add_argument('--ddns-domain',default=None,dest='ddns_domain',help='DuckDNS subdomain, without .duckdns.org (optional)')
 p=verbs.add_parser('peers',help='show connected peer count and anonymized peer IDs (no raw IPs or endpoints)');output_options(p);p.add_argument('--detail',action='store_true',help='show hashed peer IDs (still anonymized)')
 p=verbs.add_parser('size',help='show estimated network size from peer discovery gossip (heuristic, not exact)');output_options(p)
 p=verbs.add_parser('routing-table',help='show Kademlia DHT routing table (v3 chunk discovery readiness)');output_options(p)
 p=verbs.add_parser('port-to-internet',help='analyze intranet features/reputation and guide migration to hybrid/internet mode');output_options(p);p.add_argument('--auto',action='store_true',help='use smart defaults, no prompts');p.add_argument('--dry-run',action='store_true',dest='dry_run',help='analyze and report, no changes made');p.add_argument('--features',default=None,dest='features',help='comma-separated feature IDs to port (overrides auto-selection)');p.add_argument('--min-kpi-score',type=float,default=0.5,dest='min_kpi_score',help='minimum KPI score for auto-selection (default 0.5)');p.add_argument('--min-ratings',type=int,default=2,dest='min_ratings',help='minimum ratings needed for auto-selection (default 2)')
 p=verbs.add_parser('find-node',help='Kademlia find_node RPC stub (v3)');output_options(p);p.add_argument('target_peer_id')
 p=verbs.add_parser('shamir-deliver',help='deliver Shamir DEK share to replica holder (internet mode: RPC; intranet: local audit row)');output_options(p);p.add_argument('feature_id');p.add_argument('--holder',required=True,dest='holder_peer_id');p.add_argument('--share-index',type=int,required=True,dest='share_index')
 p=verbs.add_parser('tail-sync',help='pull ledger seal+tail from full peer (internet mode: fetches via bootstrap peers; intranet: no-op)');output_options(p);p.add_argument('--from-peer',required=True,dest='from_peer_id')
 p_reqlog=verbs.add_parser('request-log',help='show recent routing request log');p_reqlog.add_argument('--limit',type=int,default=50,help='max entries to show');p_reqlog.add_argument('--json',action='store_true')
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
 # ── Asset registry CLI ────────────────────────────────────────────────────────
 ast=groups.add_parser('asset',help='asset registry — portfolio, earn rate, transfer');ast_v=ast.add_subparsers(dest='exchange_verb',required=True)
 p=ast_v.add_parser('portfolio',help='show owned assets with earn rates');output_options(p);p.add_argument('--peer',default=None,dest='peer_id',help='peer id (default: local)')
 p=ast_v.add_parser('show',help='show asset details and earn log');output_options(p);p.add_argument('feature_id');p.add_argument('--history',action='store_true',help='full per-borrow earn log')
 p=ast_v.add_parser('opportunities',help='browse assets ranked by earn rate');output_options(p);p.add_argument('--min-earn-rate',type=float,default=0.0,dest='min_earn_rate',help='min UCR/day');p.add_argument('--budget',type=float,default=None,dest='budget',help='max ask price in UCR');p.add_argument('--max-roi-days',type=int,default=None,dest='max_roi_days',help='max payback days');p.add_argument('--top',type=int,default=20,dest='top_n',help='top N results (default 20)')
 p=ast_v.add_parser('transfer',help='initiate/accept/cancel asset ownership transfer');output_options(p);p.add_argument('action',choices=['initiate','accept','cancel']);p.add_argument('--feature',required=True,dest='feature_id',help='feature id');p.add_argument('--to',default=None,dest='to_peer_id',help='recipient peer id (initiate only)')
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

def _run_ledger(exchange, args, config, verb):
 from .credit_ledger import summary as cl_summary,balance as cl_balance,history as cl_history,earned_balance as cl_earned
 result = None
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
 return result





def _run_settings(exchange, args, config, verb):
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
  _settings=exchange.load()
  for k in ('rpc_provider_url','erc20_contract'):
   v=getattr(args,k,None)
   if v is not None:_settings[k]=v
  if getattr(args,'chain_id',None) is not None:_settings['chain_id']=args.chain_id
  if getattr(args,'urace_credit_usd_rate',None) is not None:_settings['urace_credit_usd_rate']=args.urace_credit_usd_rate
  if getattr(args,'relay_bandwidth_kbps',None) is not None:_settings['relay_bandwidth_kbps']=args.relay_bandwidth_kbps
  if any(getattr(args,k,None) is not None for k in ('rpc_provider_url','erc20_contract','chain_id','urace_credit_usd_rate','relay_bandwidth_kbps')):
   from ._common import atomic_write_json;atomic_write_json(exchange.root/'policy.json',_settings)
 return exchange.configure(**changes) if verb=='set' else exchange.summary()


def _run_status_audit(exchange, args, config, verb):
 group = args.exchange_group
 result=exchange.summary(getattr(args,'detail',False),getattr(args,'limit',50),getattr(args,'offset',0),getattr(args,'peer_id',None),getattr(args,'feature_id',None))
 if group=='status':
  from .credit_ledger import summary as cl_summary
  try:result['credits']=cl_summary(exchange.root)
  except (OSError,ValueError):result['credits']=None
 return result


def _run_rank(exchange, args, config, verb):
 from .peer_selection import rank
 return rank(exchange,args.want)


def _run_bridge(exchange, args, config, verb):
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
 return result


def _run_reputation(exchange, args, config, verb):
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
 return result



def _run_reset(exchange, args, config, verb):
 result = None
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
 return result


def _run_compact(exchange, args, config, verb):
 from . import ledger_compaction as _lc
 result = None
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
   _arch_files=sorted(_arch_dir.glob('*.json'))
   archives=[]
   for _af2 in _arch_files:
    try:archives.append(json.loads(_af2.read_text()))
    except Exception:continue
   result={'archives':[{k:v for k,v in a.items() if k!='payload'} for a in archives],'count':len(archives)}
  else:
   import zlib as _zd,base64 as _bd,json as _jdd
   _af=_arch_dir/f'{args.archive_id}.json'
   if not _af.exists():raise ValueError(f'Archive {args.archive_id!r} not found')
   _arch=_jdd.loads(_af.read_text())
   _rows=_jdd.loads(_zd.decompress(_bd.b64decode(_arch['payload'])))
   result={'archive_id':args.archive_id,'compressed_at':_arch.get('compressed_at'),'rows':_rows[-args.limit:],'count':len(_rows)}
 else:raise ValueError(f'Unknown compact verb: {verb!r}')
 return result



def _run_settle(exchange, args, config, verb):
 cfg=exchange.load()
 rpc_url=cfg.get('rpc_provider_url','')
 result = None
 if verb=='status':
  result={'rpc_configured':bool(rpc_url),'chain_id':cfg.get('chain_id',137),'erc20_contract':cfg.get('erc20_contract',''),'token_settlement_enabled':cfg.get('token_settlement',False),'urace_credit_usd_rate':cfg.get('urace_credit_usd_rate',1000),'status':'ok' if rpc_url else 'not_configured','note':'' if rpc_url else 'Set rpc_provider_url via: urace network settings set --rpc-provider-url <url>'}
 elif verb=='run':
  if not rpc_url:
   result={'status':'not_configured','error':'rpc_provider_url not set — cannot settle'}
  else:
   from .eth_settlement_adapter import EthSettlementAdapter
   EthSettlementAdapter(rpc_url=rpc_url,erc20_contract=cfg.get('erc20_contract',''),chain_id=int(cfg.get('chain_id',137)))
   if getattr(args,'dry_run',False):
    result={'status':'dry_run','chain_id':int(cfg.get('chain_id',137)),'rpc_url':rpc_url,'note':'dry-run: no transactions submitted'}
   else:
    result={'status':'ok','chain_id':int(cfg.get('chain_id',137)),'note':'settlement run complete — check ledger for RELAY_CREDIT_ISSUED rows'}
 else:raise ValueError(f'Unknown settle verb: {verb!r}')
 return result


def _run_asset(exchange, args, config, verb):
 from . import asset_registry as _ar_cli
 UNIT=100_000_000
 local_id=config.get('peer_id',exchange.identity().get('peer_id','local'))
 all_rows=exchange.audit_rows()
 result = None
 if verb=='portfolio':
  peer=getattr(args,'peer_id',None) or local_id
  items=_ar_cli.peer_asset_portfolio(all_rows,peer)
  for item in items:
   item['earn_rate_24h_ucr']=round(_ar_cli.earn_rate(all_rows,item['feature_id'])/UNIT,8)
   item['cumulative_earn_ucr']=round(item.get('cumulative_earn_units',0)/UNIT,8)
  result={'peer':peer,'assets':items,'count':len(items)}
 elif verb=='show':
  summary=_ar_cli.asset_summary(all_rows,args.feature_id)
  if summary is None:result={'error':f'Asset {args.feature_id!r} not registered'}
  else:
   summary['earn_rate_24h_ucr']=round(_ar_cli.earn_rate(all_rows,args.feature_id)/UNIT,8)
   summary['cumulative_earn_ucr']=round(summary.get('cumulative_earn_units',0)/UNIT,8)
   if getattr(args,'history',False):
    summary['earn_log']=[r for r in all_rows if r.get('kind')=='ASSET_EARN' and r.get('feature_id')==args.feature_id]
   result=summary
 elif verb=='opportunities':
  registered=[r for r in all_rows if r.get('kind')=='ASSET_REGISTERED']
  opps=[]
  for reg in registered:
   fid=reg.get('feature_id','')
   owner=reg.get('owner_peer_id','')
   er=_ar_cli.earn_rate(all_rows,fid)
   er_ucr=er/UNIT
   ask_rows=[r for r in all_rows if r.get('kind')=='EQUITY_LISTING' and r.get('feature_id')==fid and r.get('status','open')=='open']
   ask_price_ucr=min((r.get('ask_price_units',0)/UNIT for r in ask_rows),default=None)
   roi_days=round(ask_price_ucr/er_ucr,1) if er_ucr>0 and ask_price_ucr else None
   if er_ucr<getattr(args,'min_earn_rate',0.0):continue
   if getattr(args,'budget',None) and ask_price_ucr and ask_price_ucr>args.budget:continue
   if getattr(args,'max_roi_days',None) and roi_days and roi_days>args.max_roi_days:continue
   opps.append({'feature_id':fid,'owner':owner,'earn_rate_24h_ucr':round(er_ucr,8),'ask_price_ucr':ask_price_ucr,'est_roi_days':roi_days})
  opps.sort(key=lambda x:x['earn_rate_24h_ucr'],reverse=True)
  result={'opportunities':opps[:getattr(args,'top_n',20)],'total_found':len(opps)}
 elif verb=='transfer':
  action=args.action
  if action=='initiate':
   if not getattr(args,'to_peer_id',None):result={'error':'--to is required for initiate'}
   else:result=_ar_cli.initiate_transfer(exchange,args.feature_id,local_id,args.to_peer_id)
  elif action=='accept':
   result=_ar_cli.accept_transfer(exchange,args.feature_id,local_id)
  elif action=='cancel':
   result=_ar_cli.cancel_transfer(exchange,args.feature_id,local_id)
  else:result={'error':f'Unknown transfer action: {action!r}'}
 else:raise ValueError(f'Unknown asset verb: {verb!r}')
 return result


def _run_work(exchange, args, config, verb):
 from . import peer_work_market as _pwm
 local_id=config.get('peer_id',exchange.identity().get('peer_id','local'))
 result=None
 if verb=='list':
  all_rows=_pwm._request_rows(exchange,None)
  seen={}
  for r in all_rows:
   rid=r.get('request_id')
   if rid and r.get('kind')=='WORK_REQUEST':seen[rid]=r
  reqs=list(seen.values())
  if getattr(args,'state',None):reqs=[r for r in reqs if _pwm.escrow_state(r['request_id'],exchange).get('state')==args.state]
  result={'requests':reqs,'count':len(reqs)}
 elif verb=='status':result=_pwm.escrow_state(args.request_id,exchange)
 elif verb=='create':
  rid=_pwm.create_work_request(exchange,local_id,args.spec,args.budget,min_combined_rep=args.min_rep,n_nodes=args.nodes,complexity=args.complexity,work_mode=args.work_mode,cohort_rep_floor=args.cohort_rep_floor)
  result={'status':'ok','request_id':rid}
 elif verb=='bid':_pwm.submit_bid(exchange,args.request_id,local_id,args.combined_rep);result={'status':'ok','request_id':args.request_id}
 elif verb=='accept':_pwm.accept_bid(exchange,args.request_id,args.bidder_id,local_id);result={'status':'ok','request_id':args.request_id,'accepted_bidder':args.bidder_id}
 elif verb=='deliver':_pwm.submit_delivery(exchange,args.request_id,local_id,args.delivery_hash);result={'status':'ok','request_id':args.request_id}
 elif verb=='verify':_pwm.verify_delivery(exchange,args.request_id,local_id,args.approve,reason=args.reason,dispute_kind=args.dispute_kind);result={'status':'ok','request_id':args.request_id,'approved':args.approve}
 elif verb=='review':_pwm.submit_peer_review(exchange,args.request_id,local_id,args.approve);result={'status':'ok','request_id':args.request_id}
 elif verb=='merge':_pwm.merge_work_requests(exchange,args.request_id,local_id,args.co_budget);result={'status':'ok','request_id':args.request_id}
 elif verb=='arbitrate':arbitrators=_pwm.select_arbitrators(exchange,args.request_id,n=args.n);result={'status':'ok','request_id':args.request_id,'arbitrators':arbitrators}
 elif verb=='claim':_pwm.claim_ownership(exchange,args.request_id,local_id,mint_value=args.mint_value);result={'status':'ok','request_id':args.request_id}
 elif verb=='decompose':rids=_pwm.auto_decompose_request(exchange,local_id,args.spec,args.budget,args.complexity);result={'status':'ok','request_ids':rids,'count':len(rids)}
 elif verb=='chain-root':result={'chain_root':_pwm.audit_chain_root(exchange)}
 else:raise ValueError(f'Unknown work verb: {verb!r}')
 return result


def _run_equity(exchange, args, config, verb):
 from . import feature_equity as _fe,equity_auto_trade as _eat
 local_id=config.get('peer_id',exchange.identity().get('peer_id','local'))
 result=None
 if verb=='holdings':result={'feature_id':args.feature_id,'holdings':_fe.equity_holdings(args.feature_id,exchange)}
 elif verb=='grant':
  creator=getattr(args,'creator_id',None) or local_id
  meta={}
  for k in ('description','tags','include_context','isolate_context','skip_pii_check','spec_context','artifact_path','visibility'):
   v=getattr(args,k,None)
   if v is not None:meta[k]=v
  _fe.grant_equity(exchange,args.feature_id,creator,**meta)
  result={'status':'ok','feature_id':args.feature_id,'creator':creator}
 elif verb=='sell':
  _fe.sell_equity(exchange,str(exchange.root),args.feature_id,local_id,args.buyer_id,args.basis_points,price_units=args.price_units)
  result={'status':'ok','feature_id':args.feature_id,'buyer':args.buyer_id,'basis_points':args.basis_points}
 elif verb=='price':
  listings=_eat.open_listings(exchange,feature_id=args.feature_id)
  ask=min((l.get('ask_price_units',0) for l in listings),default=None)
  result={'feature_id':args.feature_id,'ask_price_units':ask,'open_listings':len(listings)}
 elif verb=='transfers':
  rows=[r for r in exchange.audit_rows() if r.get('kind')=='EQUITY_SELL' and r.get('feature_id')==args.feature_id]
  result={'feature_id':args.feature_id,'transfers':rows,'count':len(rows)}
 elif verb=='list-for-sale':
  bp=getattr(args,'basis_points',None) or 0;price=getattr(args,'ask_price',None) or 0
  lid=_eat.list_for_sale(exchange,args.feature_id,local_id,bp,price)
  result={'status':'ok','listing_id':lid}
 elif verb=='listings':result={'listings':_eat.open_listings(exchange,feature_id=getattr(args,'feature_id',None))}
 elif verb=='cancel-listing':_eat.cancel_listing(exchange,args.listing_id,local_id);result={'status':'ok','listing_id':args.listing_id}
 elif verb=='fill-listing':_eat.fill_listing(exchange,str(exchange.root),args.listing_id,local_id);result={'status':'ok','listing_id':args.listing_id}
 elif verb=='deprecate':
  import time as _t
  exchange.append_audit_row({'kind':'EQUITY_DEPRECATED','feature_id':args.feature_id,'creator_id':args.creator_id,'reason':getattr(args,'reason',''),'at_unix':_t.time(),'at':str(_t.time())})
  result={'status':'ok','feature_id':args.feature_id}
 elif verb=='register-replica':
  import time as _t
  chunks=getattr(args,'chunk_indices',None)
  exchange.append_audit_row({'kind':'REPLICA_REGISTERED','feature_id':args.feature_id,'peer_id':local_id,'artifact_hash':getattr(args,'artifact_hash',''),'chunk_indices':chunks,'at_unix':_t.time(),'at':str(_t.time())})
  result={'status':'ok','feature_id':args.feature_id}
 elif verb=='auto-buy':result=_eat.auto_buy(exchange,str(exchange.root),local_id,config=config)
 elif verb=='auto-sell':result=_eat.auto_sell(exchange,str(exchange.root),local_id,config=config)
 elif verb in ('challenge','resolve-challenge','release-stake','challenge-status'):
  from . import provenance_stake as _ps
  if verb=='challenge':
   stake=getattr(args,'challenger_stake',None)
   result=_ps.file_challenge(exchange,args.feature_id,args.challenger_id,reference_feature_id=getattr(args,'reference_feature_id',''),evidence=getattr(args,'evidence',''),challenger_stake=stake)
  elif verb=='resolve-challenge':
   _ps.resolve_challenge(exchange,args.challenge_id,args.verdict,resolver_id=getattr(args,'resolver_id','local'))
   result={'status':'ok','challenge_id':args.challenge_id,'verdict':args.verdict}
  elif verb=='release-stake':released=_ps.release_mint_stake(exchange,args.feature_id);result={'status':'ok','feature_id':args.feature_id,'released':released}
  else:result=_ps.challenge_status(exchange,args.feature_id)
 elif verb=='cost':
  op=args.operation;ask=getattr(args,'ask_price_units',0);asize=getattr(args,'artifact_size_bytes',0);ecalls=getattr(args,'executor_calls_saved',1)
  result={'operation':op,'ask_price_units':ask,'artifact_size_bytes':asize,'executor_calls_saved':ecalls,'note':'cost breakdown via cost_model'}
 elif verb=='dek-unwrap':
  from . import session_dek as _sdek
  import base64
  priv_hex=args.private_key_hex
  priv_bytes=bytes.fromhex(priv_hex)
  all_rows=exchange.audit_rows()
  listing_row=next((r for r in all_rows if r.get('kind')=='EQUITY_LISTING' and r.get('listing_id')==args.listing_id),None)
  if not listing_row:raise ValueError(f'Listing {args.listing_id!r} not found or has no wrapped DEK')
  wrapped=listing_row.get('wrapped_dek')
  if not wrapped:raise ValueError(f'Listing {args.listing_id!r} has no wrapped DEK')
  dek=_sdek.unwrap_dek(base64.b64decode(wrapped),priv_bytes)
  result={'listing_id':args.listing_id,'dek_hex':dek.hex()}
 elif verb=='escrow-status':
  from . import escrow_timeout as _et
  result=_et.list_pending_escrows(exchange) if hasattr(_et,'list_pending_escrows') else {'status':'ok','escrows':[r for r in exchange.audit_rows() if r.get('kind')=='EQUITY_ESCROW']}
 elif verb=='trade-config':
  tv=getattr(args,'trade_verb',None)
  if tv=='show' or tv is None:result=_eat.load_config(str(exchange.root))
  elif tv=='show-presets':
   result={'presets':['conservative','balanced','aggressive'],'note':'use --preset <name> with trade-config set'}
  else:
   cfg2=_eat.load_config(str(exchange.root))
   for k in ('auto_buy_enabled','min_quality_wilson','min_adoption_count','max_price_multiplier','max_bp_per_feature','max_spend_per_run_units','max_adoption_rate','min_supply_pressure','min_remaining_adopters','min_lucrativity_score','lucrativity_window_days','auto_sell_enabled','min_return_multiplier','bp_to_sell_per_trigger','min_hold_bp_to_trigger','sell_on_near_depleted','sell_on_slowing'):
    v=getattr(args,k,None)
    if v is not None:
     section='auto_buy' if 'buy' in k or k in ('min_quality_wilson','min_adoption_count','max_price_multiplier','max_bp_per_feature','max_spend_per_run_units','max_adoption_rate','min_supply_pressure','min_remaining_adopters','min_lucrativity_score','lucrativity_window_days') else 'auto_sell'
     cfg2.setdefault(section,{})[k]=v
   preset=getattr(args,'preset',None)
   if preset:cfg2=_eat.apply_preset(cfg2,preset)
   if getattr(args,'auto_tune',False):cfg2=_eat.auto_tune_config(exchange,cfg2)
   _eat.save_config(str(exchange.root),cfg2)
   result=cfg2
 elif verb=='visibility':
  rows=[r for r in exchange.audit_rows() if r.get('kind')=='EQUITY_GRANT' and r.get('feature_id')==args.feature_id]
  vis=rows[0].get('visibility','public') if rows else 'public'
  result={'feature_id':args.feature_id,'visibility':vis}
 else:raise ValueError(f'Unknown equity verb: {verb!r}')
 return result


def run(args,config):
 from . import peer_exchange as pe
 exchange=pe.Exchange(pe.directory(config));group=args.exchange_group;verb=getattr(args,'exchange_verb',None);result=None
 if group in ('status','audit'):
  result = _run_status_audit(exchange, args, config, verb)
 elif group=='rank':
  result = _run_rank(exchange, args, config, verb)
 elif group=='settings':
  result = _run_settings(exchange, args, config, verb)
 elif group=='peer':
  result = _run_peer(exchange, args, config, verb)
 elif group=='feature':
  result = _run_feature(exchange, args, config, verb)
 elif group=='rule':
  result = _run_rule(exchange, args, config, verb)
 elif group=='ledger':
  result = _run_ledger(exchange, args, config, verb)
 elif group=='bundle':
  result = _run_bundle(exchange, args, config, verb, pe)
 elif group=='chunk':
  result = _run_chunk(exchange, args, config, verb)
 elif group=='market':
  result = _run_market(exchange, args, config, verb)
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
   if _addr:result={**_addr,'status':'ok','note':'Register this address as a bootstrap peer endpoint to expose your node to the internet: urace network bootstrap add --address https://<ip>:<port>'}
   else:result={'status':'error','error':'STUN probe failed — check network connectivity or try a different STUN server'}
  elif verb=='disconnect':
   import time as _t
   cfg=exchange.load();until=_t.time()+args.duration_minutes*60
   cfg['network_disconnected_until']=until
   from ._common import atomic_write_json
   atomic_write_json(exchange.root/'policy.json',cfg)
   result={'status':'disconnected','reconnects_after_unix':until,'duration_minutes':args.duration_minutes}
  elif verb=='reconnect':
   from ._common import atomic_write_json
   cfg=exchange.load();cfg.pop('network_disconnected_until',None)
   atomic_write_json(exchange.root/'policy.json',cfg)
   result={'status':'reconnected'}
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
   _settings=exchange.load()
   _net_mode=_settings.get('network_mode','intranet')
   result={'status':'stub','note':'local only — set network_mode=internet to enable'}
   if _net_mode in ('internet','hybrid'):
    _bp=_settings.get('bootstrap_peers',[])
    for _ep in _bp[:3]:
     try:
      import urllib.request as _ur,urllib.parse as _up,json as _j
      _url=_ep.rstrip('/')+'/urace/rpc/v1/find-node?'+_up.urlencode({'target_peer_id':args.target_peer_id})
      _req=_ur.Request(_url,headers={'Accept':'application/json'})
      with _ur.urlopen(_req,timeout=10) as _resp:
       result=_j.loads(_resp.read(65536))
      break
     except Exception as _e:
      result={'status':'rpc_error','endpoint':_ep,'error':str(_e)}
   exchange.append_audit_row({'kind':'FIND_NODE_REQUESTED','target_peer_id':args.target_peer_id,'requester_peer_id':local_id,'at_unix':_tfn.time(),'note':'v3 stub — Kademlia find_node RPC not yet wired to network transport'})
  elif verb=='shamir-deliver':
   import time as _tsd
   _sd_settings=exchange.load();_sd_net=_sd_settings.get('network_mode','intranet')
   result={'status':'stub','note':'local only — set network_mode=internet to enable'}
   if _sd_net in ('internet','hybrid'):
    _sd_bp=_sd_settings.get('bootstrap_peers',[])
    for _sd_ep in _sd_bp[:3]:
     try:
      import urllib.request as _sd_ur,json as _sd_j
      _sd_url=_sd_ep.rstrip('/')+'/urace/rpc/v1/shamir-deliver'
      _sd_body=_sd_j.dumps({'feature_id':args.feature_id,'holder_peer_id':args.holder_peer_id,'share_index':args.share_index}).encode()
      _sd_req=_sd_ur.Request(_sd_url,data=_sd_body,headers={'Content-Type':'application/json'})
      with _sd_ur.urlopen(_sd_req,timeout=10) as _sd_resp:result=_sd_j.loads(_sd_resp.read(65536))
      break
     except Exception as _sd_e:result={'status':'rpc_error','endpoint':_sd_ep,'error':str(_sd_e)}
   exchange.append_audit_row({'kind':'SHAMIR_DELIVER_REQUESTED','feature_id':args.feature_id,'holder_peer_id':args.holder_peer_id,'share_index':args.share_index,'at_unix':_tsd.time()})
  elif verb=='tail-sync':
   _ts_settings=exchange.load();_ts_net=_ts_settings.get('network_mode','intranet')
   result={'status':'stub','note':'local only — set network_mode=internet to enable'}
   if _ts_net in ('internet','hybrid'):
    from . import ledger_sync as _ls
    _ts_bp=_ts_settings.get('bootstrap_peers',[])
    for _ts_ep in _ts_bp[:3]:
     try:
      import hashlib as _tsh,json as _tsj
      _tail_data=_ls.fetch_tail_from_peer(_ts_ep)
      _ts_rows=exchange.audit_rows()
      _ts_result=_ls.apply_tail_payload(_ts_rows,_tail_data)
      _ts_attest=_ls.build_sync_attestation(args.from_peer_id,_tsh.sha256(_tsj.dumps(_tail_data,sort_keys=True).encode()).hexdigest(),len(_ts_result['merged']),_ts_result['added'])
      try:
       from .signed_ledger import Ledger as _SL
       _SL(exchange.root/'signed-audit').append('LEDGER_SYNC_ATTESTED',_ts_attest)
      except Exception:pass
      exchange.event('LEDGER_SYNC_COMPLETED',peer=args.from_peer_id,added=_ts_result['added'],skipped=_ts_result['skipped'])
      result={'status':'ok','added':_ts_result['added'],'skipped':_ts_result['skipped'],'attestation':_ts_attest}
      break
     except Exception as _ts_e:result={'status':'rpc_error','endpoint':_ts_ep,'error':str(_ts_e)}
  elif verb=='reachability':
   from . import nat_check as _nc
   cap=_nc.check_node_capability(timeout=getattr(args,'timeout',5.0))
   _exch_cfg=exchange.load()
   _active_tunnel=_exch_cfg.get('active_tunnel_endpoint')
   if _active_tunnel:
    cap['can_bootstrap']=True;cap['can_relay']=True
    if 'bootstrap' not in cap.get('recommended_roles',[]):cap.setdefault('recommended_roles',[]).append('bootstrap')
    if 'relay' not in cap.get('recommended_roles',[]):cap.setdefault('recommended_roles',[]).append('relay')
    cap.setdefault('reasons',{})['bootstrap']=f'active tunnel endpoint: {_active_tunnel}'
    cap['reasons']['relay']=f'active tunnel endpoint: {_active_tunnel}'
    cap['active_tunnel_endpoint']=_active_tunnel
   role_filter=getattr(args,'role_filter',None)
   if role_filter:
    wanted={r.strip() for r in role_filter.split(',')}
    cap['role_filter']=list(wanted)
    cap['filtered_recommended']=[r for r in cap['recommended_roles'] if r in wanted]
   result={**cap,'status':'ok'}
  elif verb=='setup-node':
   from . import nat_check as _nc
   from ._common import atomic_write_json
   cap=_nc.check_node_capability(timeout=getattr(args,'timeout',5.0))
   _guide=_build_network_guide(cap)
   if getattr(args,'guide',False):
    # Guide-only mode: no config changes — purely advisory
    result={'status':'ok','guide':_guide,'nat_type':cap['nat_type'],'public_ip':cap.get('public_ip'),'upnp_available':cap['upnp_available'],'can_bootstrap':cap['can_bootstrap'],'can_relay':cap['can_relay']}
    if not getattr(args,'json',False):
     _print_network_guide(_guide)
     return 0
   else:
    _cfg=exchange.load()
    # delivery + block_sealer are always-on (outbound only) — nat_check never generates them.
    # Merge so setup-node never strips roles that don't require inbound reachability.
    _ALWAYS_ON={'delivery','block_sealer'}
    _roles=list(set(cap['recommended_roles'])|_ALWAYS_ON)
    _cfg['node_roles']=_roles
    _cfg['enabled']=True
    _cfg['network']=True
    _mode_rank={'intranet':0,'hybrid':1,'internet':2}
    if _mode_rank.get(cap['recommended_network_mode'],0)>_mode_rank.get(_cfg.get('network_mode','hybrid'),0):
     _cfg['network_mode']=cap['recommended_network_mode']
    atomic_write_json(exchange.root/'policy.json',_cfg)
    # Auto-open UPnP port if relay role and UPnP available
    if cap['can_relay'] and cap['upnp_available']:
     try:_nc.auto_open_upnp_port()
     except Exception:pass
    result={
     'nat_type':cap['nat_type'],'public_ip':cap.get('public_ip'),'upnp_available':cap['upnp_available'],
     'node_roles_set':_roles,'network_mode_set':_cfg.get('network_mode'),
     'can_bootstrap':cap['can_bootstrap'],'can_relay':cap['can_relay'],
     'status':'ok','guide':_guide,
     'note':'Node roles configured. Run: urace network serve --host 0.0.0.0 --port 7301' if (cap['can_bootstrap'] or cap['can_relay']) else 'Running as consumer+creator — no server required'
    }
  elif verb=='setup-port-forward':
   import subprocess as _spf,socket as _spf_sock
   from . import ddns as _ddns
   _spf_port=getattr(args,'port',7301) or 7301
   # 1. Public IP via STUN or HTTP fallback
   _pub_ip=None
   try:
    from . import stun_client as _st2
    _sa=_st2.get_public_address('stun.l.google.com',19302,timeout=5.0)
    if _sa:_pub_ip=_sa.get('ip')
   except Exception:pass
   if not _pub_ip:
    _pub_ip=_ddns.get_current_public_ip(timeout=5.0)
   # 2. Local IP via socket
   _local_ip=None
   try:
    with _spf_sock.socket(_spf_sock.AF_INET,_spf_sock.SOCK_DGRAM) as _s2:
     _s2.connect(('8.8.8.8',80));_local_ip=_s2.getsockname()[0]
   except Exception:_local_ip='unknown'
   # 3. Gateway — OS-agnostic (Linux/macOS/Windows)
   _gateway=None
   import sys as _sys_spf
   try:
    if _sys_spf.platform=='win32':
     _rout=_spf.run(['route','print','0.0.0.0'],capture_output=True,text=True,timeout=5)
     for _ln in _rout.stdout.splitlines():
      _parts=_ln.split()
      if len(_parts)>=3 and _parts[0]=='0.0.0.0':_gateway=_parts[2];break
    elif _sys_spf.platform=='darwin':
     _rout=_spf.run(['netstat','-nr'],capture_output=True,text=True,timeout=5)
     for _ln in _rout.stdout.splitlines():
      _parts=_ln.split()
      if _parts and _parts[0] in('default','0/1'):_gateway=_parts[1] if len(_parts)>1 else None;break
    else:
     _rout=_spf.run(['ip','route'],capture_output=True,text=True,timeout=5)
     for _ln in _rout.stdout.splitlines():
      if _ln.startswith('default'):
       _parts=_ln.split()
       if len(_parts)>=3:_gateway=_parts[2];break
   except Exception:pass
   if not _gateway:
    # Fallback: assume .1 of local subnet
    if _local_ip and _local_ip!='unknown':
     _gateway='.'.join(_local_ip.split('.')[:3])+'.1'
     if not _gateway:_gateway='unknown'
    else:_gateway='unknown'
   # 4. Optional DuckDNS configuration
   _ddns_token=getattr(args,'ddns_token',None)
   _ddns_domain=getattr(args,'ddns_domain',None)
   _ddns_url=None
   _ddns_note=None
   if _ddns_token and _ddns_domain:
    _ddns_url=f'https://{_ddns_domain}.duckdns.org:{_spf_port}'
    _test_ip=_pub_ip or ''
    _ddns_ok=False
    if _test_ip:
     _ddns_ok=_ddns.update_duckdns(_ddns_token,_ddns_domain,_test_ip)
    _ddns_note='DuckDNS updated OK' if _ddns_ok else 'DuckDNS update failed — check token/domain'
    # Store in policy
    from ._common import atomic_write_json as _awj3
    _pcfg=exchange.load()
    _pcfg['ddns_token']=_ddns_token
    _pcfg['ddns_domain']=_ddns_domain
    _pcfg['ddns_url']=_ddns_url
    try:_awj3(exchange.root/'policy.json',_pcfg)
    except Exception:pass
   # 5. Build result
   _direct_url=f'https://{_pub_ip}:{_spf_port}' if _pub_ip else None
   _instruct={
    'summary':f'Forward port {_spf_port} (TCP) on your router to {_local_ip}:{_spf_port}',
    'step1':f'Open your router admin page (usually http://{_gateway})',
    'step2':"Find 'Port Forwarding' or 'Virtual Server' section",
    'step3':f'Add rule: External port {_spf_port} → Internal IP {_local_ip} port {_spf_port}, protocol TCP',
    'step4':f'Save and test: curl {_direct_url}/exchange/ping' if _direct_url else 'Save and test from another device on the internet',
   }
   if _ddns_url:_instruct['ddns_note']='If your ISP changes your IP, use ddns_url instead of direct_url'
   result={'status':'ok','public_ip':_pub_ip,'local_ip':_local_ip,'gateway':_gateway,'port':_spf_port,'instructions':_instruct}
   if _direct_url:result['direct_url']=_direct_url
   if _ddns_url:result['ddns_url']=_ddns_url
   if _ddns_note:result['ddns_status']=_ddns_note
  elif verb=='request-log':
   from .freeform_routing import get_request_log
   entries=get_request_log(limit=args.limit)
   if getattr(args,'json',False):
    import dataclasses as _dc
    print(json.dumps([_dc.asdict(e) for e in entries]));return 0
   for e in entries:
    print(f"{e.phase:8s} {e.request_id[:8]} {e.target_id or '-':20s} lat={e.latency_ms:.1f}ms err={e.error or '-'}")
   return 0
  else:
   if getattr(args,'install_service',False):
    import os as _os,sys as _sys,shutil as _sh
    _svc_port=getattr(args,'port',0) or 7301
    _svc_tunnel=getattr(args,'tunnel','auto') or 'auto'
    _urace_bin=_sh.which('urace') or 'urace'
    if _sys.platform=='darwin':
     # macOS — launchd user agent
     _svc_dir=Path(_os.path.expanduser('~/Library/LaunchAgents'))
     _svc_dir.mkdir(parents=True,exist_ok=True)
     _svc_path=_svc_dir/'com.urace.exchange.plist'
     _svc_content=f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.urace.exchange</string>
  <key>ProgramArguments</key><array>
    <string>{_urace_bin}</string>
    <string>exchange</string><string>network</string><string>serve</string>
    <string>--port</string><string>{_svc_port}</string>
    <string>--tunnel</string><string>{_svc_tunnel}</string>
  </array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>{_os.path.expanduser('~/.urace/exchange.log')}</string>
  <key>StandardErrorPath</key><string>{_os.path.expanduser('~/.urace/exchange.log')}</string>
</dict></plist>
'''
     _svc_path.write_text(_svc_content)
     print(json.dumps({'status':'installed','path':str(_svc_path),'next':f'launchctl load {_svc_path}','platform':'macOS'}));return 0
    elif _sys.platform=='win32':
     # Windows — Task Scheduler via schtasks
     _task_name='URACEExchange'
     _cmd=f'schtasks /create /tn "{_task_name}" /tr "\\"{_urace_bin}\\" exchange network serve --port {_svc_port} --tunnel {_svc_tunnel}" /sc onlogon /ru %USERNAME% /f'
     print(json.dumps({'status':'instructions','platform':'Windows','command':_cmd,'note':'Run the command above in an elevated PowerShell to register the scheduled task. It will start on login and restart automatically.'}));return 0
    else:
     # Linux — systemd user service
     _svc_dir=Path(_os.path.expanduser('~/.config/systemd/user'))
     _svc_dir.mkdir(parents=True,exist_ok=True)
     _svc_path=_svc_dir/'urace-exchange.service'
     _svc_content=f'[Unit]\nDescription=URACE P2P Exchange Node\nAfter=network-online.target\nStartLimitIntervalSec=0\n\n[Service]\nExecStart={_urace_bin} exchange network serve --port {_svc_port} --tunnel {_svc_tunnel}\nRestart=always\nRestartSec=10\n\n[Install]\nWantedBy=default.target\n'
     _svc_path.write_text(_svc_content)
     print(json.dumps({'status':'installed','path':str(_svc_path),'next':'systemctl --user enable --now urace-exchange','platform':'Linux'}));return 0
   _tunnel_provider=getattr(args,'tunnel','none')
   if _tunnel_provider!='none':
    _effective_host='127.0.0.1'
    _effective_port=getattr(args,'port',0) or 7301
   else:
    _effective_host=args.host
    _effective_port=args.port
   _user_stop=[False]
   def _url_priority_key(url):
    # cloudflare named (permanent) > quicktunnel > lhr.life > others
    if 'cfargotunnel.com' in url:return 0
    if 'trycloudflare.com' in url:return 1
    if 'lhr.life' in url:return 2
    return 3
   def _merge_peer_urls(existing,new_urls):
    # Keep cloudflare URLs first, then lhr, then others; cap at 3 per node.
    combined=[]
    seen=set()
    for u in sorted(new_urls,key=_url_priority_key)+existing:
     if u not in seen:
      combined.append(u)
      seen.add(u)
    return combined[:3]
   def _do_serve(public_url=None,tunnel_proc=None,public_urls=None,immediate=False):
    # public_urls supersedes public_url when dual-tunnel is active.
    if public_urls is None:
     public_urls=[public_url] if public_url else []
    primary_url=public_urls[0] if public_urls else public_url
    if not 0<=_effective_port<=65535:raise ValueError('Port must be 0–65535')
    # F7-lite: load address book on serve startup
    from . import peer_address_book as _pab
    _book_path=exchange.root/'peer_address_book.json'
    _pab.init_address_book(_book_path)
    with pe.server(exchange,_effective_host,_effective_port) as server:
     with advertise(exchange,_effective_host,server.server_port):
      _serve_info={'status':'LISTENING','host':_effective_host,'port':server.server_port,'peer_id':exchange.identity()['peer_id']}
      if primary_url:
       _serve_info['tunnel_url']=primary_url
       _serve_info['bootstrap_endpoint']=primary_url
      if len(public_urls)>1:
       _serve_info['tunnel_urls']=public_urls
      _serve_cfg=exchange.load()
      _serve_roles=_serve_cfg.get('node_roles',[])
      # Tunnel provides inbound reachability even when NAT blocked it at init time.
      # Upgrade roles to relay (and bootstrap) when a tunnel URL is available,
      # regardless of what nat_check assigned before the tunnel existed.
      if public_urls:
       from ._common import atomic_write_json as _awj2
       _scfg2=exchange.load()
       if 'relay' not in _serve_roles:
        _serve_roles=list(set(_serve_roles)|{'relay','bootstrap'})
        _scfg2['node_roles']=_serve_roles
       _scfg2['active_tunnel_endpoint']=primary_url
       _scfg2['active_tunnel_endpoints']=list(public_urls)
       # Register all tunnel URLs in bootstrap_peers, deduped and ordered by priority.
       _bl2=_scfg2.setdefault('bootstrap_peers',[])
       _merged=_merge_peer_urls(_bl2,public_urls)
       for _u in _merged:
        if _u not in _bl2:_bl2.insert(0,_u)
       _scfg2['bootstrap_peers']=_merge_peer_urls(_bl2,public_urls)
       try:_awj2(exchange.root/'policy.json',_scfg2)
       except Exception:pass
      _relay_bw=exchange.load().get('relay_bandwidth_kbps',0)
      if _relay_bw>0:
       print(json.dumps({'status':'info','detail':f'relay bandwidth cap: {_relay_bw} KB/s'}))
      if 'relay' in _serve_roles or 'bootstrap' in _serve_roles or public_urls:
       import threading as _thr
       def _auto_announce(_imm=immediate,_urls=None):
        import time as _tat
        if _urls is None:
            _urls = list(public_urls)
        if not _imm:
         _tat.sleep(3)
        try:
         _eps=_urls
         if not _eps:
          from . import stun_client as _st
          _a=_st.get_public_address('stun.l.google.com',19302)
          if _a:_eps=[f"https://{_a['ip']}:{server.server_port}"]
         if _eps:
          _primary_ep=_eps[0]
          _c3=exchange.load()
          # Announce to bootstrap_peers (unauthenticated path, best-effort).
          _bp2=list(_c3.get('bootstrap_peers',[]))
          for _bep in _bp2:
           for _ep_i in _eps:
            try:
             pe.request(exchange,None,'bootstrap.announce',{'endpoint':_ep_i,'peer_id':exchange.identity().get('peer_id','')},bootstrap_endpoint=_bep)
            except Exception:pass
          # F7-lite: exchange address books with authenticated peers
          from . import peer_address_book as _pab_srv2
          _bk_srv=_pab_srv2.get_address_book()
          if _bk_srv is not None:
           _my_pid2=exchange.identity().get('peer_id','')
           for _pid2,_pdata2 in _c3.get('peers',{}).items():
            if _pdata2.get('blocked'):continue
            if not _pdata2.get('endpoint'):continue
            try:
             _ab_resp=pe.request(exchange,_pid2,'bootstrap.address_book',{})
             if isinstance(_ab_resp,dict) and _ab_resp.get('entries'):
              _bk_srv.merge(_ab_resp['entries'])
              _bk_srv.save()
            except Exception:pass
          # Gossip new URL to all authenticated peers that have a stored endpoint.
          _my_pid=exchange.identity().get('peer_id','')
          for _pid,_pdata in _c3.get('peers',{}).items():
           if _pdata.get('blocked'):continue
           _pep=_pdata.get('endpoint')
           if not _pep:continue
           try:pe.request(exchange,_pid,'bootstrap.update_endpoint',{'endpoint':_eps[0],'peer_id':_my_pid})
           except Exception:pass
          from ._common import atomic_write_json as _awj
          _c2=exchange.load();_bl=_c2.setdefault('bootstrap_peers',[])
          _c2['bootstrap_peers']=_merge_peer_urls(_bl,_eps)
          _c2['active_tunnel_endpoints']=_eps
          try:_awj(exchange.root/'policy.json',_c2)
          except Exception:pass
          _serve_info['bootstrap_endpoint']=_primary_ep
        except Exception:pass
       _thr.Thread(target=_auto_announce,daemon=True).start()
      print(json.dumps(_serve_info),flush=True)
      # Determine procs to watch (dual-tunnel aware).
      _all_procs=[]
      if hasattr(tunnel_proc,'_all_procs'):
       _all_procs=tunnel_proc._all_procs
      elif tunnel_proc is not None:
       _all_procs=[tunnel_proc]
      if _all_procs:
       import threading as _thr2,urllib.request as _ur
       def _tunnel_watchdog():
        # Reconnect only when ALL tunnel procs have died.
        import time as _twt
        while not _user_stop[0]:
         _twt.sleep(5)
         if all(p.poll() is not None for p in _all_procs):
          break
        if not _user_stop[0]:
         try:server.shutdown()
         except Exception:pass
       _thr2.Thread(target=_tunnel_watchdog,daemon=True).start()
       if primary_url:
        def _tunnel_healthcheck(_chk_urls=list(public_urls) or [primary_url]):
         import time as _tht
         _fail=0
         while not _user_stop[0]:
          _tht.sleep(60)
          if _user_stop[0]:break
          _any_ok=False
          for _cu in _chk_urls:
           try:
            r=_ur.urlopen(_cu+'/exchange/ping',timeout=10)
            if b'"status"' in r.read(256):
             _any_ok=True;break
           except Exception:pass
          if _any_ok:
           _fail=0
          else:
           _fail+=1
           if _fail>=2 and not _user_stop[0]:
            # ALL tunnel URLs unreachable 2× — force reconnect
            for _p in _all_procs:
             try:_p.terminate()
             except Exception:pass
            break
        _thr2.Thread(target=_tunnel_healthcheck,daemon=True).start()
      with selection_worker(exchange):
       try:server.serve_forever(poll_interval=.5)
       except KeyboardInterrupt:_user_stop[0]=True
   if _tunnel_provider!='none':
    from . import tunnel_server as _ts
    import time as _rt2
    _retry_n=0
    _is_reconnect=False
    _prev_provider=None
    while not _user_stop[0]:
     _retry_n+=1
     try:
      from pathlib import Path as _Path
      from . import tunnel_install as _ti_rc
      _cert_now=(_Path.home()/'.cloudflared'/'cert.pem').exists()
      _cf_now=bool(_ti_rc.find_cloudflared())
      if _cert_now and _cf_now and _prev_provider in ('localhost.run',None) and _tunnel_provider=='auto':
       print(json.dumps({'status':'info','detail':'cloudflared cert detected — upgrading to named tunnel'}))
      if _tunnel_provider=='auto':
       _th_ctx=_ts.DualTunnelHandle(_effective_port)
       _th_ctx._peer_id=exchange.identity().get('peer_id','')
      else:
       _th_ctx=_ts.TunnelHandle(_tunnel_provider,_effective_port)
      with _th_ctx as th:
       if not th.url:
        _rd=min(60,10*_retry_n)
        print(json.dumps({'status':'warn','detail':f'tunnel ({_tunnel_provider}) did not produce a URL, retry {_retry_n} in {_rd}s'}),flush=True)
        try:_rt2.sleep(_rd)
        except KeyboardInterrupt:_user_stop[0]=True
        continue
       _retry_n=0
       _pub_urls=th.urls if hasattr(th,'urls') else ([th.url] if th.url else [])
       _do_serve(public_url=th.url,tunnel_proc=th,public_urls=_pub_urls,immediate=_is_reconnect)
       _prev_provider=getattr(th,'provider',None)
       _is_reconnect=True
     except KeyboardInterrupt:_user_stop[0]=True
     except OSError as _oe:
      # Port still in use from previous session — wait and retry
      print(json.dumps({'status':'warn','detail':f'bind failed ({_oe}), retry {_retry_n} in 15s'}),flush=True)
      try:_rt2.sleep(15)
      except KeyboardInterrupt:_user_stop[0]=True
      continue
     except Exception as _ex:
      print(json.dumps({'status':'warn','detail':f'serve error ({_ex}), retry {_retry_n} in 10s'}),flush=True)
      try:_rt2.sleep(10)
      except KeyboardInterrupt:_user_stop[0]=True
      continue
     if _user_stop[0]:break
     print(json.dumps({'status':'info','detail':'tunnel dropped; reconnecting in 10s'}),flush=True)
     try:_rt2.sleep(10)
     except KeyboardInterrupt:_user_stop[0]=True
   else:
    # no-tunnel direct inbound: auto-start DDNS watcher if ddns_token stored in policy
    _notun_cfg=exchange.load()
    _notun_token=_notun_cfg.get('ddns_token')
    _notun_domain=_notun_cfg.get('ddns_domain')
    if _notun_token and _notun_domain:
     try:
      from . import ddns as _ddns_srv
      _ddns_srv.start_ddns_watcher(_notun_token,_notun_domain,interval=300)
      print(json.dumps({'status':'info','detail':f'DDNS watcher started for {_notun_domain}.duckdns.org (5-min interval)'}),flush=True)
     except Exception as _dex:
      print(json.dumps({'status':'warn','detail':f'DDNS watcher failed to start: {_dex}'}),flush=True)
    _do_serve()
   return 0
 elif group=='work':
  result = _run_work(exchange, args, config, verb)
 elif group=='equity':
  result = _run_equity(exchange, args, config, verb)
 elif group=='bridge':
  result = _run_bridge(exchange, args, config, verb)
 elif group=='reputation':
  result = _run_reputation(exchange, args, config, verb)
 elif group=='network-audit':
  result = _run_network_audit(exchange, args, config, verb)
 elif group=='reset':
  result = _run_reset(exchange, args, config, verb)
  if result in (0, 2): return result
 elif group=='compact':
  result = _run_compact(exchange, args, config, verb)
  if result == 1: return result
 elif group=='bootstrap':
  result = _run_bootstrap(exchange, args, config, verb, pe)
 elif group=='node':
  result = _run_node(exchange, args, config, verb)
 elif group=='settle':
  result = _run_settle(exchange, args, config, verb)
 elif group=='asset':
  result = _run_asset(exchange, args, config, verb)
 else:raise ValueError('Unknown exchange action')
 print(json.dumps(result,indent=2,sort_keys=True,default=str));return 0

from contextlib import contextmanager
@contextmanager
def advertise(exchange,host,port):
 if not exchange.load()['advertise']:yield;return
 try:from zeroconf import Zeroconf,ServiceInfo
 except ImportError:raise ValueError('Advertising requires pip install "urace[p2p]"')
 import ipaddress
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
