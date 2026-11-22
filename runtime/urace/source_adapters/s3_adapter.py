"""S3-compatible object storage source adapter — observes bucket contents; acts with upload/download."""
from __future__ import annotations

from typing import Any

from ._base import NullSourceAdapter, SourceUnavailableError, _get_source, _set_source
from . import SOURCE_REGISTRY
from .._common import now

try:
    import boto3 as _boto3
    _AVAILABLE = True
except ImportError:
    _boto3 = None  # type: ignore[assignment]
    _AVAILABLE = False


def _require_boto3() -> None:
    if not _AVAILABLE:
        raise SourceUnavailableError('pip install "urace[sources-s3]"')


class S3Adapter(NullSourceAdapter):
    kind = 's3'

    def add_args(self, subparser: Any) -> None:
        subparser.add_argument('--bucket', default=None, help='S3 bucket name')
        subparser.add_argument('--prefix', default='', help='Key prefix to observe')
        subparser.add_argument('--endpoint-url', dest='endpoint_url', default=None,
                               help='Custom endpoint URL (for S3-compatible APIs)')
        subparser.add_argument('--region', default=None)
        subparser.add_argument('--access-key-env', dest='access_key_env',
                               default='AWS_ACCESS_KEY_ID')
        subparser.add_argument('--secret-key-env', dest='secret_key_env',
                               default='AWS_SECRET_ACCESS_KEY')

    def validate(self, args: Any) -> dict[str, Any]:
        name = getattr(args, 'name', None) or getattr(args, 'id', None) or ''
        bucket = getattr(args, 'bucket', None) or ''
        if not name:
            raise ValueError('source add --kind s3 requires a name')
        if not bucket:
            raise ValueError('source add --kind s3 requires --bucket')
        return {
            'kind': self.kind,
            'bucket': bucket,
            'prefix': getattr(args, 'prefix', '') or '',
            'endpoint_url': getattr(args, 'endpoint_url', None),
            'region': getattr(args, 'region', None),
            'access_key_env': getattr(args, 'access_key_env', None) or 'AWS_ACCESS_KEY_ID',
            'secret_key_env': getattr(args, 'secret_key_env', None) or 'AWS_SECRET_ACCESS_KEY',
        }

    def _add(self, config: dict, state: dict, source_id: str, **kwargs: Any) -> dict:
        return {
            'id': source_id,
            'kind': self.kind,
            'enabled': True,
            'added_at': now(),
            'status': 'CONFIGURED',
            'status_history': [{'status': 'CONFIGURED', 'at': now()}],
            'adapter_state': {
                'bucket': kwargs.get('bucket', ''),
                'prefix': kwargs.get('prefix', ''),
                'endpoint_url': kwargs.get('endpoint_url'),
                'region': kwargs.get('region'),
                'access_key_env': kwargs.get('access_key_env', 'AWS_ACCESS_KEY_ID'),
                'secret_key_env': kwargs.get('secret_key_env', 'AWS_SECRET_ACCESS_KEY'),
                'last_sync_at': None,
                'object_count': None,
                'enabled_actions': [],
            },
        }

    def _client(self, astate: dict) -> Any:
        import os
        _require_boto3()
        return _boto3.client(
            's3',
            endpoint_url=astate.get('endpoint_url'),
            region_name=astate.get('region'),
            aws_access_key_id=os.environ.get(astate.get('access_key_env', 'AWS_ACCESS_KEY_ID'), ''),
            aws_secret_access_key=os.environ.get(astate.get('secret_key_env', 'AWS_SECRET_ACCESS_KEY'), ''),
        )

    def _sync(self, config: dict, state: dict, source_id: str) -> dict:
        _require_boto3()
        record = _get_source(state, source_id)
        if not record:
            return {'synced': False, 'reason': 'source not found'}
        astate = record.get('adapter_state', {})
        bucket = astate.get('bucket', '')
        prefix = astate.get('prefix', '')
        if not bucket:
            return {'synced': False, 'reason': 'no bucket configured'}
        try:
            client = self._client(astate)
            paginator = client.get_paginator('list_objects_v2')
            count = sum(
                page.get('KeyCount', 0)
                for page in paginator.paginate(Bucket=bucket, Prefix=prefix)
            )
        except Exception as exc:
            return {'synced': False, 'reason': str(exc)}
        astate['last_sync_at'] = now()
        astate['object_count'] = count
        _set_source(state, source_id, record)
        return {'synced': True, 'bucket': bucket, 'prefix': prefix, 'object_count': count}

    def _act(self, config: dict, state: dict, source_id: str,
             action: str, payload: dict) -> dict:
        _require_boto3()
        record = _get_source(state, source_id)
        if not record:
            return {'acted': False, 'reason': 'source not found'}
        astate = record.get('adapter_state', {})
        bucket = astate.get('bucket', '')
        client = self._client(astate)
        try:
            if action == 'upload':
                key = payload.get('key', '')
                local_path = payload.get('path', '')
                if not key or not local_path:
                    return {'acted': False, 'reason': 'upload requires key and path in payload'}
                client.upload_file(local_path, bucket, key)
                return {'acted': True, 'action': 'upload', 'key': key}
            elif action == 'download':
                key = payload.get('key', '')
                local_path = payload.get('path', '')
                if not key or not local_path:
                    return {'acted': False, 'reason': 'download requires key and path in payload'}
                client.download_file(bucket, key, local_path)
                return {'acted': True, 'action': 'download', 'key': key}
            elif action == 'delete':
                key = payload.get('key', '')
                if not key:
                    return {'acted': False, 'reason': 'delete requires key in payload'}
                client.delete_object(Bucket=bucket, Key=key)
                return {'acted': True, 'action': 'delete', 'key': key}
            else:
                return {'acted': False, 'reason': f'unknown action: {action}'}
        except Exception as exc:
            return {'acted': False, 'reason': str(exc)}


SOURCE_REGISTRY.register(S3Adapter())
