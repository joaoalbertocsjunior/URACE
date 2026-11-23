"""Expose URACE operations via sources-lib M2MServer (JSON-RPC 2.0)."""
from __future__ import annotations

import hmac
import os
import sys
import uuid

from sources.m2m.interface import M2MServer, RpcError

from .integration_bridge import BridgeError, Jobs, load_policy, owner_lifetime


def make_dispatch_fn(jobs):
    """Return a dispatch callable suitable for M2MServer(dispatch_fn=...)."""

    def dispatch(method: str, params: dict) -> object:
        try:
            if method == "urace.submit":
                command = params.get("command")
                job_params = params.get("params", {})
                if not isinstance(command, str):
                    raise RpcError(-32602, "command must be a string")
                request_id = "m2m:" + uuid.uuid4().hex
                row = jobs.submit(command, job_params, request_id)
                return {"job_id": row["job_id"], "status": row["status"]}
            if method == "urace.status":
                job_id = params.get("job_id")
                if not isinstance(job_id, str):
                    raise RpcError(-32602, "job_id must be a string")
                return jobs.status(job_id)
            if method == "urace.cancel":
                job_id = params.get("job_id")
                if not isinstance(job_id, str):
                    raise RpcError(-32602, "job_id must be a string")
                jobs.cancel(job_id)
                return {"job_id": job_id, "cancelled": True}
            raise RpcError(-32601, "Method not found")
        except RpcError:
            raise
        except BridgeError as exc:
            raise RpcError(-32602, str(exc)) from exc

    return dispatch


def serve(parser, policy_path=None, *, port: int = 8766, token_env: str = "URACE_M2M_TOKEN") -> int:
    """Start a JSON-RPC 2.0 M2M server on 127.0.0.1:<port>.

    Returns 0 on clean exit (KeyboardInterrupt), 2 on configuration/runtime error.
    """
    jobs = server = None
    try:
        policy = load_policy(parser, policy_path)
        token = os.environ.get(token_env, "")
        jobs = Jobs(policy, private_env=(token_env,))

        def auth_fn(t: str) -> bool:
            if token:
                return hmac.compare_digest(t.encode(), token.encode())
            return True

        server = M2MServer(
            dispatch_fn=make_dispatch_fn(jobs),
            auth_fn=auth_fn,
        )
        server.start(host="127.0.0.1", port=port)
        with owner_lifetime():
            # Block until KeyboardInterrupt (Ctrl-C or SIGINT).
            import time
            while True:
                time.sleep(1)
    except KeyboardInterrupt:
        return 0
    except (ValueError, OSError, KeyError) as error:
        print("URACE M2M: " + str(error), file=sys.stderr)
        return 2
    finally:
        if server is not None:
            server.stop()
        if jobs is not None:
            jobs.close()
    return 0
