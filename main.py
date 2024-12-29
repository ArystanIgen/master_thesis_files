import logging
import sys
import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from loguru import logger
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk._logs import LoggingHandler
from config import CONFIG
from api.v1.api import api_router
from monitoring.logging import get_logger_provider
from monitoring.tracing import get_tracer_provider

from monitoring.prometheus import PrometheusMiddleware, metrics

custom_formatter = (
    "<green>{level}</green>: "
    "<yellow>{time:YYYY-MM-DD at HH:mm:ss}</yellow> | "
    "<cyan>Request ID: {extra[request_id]}</cyan> | "
    "<level>{message}</level>"
)

logger.remove()


def safe_format(record):
    record["extra"].setdefault("request_id", "N/A")
    record["extra"].setdefault("span_id", "N/A")
    record["extra"].setdefault("trace_id", "N/A")


logger.configure(patcher=safe_format)
logger.add(
    sys.stderr,
    colorize=False,
    enqueue=True,
    format=custom_formatter,
    backtrace=True,
    diagnose=True,
    level="INFO",
    serialize=False,
    catch=True,
)

main_app = FastAPI(
    title=CONFIG.api.title,
    debug=CONFIG.api.debug,
    version=CONFIG.api.version,
    openapi_url="/openapi.json",
)

main_app.add_middleware(
    middleware_class=CORSMiddleware,
    allow_origins=CONFIG.api.allowed_hosts or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
main_app.add_middleware(GZipMiddleware, minimum_size=1000)

main_app.include_router(router=api_router, prefix=CONFIG.api.prefix)

if CONFIG.use_monitoring:
    excluded_urls = ",".join(
        [
            "v1/healthz",
            "/openapi.json",
            "/docs",
            "/metrics"
        ]
    )
    FastAPIInstrumentor.instrument_app(
        main_app,
        tracer_provider=get_tracer_provider(),
        excluded_urls=excluded_urls,
    )
    # Setting metrics middleware
    main_app.add_middleware(PrometheusMiddleware, app_name=CONFIG.api.title)
    main_app.add_route("/metrics", metrics)

    handler = LoggingHandler(level=logging.NOTSET, logger_provider=get_logger_provider())
    logging.getLogger().addHandler(handler)


    class PropagateHandler(logging.Handler):
        def emit(self, record):
            if hasattr(record, 'extra') and isinstance(record.extra, dict):
                del record.extra
            logging.getLogger(record.name).handle(record)


    custom_formatter += " | Trace ID: {extra[trace_id]} | Span ID: {extra[span_id]}"
    logger.add(
        PropagateHandler(),
        format=custom_formatter,
        colorize=False,
        level="INFO",
    )

if __name__ == "__main__":
    uvicorn.run(
        "main:main_app", host="0.0.0.0", port=8000, workers=7
    )  # pragma: no cover
