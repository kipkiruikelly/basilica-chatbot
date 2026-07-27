from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from backend.infrastructure.logging import log_event

# Global indicator for setup verification
TELEMETRY_ACTIVE = False

def setup_telemetry(app) -> None:
    """Sets up openTelemetry trace instrumentation for Flask applications."""
    global TELEMETRY_ACTIVE
    try:
        provider = TracerProvider()
        processor = BatchSpanProcessor(ConsoleSpanExporter())
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)
        
        # Try importing dynamic instrumentors
        from opentelemetry.instrumentation.flask import FlaskInstrumentor
        FlaskInstrumentor().instrument_app(app)
        TELEMETRY_ACTIVE = True
        log_event("telemetry_init_success", {})
    except ImportError:
        log_event("telemetry_init_bypass", {"info": "opentelemetry packages not installed, skipping tracer instrumenting"})
    except Exception as e:
        log_event("telemetry_init_error", {"error": str(e)}, "warning")
