"""Home Assistant device registry helpers."""


def format_mac(mac: str) -> str:
    """Return the canonical lower-case form of a MAC address."""
    return mac.lower().replace("-", "").replace(":", "").replace(".", "")
