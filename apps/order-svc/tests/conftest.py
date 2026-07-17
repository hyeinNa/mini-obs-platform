"""Shared test fixtures for order-svc.

The otel_setup module is replaced with a no-op stub before any app module is
imported, so tests run without a live OTLP endpoint.
"""
import sys
import types

_fake_otel = types.ModuleType("otel_setup")
_fake_otel.setup_otel = lambda: None  # type: ignore[attr-defined]
sys.modules.setdefault("otel_setup", _fake_otel)
