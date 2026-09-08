from jaeger_client.codecs import B3Codec


class B3Codec128Bit(B3Codec):
    """Serialize 128-bit B3 trace IDs with their full 32-character width."""

    def __init__(self, generate_128bit_trace_id=True):
        """Support both Jaeger 4.3 and 4.4 B3Codec constructors."""
        try:
            super(B3Codec128Bit, self).__init__(
                generate_128bit_trace_id=generate_128bit_trace_id
            )
        except TypeError:
            # jaeger-client 4.3 inherits object.__init__ and accepts no args.
            super(B3Codec128Bit, self).__init__()

    def inject(self, span_context, carrier):
        super(B3Codec128Bit, self).inject(span_context, carrier)
        carrier[self.trace_header] = format(
            span_context.trace_id, "x"
        ).zfill(32)
