"""DHCP discovery service info."""

from dataclasses import dataclass, field


@dataclass
class DhcpServiceInfo:
    ip: str = ""
    hostname: str = ""
    macaddress: str = ""
    hostname_data: str | None = None
    options: dict = field(default_factory=dict)
