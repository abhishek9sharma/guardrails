import json
from functools import wraps
from typing import (
    AsyncIterator,
    Awaitable,
    Callable,
    Iterator,
    Optional,
)
from phoenix.otel import register

from opentelemetry import context, trace
from opentelemetry.trace import StatusCode, Span
import os

PHOENIX_API_KEY = ""
os.environ["PHONEIX_CLIENT_HEADERS"] = f"api_key={PHOENIX_API_KEY}"
tracer_provider = register(
    project_name="arizetest2s", endpoint="http://localhost:6006/v1/traces"
)

GUARDRAILS_VERSION = "1.0.0"

from functools import wraps
from opentelemetry import context, trace
from opentelemetry.trace import StatusCode

GUARDRAILS_VERSION = "1.0.0"

def trace_abc(fn):
    @wraps(fn)
    def trace_wrapper(*args, **kwargs):
        # Get the current OpenTelemetry context
        current_otel_context = context.get_current()
        tracer = trace.get_tracer("guardrails-ai", GUARDRAILS_VERSION)

        # Start a new span
        with tracer.start_as_current_span(
            name=fn.__name__,  # Dynamically set the span name to the function's name
            context=current_otel_context,
        ) as step_span:
            try:
                # Log incoming arguments
                step_span.set_attribute("args", str(args))
                step_span.set_attribute("kwargs", str(kwargs))

                # Call the original function
                response = fn(*args, **kwargs)

                # Optionally log the response
                step_span.set_attribute("response", str(response))

                return response
            except Exception as e:
                # Log exception and mark span as an error
                step_span.set_status(status=StatusCode.ERROR, description=str(e))
                step_span.set_attribute("exception", str(e))
                raise e

    return trace_wrapper



@trace_abc
def add(a,b):
     return a+b


@trace_abc
def sub(a,b):
    return add(a, -b)


print(sub(1,2))