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

from opentelemetry.test.test_base import TestBase
from opentelemetry.trace import SpanKind
from opentelemetry.instrumentation.asgiref import AsgirefInstrumentor


async def asyncfun():
    return "async"


def syncfun():
    return "sync"


class TestAsgirefInstrumentor(TestBase):
    def setUp(self):
        super().setUp()
        AsgirefInstrumentor().instrument()

    def tearDown(self):
        super().tearDown()
        AsgirefInstrumentor().uninstrument()

    def assert_span(self, span, span_name):
        self.assertEqual(span.attributes, {})
        self.assertEqual(span.name, span_name)
        self.assertEqual(span.kind, SpanKind.INTERNAL)

    def assert_event(self, event, event_type):
        self.assertEqual(event.name, "exception")
        self.assertEqual(event.attributes["exception.type"], event_type)
        self.assertTrue(event.attributes["exception.stacktrace"])
        self.assertTrue(isinstance(event.attributes["exception.stacktrace"], str))
        self.assertEqual(event.attributes["exception.escaped"], "False")

    def test_sync_to_async(self):
        from asgiref.sync import sync_to_async
        coroutine = sync_to_async(syncfun)()
        span_list = self.memory_exporter.get_finished_spans()
        self.assertEqual(1, len(span_list))
        span = span_list[0]
        self.assert_span(span, "asgiref.sync.sync_to_async")
        events = span.events
        self.assertEqual(1, len(events))
        event = events[0]
        self.assert_event(event, "asgiref.sync.sync_to_async")

    def test_async_to_sync(self):
        from asgiref.sync import async_to_sync
        async_to_sync(asyncfun)()
        span_list = self.memory_exporter.get_finished_spans()
        self.assertEqual(1, len(span_list))
        span = span_list[0]
        self.assert_span(span, "asgiref.sync.async_to_sync")
        events = span.events
        self.assertEqual(1, len(events))
        event = events[0]
        self.assert_event(event, "asgiref.sync.async_to_sync")
