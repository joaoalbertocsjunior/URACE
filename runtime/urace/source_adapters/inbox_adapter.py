"""Inbox source adapter — observes email/message inboxes (IMAP); acts with send (SMTP).

Uses stdlib imaplib + smtplib — no extra dep required for basic operation.
"""
from __future__ import annotations

import imaplib
import smtplib
import ssl
from email.mime.text import MIMEText
from typing import Any

from ._base import NullSourceAdapter, _get_source, _set_source
from . import SOURCE_REGISTRY
from .._common import now

import os


class InboxAdapter(NullSourceAdapter):
    kind = 'inbox'

    def add_args(self, subparser: Any) -> None:
        subparser.add_argument('--imap-host', dest='imap_host', default=None)
        subparser.add_argument('--imap-port', dest='imap_port', type=int, default=993)
        subparser.add_argument('--smtp-host', dest='smtp_host', default=None)
        subparser.add_argument('--smtp-port', dest='smtp_port', type=int, default=587)
        subparser.add_argument('--user-env', dest='user_env', default='INBOX_USER',
                               help='Env var with inbox username/email')
        subparser.add_argument('--pass-env', dest='pass_env', default='INBOX_PASS',
                               help='Env var with inbox password')
        subparser.add_argument('--mailbox', default='INBOX')
        subparser.add_argument('--description', default=None)

    def validate(self, args: Any) -> dict[str, Any]:
        name = getattr(args, 'name', None) or getattr(args, 'id', None) or ''
        imap_host = getattr(args, 'imap_host', None) or ''
        if not name:
            raise ValueError('source add --kind inbox requires a name')
        if not imap_host:
            raise ValueError('source add --kind inbox requires --imap-host')
        return {
            'kind': self.kind,
            'imap_host': imap_host,
            'imap_port': int(getattr(args, 'imap_port', None) or 993),
            'smtp_host': getattr(args, 'smtp_host', None) or imap_host,
            'smtp_port': int(getattr(args, 'smtp_port', None) or 587),
            'user_env': getattr(args, 'user_env', None) or 'INBOX_USER',
            'pass_env': getattr(args, 'pass_env', None) or 'INBOX_PASS',
            'mailbox': getattr(args, 'mailbox', None) or 'INBOX',
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
                'imap_host': kwargs.get('imap_host', ''),
                'imap_port': kwargs.get('imap_port', 993),
                'smtp_host': kwargs.get('smtp_host', ''),
                'smtp_port': kwargs.get('smtp_port', 587),
                'user_env': kwargs.get('user_env', 'INBOX_USER'),
                'pass_env': kwargs.get('pass_env', 'INBOX_PASS'),
                'mailbox': kwargs.get('mailbox', 'INBOX'),
                'last_sync_at': None,
                'message_count': None,
                'enabled_actions': [],
            },
        }

    def _sync(self, config: dict, state: dict, source_id: str) -> dict:
        record = _get_source(state, source_id)
        if not record:
            return {'synced': False, 'reason': 'source not found'}
        astate = record.get('adapter_state', {})
        host = astate.get('imap_host', '')
        port = astate.get('imap_port', 993)
        user = os.environ.get(astate.get('user_env', 'INBOX_USER'), '')
        password = os.environ.get(astate.get('pass_env', 'INBOX_PASS'), '')
        mailbox = astate.get('mailbox', 'INBOX')
        if not host or not user or not password:
            return {'synced': False, 'reason': 'missing host/credentials in environment'}
        try:
            context = ssl.create_default_context()
            with imaplib.IMAP4_SSL(host, port, ssl_context=context) as imap:
                imap.login(user, password)
                status, data = imap.select(mailbox, readonly=True)
                if status != 'OK':
                    return {'synced': False, 'reason': f'SELECT failed: {status}'}
                count = int(data[0]) if data and data[0] else 0
        except Exception as exc:
            return {'synced': False, 'reason': str(exc)}
        astate['last_sync_at'] = now()
        astate['message_count'] = count
        _set_source(state, source_id, record)
        return {'synced': True, 'mailbox': mailbox, 'message_count': count}

    def _act(self, config: dict, state: dict, source_id: str,
             action: str, payload: dict) -> dict:
        if action != 'send':
            return {'acted': False, 'reason': f'unknown action: {action}'}
        record = _get_source(state, source_id)
        if not record:
            return {'acted': False, 'reason': 'source not found'}
        astate = record.get('adapter_state', {})
        smtp_host = astate.get('smtp_host', '')
        smtp_port = astate.get('smtp_port', 587)
        user = os.environ.get(astate.get('user_env', 'INBOX_USER'), '')
        password = os.environ.get(astate.get('pass_env', 'INBOX_PASS'), '')
        to = payload.get('to', '')
        subject = payload.get('subject', '(no subject)')
        body = payload.get('body', '')
        if not smtp_host or not user or not password or not to:
            return {'acted': False, 'reason': 'missing smtp config or to/body in payload'}
        try:
            msg = MIMEText(body)
            msg['Subject'] = subject
            msg['From'] = user
            msg['To'] = to
            context = ssl.create_default_context()
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.ehlo()
                server.starttls(context=context)
                server.login(user, password)
                server.sendmail(user, [to], msg.as_string())
        except Exception as exc:
            return {'acted': False, 'reason': str(exc)}
        return {'acted': True, 'to': to, 'subject': subject}


SOURCE_REGISTRY.register(InboxAdapter())
