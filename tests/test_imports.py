"""Guard: every platform module has to import cleanly."""

from __future__ import annotations

import importlib

import pytest

MODULES = [
    "midnite_solar",
    "midnite_solar.base",
    "midnite_solar.const",
    "midnite_solar.coordinator",
    "midnite_solar.hub",
    "midnite_solar.register_values",
    "midnite_solar.button",
    "midnite_solar.number",
    "midnite_solar.select",
    "midnite_solar.sensor",
    "midnite_solar.binary_sensor",
    "midnite_solar.text",
    "midnite_solar.config_flow",
]


@pytest.mark.parametrize("module", MODULES)
def test_module_imports(module):
    assert importlib.import_module(module) is not None


def test_no_module_imports_the_removed_name():
    import midnite_solar.sensor as sensor

    assert not hasattr(sensor, "WindPowerCurveV0Number")
