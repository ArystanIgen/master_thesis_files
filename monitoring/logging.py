from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import (
    OTLPLogExporter,
)
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import Resource

from config import CONFIG

_LOGGER_PROVIDER: LoggerProvider | None = None


def get_logger_provider() -> LoggerProvider:
    global _LOGGER_PROVIDER
    if _LOGGER_PROVIDER is not None:
        return _LOGGER_PROVIDER

    log_exporter = OTLPLogExporter(
        endpoint=f"grpc://{CONFIG.otel_collector_url}",
        insecure=True
    )
    log_provider = LoggerProvider(resource=Resource(
        attributes={
            'service.name': CONFIG.api.title,
            'telemetry.sdk.language': 'python',
            'environment': CONFIG.env,
        }
    ))
    set_logger_provider(log_provider)

    log_processor = BatchLogRecordProcessor(log_exporter)
    log_provider.add_log_record_processor(log_processor)

    _LOGGER_PROVIDER = log_provider
    return _LOGGER_PROVIDER
