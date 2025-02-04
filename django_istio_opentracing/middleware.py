from . import tracer
from opentracing.ext import tags
from opentracing.propagation import Format


class Middleware:
    def __init__(self, get_response=None):
        self.get_response = get_response
        self.scope = None
        self._extra_headers = {}
        self.set_extra_headers()

    def set_extra_headers(self):
        incoming_headers = [
            # All applications should propagate x-request-id. This header is
            # included in access log statements and is used for consistent
            # trace sampling and log sampling decisions in Istio.
            "x-request-id",
            # Lightstep tracing header. Propagate this if you use lightstep
            # tracing in Istio (see
            # https://istio.io/latest/docs/tasks/observability/distributed-tracing/lightstep/)
            # Note: this should probably be changed to use B3 or W3C
            # TRACE_CONTEXT Lightstep recommends using B3 or TRACE_CONTEXT and
            # most application libraries from lightstep do not support
            # x-ot-span-context.
            "x-ot-span-context",
            # Datadog tracing header. Propagate these headers if you use
            #  Datadog tracing.
            "x-datadog-trace-id",
            "x-datadog-parent-id",
            "x-datadog-sampling-priority",
            # W3C Trace Context. Compatible with OpenCensusAgent and
            # Stackdriver Istio configurations.
            "traceparent",
            "tracestate",
            # Cloud trace context. Compatible with OpenCensusAgent and
            # Stackdriver Istio configurations.
            "x-cloud-trace-context",
            # Grpc binary trace context. Compatible with OpenCensusAgent nad
            # Stackdriver Istio configurations.
            "grpc-trace-bin",
            # b3 trace headers. Compatible with Zipkin, OpenCensusAgent, and
            # Stackdriver Istio configurations. Commented out since they are
            # propagated by the OpenTracing tracer above.
            # 'x-b3-traceid',
            # 'x-b3-spanid',
            # 'x-b3-parentspanid',
            # 'x-b3-sampled',
            # 'x-b3-flags',
            # Application-specific headers to forward.
            "user-agent",
            "x-weike-node",
            "x-weike-forward",
        ]
        # For Zipkin, always propagate b3 headers.
        # For Lightstep, always propagate the x-ot-span-context header.
        # For Datadog, propagate the corresponding datadog headers.
        # For OpenCensusAgent and Stackdriver configurations, you can choose
        # set of compatible headers to propagate within your application. For
        # any example, you can propagate b3 headers or W3C trace context
        # headers with the same result. This can also allow you to translate
        # between context propagation mechanisms between different
        # applications.
        self._extra_headers = incoming_headers

    def process_request(self, request):
        try:
            # Create a new span context, reading in values (traceid,
            # spanid, etc) from the incoming x-b3-*** headers.
            headers_dict = {}
            for k in request.META.keys():
                if k.startswith("HTTP_"):
                    kk = "-".join([t.capitalize() for t in k[5:].split("_")])
                    headers_dict[kk] = request.META[k]
            span_ctx = tracer.extract(
                Format.HTTP_HEADERS,
                headers_dict,
            )
            # Note: this tag means that the span will *not* be
            # a child span. It will use the incoming traceid and
            # spanid. We do this to propagate the headers verbatim.
            rpc_tag = {tags.SPAN_KIND: tags.SPAN_KIND_RPC_SERVER}
            
            # application tag
            rpc_tag["framework"] = "Django"
            rpc_tag["uri"] = request.build_absolute_uri().split("?")[0]

            span = tracer.start_span(
                operation_name="opentracing-middleware",
                child_of=span_ctx,
                tags=rpc_tag,
            )
        except Exception:
            # We failed to create a context, possibly due to no
            # incoming x-b3-*** headers. Start a fresh span.
            # Note: This is a fallback only, and will create fresh headers,
            # not propagate headers.
            span = tracer.start_span("opentracing-middleware")
            # Keep this in sync with the headers in details and reviews.
        extra_headers = {}
        for ihdr in self._extra_headers:
            val = request.META.get("HTTP_" + "_".join(ihdr.upper().split("-")))
            if val is not None:
                extra_headers[ihdr] = val
        setattr(span, "extra_headers", extra_headers)
        self.scope = tracer.scope_manager.activate(span, True)
        return None

    def close_scope(self):
        scope = tracer.scope_manager.active
        if scope:
            scope.close()

    def process_response(self, request, response):
        self.close_scope()
        return response

    def __call__(self, request):
        self.process_request(request)
        response = self.get_response(request)
        response = self.process_response(request, response)
        return response
