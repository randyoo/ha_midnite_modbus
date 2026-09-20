"""DHCP discovery service info."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DhcpServiceInfo:
    ip: str = ""
    hostname: str = ""
    macaddress: str = ""
    hostname_data: Optional[str] = None
    options: dict = field(default_factory=dict)
