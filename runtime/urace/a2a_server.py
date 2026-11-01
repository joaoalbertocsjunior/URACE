"""Opt-in A2A 1.0 polling endpoint over the scoped application job core.

Single owner policy/identity per listener; loopback only. No discovery crawling,
model invocation, remote callback, or listener starts merely by importing this.
"""
from __future__ import annotations

import base64
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hmac
import json
import os
import re
import signal
import sys
import threading
import uuid

from .integration_bridge import (
    BridgeError, Jobs, IDENTIFIER, TERMINAL, atomic_write_json, digest,
    encoded, load_policy, receipt_lock, owner_lifetime,
)

PROTOCOL = '1.0'
MAX_REQUEST = 1048576
STATES = {
    'PENDING': 'TASK_STATE_SUBMITTED', 'RUNNING': 'TASK_STATE_WORKING',
    'COMPLETED': 'TASK_STATE_COMPLETED', 'CANCELLED': 'TASK_STATE_CANCELED',
    'FAILED': 'TASK_STATE_FAILED', 'TIMED_OUT': 'TASK_STATE_FAILED',
    'INTERRUPTED': 'TASK_STATE_FAILED', 'OUTPUT_LIMIT': 'TASK_STATE_FAILED',
}


class RpcError(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def fields(value, allowed, required=()):
    if not isinstance(value, dict) or set(value) - set(allowed) or any(k not in value for k in required):
        raise RpcError(-32602, 'Invalid or unsupported parameters')
    return value


def identifier(value):
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise RpcError(-32602, 'Bounded identifier required')
    return value


class Adapter:
    """Map protocol tasks to existing receipts; never infer product acceptance."""

    def __init__(self, policy, jobs):
        self.policy = policy
        self.jobs = jobs
        self.lock = threading.RLock()
        self.blocking_calls = threading.BoundedSemaphore(min(16, policy.limits["parallel_jobs"] + 2))

    def card(self, url):
        return {
            'name': 'URACE', 'description': 'Policy-scoped finite URACE operations. '
            'Send one data part containing command and params. Discover exact operations through MCP urace_operations or urace api commands. '
            'Operation completion does not establish product acceptance.',
            'version': '1.0.0',
            'supportedInterfaces': [{'url': url, 'protocolBinding': 'JSONRPC', 'protocolVersion': PROTOCOL}],
            'capabilities': {'streaming': False, 'pushNotifications': False},
            'defaultInputModes': ['application/json'], 'defaultOutputModes': ['application/json'],
            'securitySchemes': {'ownerBearer': {'httpAuthSecurityScheme': {'scheme': 'Bearer'}}},
            'securityRequirements': [{'schemes': {'ownerBearer': {'list': []}}}],
            'skills': [{'id': 'delegated-operation', 'name': 'Delegated URACE operation',
                        'description': 'Submit a typed operation allowed by the owner policy; poll or cancel its task. '
                        'Use messageId as a stable deduplication identity. Text inference and multi-turn task mutation are unsupported.',
                        'tags': ['autonomy', 'operations'],
                        'examples': ['{"command":"help","params":{}}']}],
        }

    def record_path(self, task_id):
        return self.jobs.path(task_id).with_suffix('.a2a.json')

    def record(self, task_id):
        try:
            path = self.record_path(task_id)
            if path.is_symlink():
                raise BridgeError('Invalid task')
            record = json.loads(path.read_text())
            if record['policy_sha256'] != self.policy.hash:
                raise BridgeError('Invalid task')
            return record
        except (BridgeError, OSError, ValueError, KeyError):
            raise RpcError(-32001, 'Task not found') from None

    def task(self, task_id, *, artifacts=True):
        record = self.record(task_id)
        try:
            row = self.jobs.status(task_id)
        except BridgeError:
            raise RpcError(-32001, 'Task not found') from None
        value = {
            'id': task_id, 'contextId': record['context_id'],
            'status': {'state': STATES[row['status']],
                       'timestamp': datetime.fromtimestamp(row['updated_unix'], timezone.utc).isoformat().replace('+00:00', 'Z')},
            'metadata': {'urace': {'project_id': row['project_id'], 'executor_id': row['executor_id'],
                                   'policy_sha256': row['policy_sha256'], 'bridge_status': row['status'],
                                   'acceptance': 'Operation completion only; product acceptance remains governed by URACE validators'}},
        }
        if artifacts:
            value['artifacts'] = []
            if row['status'] in TERMINAL:
                value['artifacts'].append({'artifactId': task_id + '-receipt', 'name': 'URACE operation receipt',
                                           'parts': [{'data': row, 'mediaType': 'application/json'}]})
        return value

    def send(self, params):
        fields(params, {'message', 'configuration', 'metadata'}, {'message'})
        if 'metadata' in params and not isinstance(params['metadata'],dict):
            raise RpcError(-32602, 'metadata must be an object')
        config = fields(params.get('configuration', {}), {'acceptedOutputModes', 'historyLength', 'returnImmediately'})
        if 'acceptedOutputModes' in config and (not isinstance(config['acceptedOutputModes'], list) or any(not isinstance(v,str) for v in config['acceptedOutputModes']) or 'application/json' not in config['acceptedOutputModes']):
            raise RpcError(-32005, 'Only application/json output is supported')
        if 'historyLength' in config and (type(config['historyLength']) is not int or config['historyLength'] < 0):
            raise RpcError(-32602, 'Invalid historyLength')
        if 'returnImmediately' in config and type(config['returnImmediately']) is not bool:
            raise RpcError(-32602, 'Invalid returnImmediately')
        message = fields(params['message'], {'messageId', 'role', 'parts', 'contextId', 'taskId', 'metadata'}, {'messageId', 'role', 'parts'})
        if 'metadata' in message and not isinstance(message['metadata'],dict):
            raise RpcError(-32602, 'metadata must be an object')
        message_id = identifier(message['messageId'])
        if message['role'] != 'ROLE_USER':
            raise RpcError(-32602, 'Client role must be ROLE_USER')
        if message.get('taskId'):
            self.record(message['taskId'])
            raise RpcError(-32004, 'Submit a new messageId for a new finite operation; task continuation is unsupported')
        parts = message['parts']
        if not isinstance(parts, list) or len(parts) != 1 or not isinstance(parts[0], dict) or set(parts[0]) - {'data', 'mediaType'} or 'data' not in parts[0] or parts[0].get('mediaType', 'application/json') != 'application/json':
            raise RpcError(-32005, 'Send exactly one application/json data part containing command and params')
        operation = fields(parts[0]['data'], {'command', 'params'}, {'command'})
        if not isinstance(operation['command'], str) or not isinstance(operation.get('params', {}), dict):
            raise RpcError(-32602, 'Typed command and params required')
        request_id = 'a2a:' + digest(message_id)
        context = identifier(message['contextId']) if 'contextId' in message else str(uuid.uuid5(uuid.NAMESPACE_URL, self.policy.hash + request_id))
        task_id = digest({'request_id': request_id, 'policy': self.policy.hash})[:32]
        path = self.record_path(task_id)
        record = {'schema': 'urace-a2a-v1', 'task_id': task_id, 'context_id': context,
                  'message_sha256': digest({'context': context, 'operation': operation}), 'policy_sha256': self.policy.hash}
        with self.lock, receipt_lock(path):
            if path.exists() and self.record(task_id) != record:
                raise RpcError(-32602, 'messageId already belongs to different content/context')
            # Validate before recording; Jobs independently rechecks authority/pause.
            self.policy.authorize(operation['command'], operation.get('params', {}))
            row = self.jobs.submit(operation['command'], operation.get('params', {}), request_id)
            atomic_write_json(path, record)
        if not config.get('returnImmediately', False):
            self.jobs.wait(row['job_id'])
        return {'task': self.task(row['job_id'])}

    def list_tasks(self, params):
        fields(params, {'contextId', 'status', 'pageSize', 'pageToken', 'historyLength', 'includeArtifacts', 'statusTimestampAfter'})
        size = params.get('pageSize', 50)
        if type(size) is not int or not 1 <= size <= 100:
            raise RpcError(-32602, 'pageSize must be 1..100')
        if 'historyLength' in params and (type(params['historyLength']) is not int or params['historyLength'] < 0):
            raise RpcError(-32602, 'Invalid historyLength')
        if 'includeArtifacts' in params and type(params['includeArtifacts']) is not bool:
            raise RpcError(-32602, 'Invalid includeArtifacts')
        if 'contextId' in params:
            identifier(params['contextId'])
        if 'pageToken' in params and not isinstance(params['pageToken'],str):
            raise RpcError(-32602, 'Invalid page token')
        if 'status' in params and (not isinstance(params['status'],str) or params['status'] not in set(STATES.values())):
            raise RpcError(-32602, 'Invalid task status')
        after = None
        if 'statusTimestampAfter' in params:
            try:
                after = datetime.fromisoformat(params['statusTimestampAfter'].replace('Z', '+00:00'))
                if after.tzinfo is None:
                    raise ValueError()
            except (ValueError, TypeError, AttributeError):
                raise RpcError(-32602, 'Timezone-qualified timestamp required') from None
        fingerprint = digest({k: v for k, v in params.items() if k != 'pageToken'})
        cursor = None
        if params.get('pageToken'):
            try:
                cursor = json.loads(base64.urlsafe_b64decode(params['pageToken'].encode()))
                if set(cursor) != {'filter', 'key'} or cursor['filter'] != fingerprint or not isinstance(cursor['key'], list) or len(cursor['key']) != 2 or any(not isinstance(x, str) for x in cursor['key']):
                    raise ValueError()
            except (ValueError, TypeError, AttributeError):
                raise RpcError(-32602, 'Invalid page token or changed filters') from None
        rows = []
        for path in self.policy.storage.glob('*.a2a.json'):
            try:
                task = self.task(path.name.removesuffix('.a2a.json'), artifacts=params.get('includeArtifacts', False))
            except RpcError:
                continue
            if 'contextId' in params and task['contextId'] != params['contextId']:
                continue
            if 'status' in params and task['status']['state'] != params['status']:
                continue
            if after and datetime.fromisoformat(task['status']['timestamp'].replace('Z', '+00:00')) < after:
                continue
            rows.append(task)
        key = lambda task: [task['status']['timestamp'], task['id']]
        rows.sort(key=key, reverse=True)
        total = len(rows)
        if cursor:
            rows = [task for task in rows if key(task) < cursor['key']]
        page = rows[:size]
        next_token = base64.urlsafe_b64encode(encoded({'filter': fingerprint, 'key': key(page[-1])})).decode() if len(rows) > size else ''
        return {'tasks': page, 'nextPageToken': next_token, 'pageSize': size, 'totalSize': total}

    def dispatch(self, method, params):
        if method == 'SendMessage':
            if not self.blocking_calls.acquire(blocking=False):
                raise RpcError(-32000, 'Send queue busy; retry with the same messageId')
            try:
                return self.send(params)
            finally:
                self.blocking_calls.release()
        if method == 'ListTasks':
            return self.list_tasks(params)
        if method in {'GetTask', 'CancelTask'}:
            fields(params, {'id', 'historyLength'} if method == 'GetTask' else {'id', 'metadata'}, {'id'})
            if 'historyLength' in params and (type(params['historyLength']) is not int or params['historyLength'] < 0):
                raise RpcError(-32602, 'Invalid historyLength')
            task = self.task(params['id'])
            if method == 'CancelTask':
                if task['status']['state'] in {'TASK_STATE_COMPLETED', 'TASK_STATE_FAILED', 'TASK_STATE_CANCELED'}:
                    raise RpcError(-32002, 'Task is not cancelable')
                self.jobs.cancel(params['id'])
                self.jobs.wait(params['id'])
                task = self.task(params['id'])
            return task
        if 'PushNotification' in method:
            raise RpcError(-32003, 'Push notifications are not supported')
        if method == 'GetExtendedAgentCard':
            raise RpcError(-32007, 'Extended Agent Card not configured')
        if method in {'SendStreamingMessage', 'SubscribeToTask'}:
            raise RpcError(-32004, 'Optional operation not supported')
        raise RpcError(-32601, 'Method not found')


class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.0'

    def setup(self):
        super().setup()
        self.connection.settimeout(10)

    def log_message(self, *args):
        pass  # Never log credentials or operation payloads.

    def reply(self, status, value):
        body = encoded(value)
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('A2A-Version', PROTOCOL)
        self.end_headers()
        self.wfile.write(body)

    def admitted(self, *, discovery=False):
        headers = self.headers
        if headers.get('Origin') is not None:
            self.reply(403, {'error': 'Browser origins are not supported'})
            return False
        auth = headers.get('Authorization', '')
        if len(headers.get_all('Authorization', [])) != 1 or not hmac.compare_digest(auth.encode(), ('Bearer ' + self.server.token).encode()):
            self.reply(401, {'error': 'Bearer authentication required'})
            return False
        if not discovery and headers.get('A2A-Version') != PROTOCOL:
            self.reply(400, {'jsonrpc': '2.0', 'id': None, 'error': {'code': -32009, 'message': 'Protocol version not supported; supported version: 1.0'}})
            return False
        return True

    def do_GET(self):
        if not self.admitted(discovery=True):
            return
        if self.path == '/.well-known/agent-card.json':
            self.reply(200, self.server.adapter.card(self.server.url))
        else:
            self.reply(404, {'error': 'Not found'})

    def do_POST(self):
        if not self.admitted():
            return
        if self.path != '/rpc':
            self.reply(404, {'error': 'Not found'})
            return
        if self.headers.get('Content-Type', '').split(';')[0].strip() != 'application/json':
            self.reply(415, {'error': 'application/json required'})
            return
        try:
            if self.headers.get('Transfer-Encoding') or len(self.headers.get_all('Content-Length', [])) != 1:
                raise ValueError()
            size = int(self.headers['Content-Length'])
            if not 0 < size <= MAX_REQUEST:
                raise ValueError()
        except (ValueError, TypeError):
            self.reply(413, {'error': 'Bounded Content-Length required'})
            return
        identifier_ = None
        try:
            raw = self.rfile.read(size)
            if len(raw) != size:
                raise ValueError()
            request = json.loads(raw, parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
        except (ValueError, RecursionError):
            self.reply(200, {'jsonrpc': '2.0', 'id': None, 'error': {'code': -32700, 'message': 'Invalid JSON'}})
            return
        try:
            if not isinstance(request, dict) or set(request) - {'jsonrpc', 'id', 'method', 'params'} or any(k not in request for k in ('jsonrpc', 'id', 'method')):
                raise RpcError(-32600, 'Invalid JSON-RPC request')
            if request['jsonrpc'] != '2.0' or type(request['id']) not in (str, int) or not isinstance(request['method'], str):
                raise RpcError(-32600, 'Invalid JSON-RPC request')
            identifier_ = request['id']
            result = self.server.adapter.dispatch(request['method'], request.get('params', {}))
            self.reply(200, {'jsonrpc': '2.0', 'id': identifier_, 'result': result})
        except RpcError as error:
            self.reply(200, {'jsonrpc': '2.0', 'id': identifier_, 'error': {'code': error.code, 'message': str(error)}})
        except BridgeError as error:
            self.reply(200, {'jsonrpc': '2.0', 'id': identifier_, 'error': {'code': -32602, 'message': str(error)}})
        except Exception as error:
            self.reply(200, {'jsonrpc': '2.0', 'id': identifier_, 'error': {'code': -32603, 'message': 'Internal error: ' + type(error).__name__}})


class HttpServer(ThreadingHTTPServer):
    daemon_threads = False
    block_on_close = True

    def __init__(self, adapter, token, port=0):
        if not isinstance(token, str) or not re.fullmatch(r'[A-Za-z0-9_.~+/-]{32,512}', token):
            raise ValueError('A2A bearer secret must contain 32..512 token characters')
        self.adapter = adapter
        self.token = token
        self.slots = threading.BoundedSemaphore(32)
        super().__init__(('127.0.0.1', port), Handler)
        self.url = 'http://127.0.0.1:' + str(self.server_port) + '/rpc'

    def process_request(self, request, address):
        if not self.slots.acquire(blocking=False):
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, address)
        except BaseException:
            self.slots.release()
            raise

    def process_request_thread(self, request, address):
        try:
            super().process_request_thread(request, address)
        finally:
            self.slots.release()


def serve(parser, policy_path=None, *, port=8765, token_env='URACE_A2A_TOKEN'):
    jobs = server = None
    try:
        if not isinstance(token_env, str) or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', token_env):
            raise ValueError('Invalid bearer environment variable name')
        policy = load_policy(parser, policy_path)
        token = os.environ.get(token_env, '')
        jobs = Jobs(policy, private_env=(token_env,))
        server = HttpServer(Adapter(policy, jobs), token, port)
        print(json.dumps({'transport': 'a2a', 'protocol': PROTOCOL, 'url': server.url,
                          'read_only': policy.read_only, 'paused': jobs.pause_check()}), file=sys.stderr, flush=True)
        with owner_lifetime():
            server.serve_forever(poll_interval=.2)
    except KeyboardInterrupt:
        return 0
    except (ValueError, OSError, KeyError) as error:
        print('URACE A2A: ' + str(error), file=sys.stderr)
        return 2
    finally:
        if jobs:
            jobs.close()
        if server:
            server.server_close()
    return 0
