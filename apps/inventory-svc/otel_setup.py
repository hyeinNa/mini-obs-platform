"""OpenTelemetry SDK initialization for inventory-svc."""
import logging
import os

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.composite import CompositePropagator
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

logger = logging.getLogger(__name__)


def setup_otel() -> None:
    """Configure OTel SDK with OTLP gRPC exporter and W3C TraceContext propagation."""
    service_name = os.environ.get("OTEL_SERVICE_NAME", "inventory-svc")
    otlp_endpoint = os.environ.get(
        "OTEL_EXPORTER_OTLP_ENDPOINT",
        "http://localhost:4317",
    )

    resource = Resource.create({"service.name": service_name})

    exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    set_global_textmap(
        CompositePropagator([TraceContextTextMapPropagator()])
    )

    logger.info(
        "OTel initialized",
        extra={"service": service_name, "otlp_endpoint": otlp_endpoint},
    )
