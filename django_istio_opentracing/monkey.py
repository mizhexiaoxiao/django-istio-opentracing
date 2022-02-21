from . import get_opentracing_span_headers
from urllib.parse import urlparse
import json
import os


try:
    import requests.adapters
except ImportError:
    pass
else:
    _HTTPAdapter_send = requests.adapters.HTTPAdapter.send


def requests_send_wrapper(http_adapter, request, **kwargs):
    """Wraps HTTPAdapter.send"""

    tracing_ignore_netloc = os.getenv("TRACING_IGNORE_NETLOC")
    if tracing_ignore_netloc is not None:     
        netloc = urlparse(request.url).netloc
        ignore_netloc_list = json.loads(tracing_ignore_netloc)
        if netloc in ignore_netloc_list:
            response = _HTTPAdapter_send(http_adapter, request, **kwargs)
            return response

    headers = get_opentracing_span_headers()
    for k, v in headers.items():
        request.headers[k] = v

    response = _HTTPAdapter_send(http_adapter, request, **kwargs)
    return response


def patch_requests():
    if "_HTTPAdapter_send" not in globals():
        raise Exception("requests not installed.")
    requests.adapters.HTTPAdapter.send = requests_send_wrapper
