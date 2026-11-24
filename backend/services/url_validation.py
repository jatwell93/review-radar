from urllib.parse import urlparse

_ALLOWED_HOSTS = {"maps.google.com", "www.google.com"}


def is_google_maps_url(value: str) -> bool:
    """True only for an https Google Maps URL, judged by the parsed host and path.

    A substring or prefix test on the raw string accepts spoofs such as
    https://www.google.com.evil.com/maps or https://www.google.com@evil.com/maps.
    """
    if not isinstance(value, str):
        return False
    try:
        parsed = urlparse(value)
        port = parsed.port
    except ValueError:
        return False
    if parsed.scheme != "https" or parsed.username or parsed.password or port:
        return False
    host = (parsed.hostname or "").lower()
    if host not in _ALLOWED_HOSTS:
        return False
    if host == "www.google.com":
        return parsed.path == "/maps" or parsed.path.startswith("/maps/")
    return True
