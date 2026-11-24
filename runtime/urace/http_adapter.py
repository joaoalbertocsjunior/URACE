"""HTTP adapter shim — implementation lives in sources_lib.transport."""
from sources_lib.transport import (
    HttpAdapter,
    HttpxTransport as HttpxAdapter,
    StdlibHttpTransport as StdlibHttpAdapter,
    make_http_transport as make_http_adapter,
)

__all__ = ["HttpAdapter", "HttpxAdapter", "StdlibHttpAdapter", "make_http_adapter"]
