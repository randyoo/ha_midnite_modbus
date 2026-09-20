"""Home Assistant device registry helpers."""


def format_mac(mac: str) -> str:
    """Return the MAC in Home Assistant's canonical form: lower case, colon separated.

    Unique ids are compared as strings, so a device discovered as "00-11-22-33-44-55"
    has to match an entry made from "00:11:22:33:44:55".
    """
    stripped = mac.lower().replace("-", "").replace(".", "").replace(":", "")
    if len(stripped) != 12:
        return mac.lower()
    return ":".join(stripped[i : i + 2] for i in range(0, 12, 2))
