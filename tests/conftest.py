"""Put the Home Assistant test double and the integration on the import path."""

from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# The double has to win over a real Home Assistant install if one is present.
sys.path.insert(0, os.path.join(HERE, "_ha_stub"))
# Lets the integration be imported as midnite_solar, the way Home Assistant does.
sys.path.insert(0, os.path.join(ROOT, "custom_components"))
