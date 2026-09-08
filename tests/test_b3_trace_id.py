import unittest

from jaeger_client.span_context import SpanContext

from django_istio_opentracing.b3 import B3Codec128Bit


class B3TraceIdTest(unittest.TestCase):
    def test_preserves_leading_zero_in_128bit_trace_id(self):
        trace_id = "0116eda0cb1685d5b98cc6d9e556b2fa"
        context = SpanContext(
            trace_id=int(trace_id, 16),
            span_id=int("b22dc3b19e556f6b", 16),
            parent_id=None,
            flags=1,
        )
        carrier = {}

        B3Codec128Bit(generate_128bit_trace_id=True).inject(
            context, carrier
        )

        self.assertEqual(trace_id, carrier["X-B3-TraceId"])
        self.assertEqual("b22dc3b19e556f6b", carrier["X-B3-SpanId"])


if __name__ == "__main__":
    unittest.main()
