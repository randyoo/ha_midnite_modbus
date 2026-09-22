"""Test double for the zeroconf package: records, never touches the network.

Real Home Assistant ships real zeroconf (its zeroconf integration uses it);
the suite must never open an mDNS socket, so this stands in with exactly the
surface bridge.BridgeAdvertiser uses: `Zeroconf()`, `register_service`,
`unregister_service`, `close`, and `ServiceInfo(...)` carrying the fields a
test asserts on.
"""

from __future__ import annotations


class ServiceInfo:
    """Holds the fields the advertiser passes so tests can read them back."""

    def __init__(
        self,
        type_,
        name,
        addresses=None,
        port=None,
        server=None,
        properties=None,
        **kwargs,
    ):
        self.type = type_
        self.name = name
        self.addresses = list(addresses or [])
        self.port = port
        self.server = server
        self.properties = dict(properties or {})


class Zeroconf:
    """Every instance lives here, so a test can find the one it created."""

    instances = []

    def __init__(self):
        self.registered = []
        self.unregistered = []
        self.closed = False
        Zeroconf.instances.append(self)

    def register_service(self, info, **kwargs):
        self.registered.append(info)

    def unregister_service(self, info, **kwargs):
        self.unregistered.append(info)

    def close(self):
        self.closed = True
