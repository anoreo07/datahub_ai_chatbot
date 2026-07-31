"""SSRF guard for URL validation."""
import ipaddress
from urllib.parse import urlparse

import structlog

log = structlog.get_logger()

PRIVATE_NETWORKS = [
    "10.0.0.0/8",
    "172.16.0.0/12",
    "192.168.0.0/16",
    "127.0.0.0/8",
    "169.254.0.0/16",
    "::1/128",
    "fc00::/7",
    "fe80::/10",
]

ALLOWED_SCHEMES = {"http", "https"}

FORBIDDEN_HOSTNAMES = {
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "[::1]",
    "metadata.google.internal",
    "169.254.169.254",
}

FORBIDDEN_PORTS = {22, 23, 25, 135, 137, 139, 445, 1433, 1521, 3306, 5432, 6379, 8080, 8443, 9200}


class SSRFGuard:
    def validate(self, url: str) -> bool:
        try:
            parsed = urlparse(url)
        except Exception as e:
            log.warning("ssrf_parse_failed", url=url[:50], error=str(e))
            return False

        if parsed.scheme not in ALLOWED_SCHEMES:
            log.warning("ssrf_invalid_scheme", scheme=parsed.scheme, url=url[:50])
            return False

        hostname = parsed.hostname or ""
        if hostname.lower() in FORBIDDEN_HOSTNAMES:
            log.warning("ssrf_forbidden_hostname", hostname=hostname, url=url[:50])
            return False

        if parsed.port and parsed.port in FORBIDDEN_PORTS:
            log.warning("ssrf_forbidden_port", port=parsed.port, url=url[:50])
            return False

        try:
            ip = ipaddress.ip_address(hostname)
            for network in PRIVATE_NETWORKS:
                if ip in ipaddress.ip_network(network):
                    log.warning("ssrf_private_ip", ip=str(ip), url=url[:50])
                    return False
        except ValueError:
            pass

        return True
