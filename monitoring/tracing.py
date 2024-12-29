from typing import Optional

from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from config import CONFIG

_TRACER_PROVIDER: Optional[TracerProvider] = None

OTEL_ENVIRONMENT = {
    "DEV": "development",
    "PRODUCTION": "production"
}


def get_tracer_provider() -> TracerProvider:
    global _TRACER_PROVIDER
    if _TRACER_PROVIDER is not None:
        return _TRACER_PROVIDER

    tracer_provider: TracerProvider = TracerProvider(
        resource=Resource(
            attributes={
                'service.name': CONFIG.api.title,
                'telemetry.sdk.language': 'python',
                'environment': OTEL_ENVIRONMENT.get(
                    CONFIG.env,
                    "development"
                ),
            }
        )
    )
    span_exporter = OTLPSpanExporter(insecure=True, endpoint=CONFIG.otel_collector_url)
    span_processor = BatchSpanProcessor(span_exporter)
    tracer_provider.add_span_processor(span_processor)

    _TRACER_PROVIDER = tracer_provider
    return _TRACER_PROVIDER
