"""Explicit protocol bindings around a common operation core; no inferred semantic translation."""
def describe():
 from .mcp_server import PROTOCOL
 from .a2a_server import PROTOCOL as A2A_PROTOCOL
 from .peer_exchange import SCHEMA as PEER_SCHEMA
 from .tokenomics import TOKEN_UNIT
 return {'schema':'urace-protocol-bindings-v1','canonical_core':'CLI grammar, typed arguments, scoped operations, jobs and native accounting','universal_translation':False,'tokenomics':TOKEN_UNIT,'bindings':[
 {'id':'cli','pattern':['request-response','explicit-follow-stream'],'authority':'local owner','enabled':'on invocation'},
 {'id':'typed-api','pattern':['request-response','explicit-NDJSON-stream'],'authority':'same local command authority; not a network authorization boundary'},
 {'id':'mcp-stdio','protocol_version':PROTOCOL,'pattern':['JSON-RPC','scoped-resources','async-job-polling'],'authority':'explicit integration capability policy','unsupported':['resource-subscriptions','arbitrary-network-transport']},
 {'id':'a2a-loopback','protocol_version':A2A_PROTOCOL+' polling subset','pattern':['SendMessage','GetTask','ListTasks','CancelTask'],'authority':'bearer authentication plus capability policy','unsupported':['public-TLS','push','streaming','full-conformance']},
 {'id':'peer-artifacts','protocol_version':PEER_SCHEMA+' over HTTPS/TLS1.3 and JSON-RPC2.0','pattern':['exchange.info','exchange.offers','exchange.receive'],'authority':'pinned mutual TLS, out-of-band hybrid identities and per-peer/per-feature permissions','application_encryption':'ML-KEM-768/HKDF-SHA-384/AES-256-GCM; no claim of post-quantum TLS','default_enabled':False,'incorporation':'quarantine; never execution','discovery':'optional DNS-SD; discovered identity is untrusted'}],
 'adapter_requirements':['declared schema/version','authentication and authority mapping','delivery/retry/deduplication semantics','deadlines and cancellation behavior','resource limits and attributable receipts','explicitly reject unsupported patterns'],
 'limitations':'Shared representation does not make protocol security, ordering, delivery guarantees or task lifecycle interchangeable'}
