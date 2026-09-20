# Tests

Two kinds of test files live here:

* `test_*.py` - pytest suite that runs with **no Midnite Classic attached and no
  Home Assistant install**, using the small Home Assistant double in
  `_ha_stub/`. Expectations are quoted from the Classic MODBUS register map, so
  a wrong constant or a wrong write sequence fails here instead of on the
  hardware. Run: `python -m pytest` from the repository root.

* `custom_components/midnite_solar/tests/` - the older zero-dependency
  diagnostic scripts. Those are run by hand, need a real Home Assistant, and are
  excluded from pytest by `pytest.ini`.

The double is a test double, not a simulator: it does not speak Modbus and never
opens a socket. Real end-to-end behaviour still needs a bench Classic, because a
Classic is effectively single-connection and resets idle links.
