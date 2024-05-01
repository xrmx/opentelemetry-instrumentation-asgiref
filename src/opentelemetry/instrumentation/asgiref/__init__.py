# Copyright 2024 Riccardo Magliocchetti
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
The opentelemetry-instrumentation-asgiref package provides wrappers sync module sync_to_async
and async_to_sync functions.
"""

from __future__ import annotations

import traceback

import asgiref.sync
from wrapt import wrap_function_wrapper

from opentelemetry.instrumentation.instrumentor import BaseInstrumentor
from opentelemetry.instrumentation.asgiref.package import _instruments
from opentelemetry.instrumentation.asgiref.version import __version__
from opentelemetry.trace import SpanKind, get_tracer
from opentelemetry.instrumentation.utils import unwrap


class AsgirefInstrumentor(BaseInstrumentor):
    def instrumentation_dependencies(self) -> Collection[str]:
        return _instruments

    def _instrument(self, **kwargs):
        tracer_provider = kwargs.get("tracer_provider")
        self.tracer = get_tracer(
            __name__,
            __version__,
            tracer_provider,
            schema_url="https://opentelemetry.io/schemas/1.25.0",
        )
        self.stacktrace_limit = kwargs.get("stacktrace_limit", 10)

        wrap_function_wrapper(asgiref.sync, "async_to_sync", self.__wrapper)
        wrap_function_wrapper(asgiref.sync, "sync_to_async", self.__wrapper)

    def _uninstrument(self, **kwargs):
        unwrap(asgiref.sync, "async_to_sync")
        unwrap(asgiref.sync, "sync_to_async")

    def __wrapper(self, wrapped, instance, args, kwargs):
        span_name = f"asgiref.sync.{wrapped.__qualname__}"
        with self.tracer.start_as_current_span(span_name, kind=SpanKind.INTERNAL) as span:
            attributes = {
                "exception.type": span_name,
                "exception.stacktrace": traceback.format_stack(limit=self.stacktrace_limit),
                "exception.escaped": str(False),
            }
            span.add_event(name="exception", attributes=attributes)

            return wrapped(*args, **kwargs)
