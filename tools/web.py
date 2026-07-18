import ipaddress
import re
import socket
import urllib.request
import urllib.parse
from urllib.parse import urlparse
from agent.registry import registry


# ── SSRF / protocol guard ──────────────────────────────────────────────

_ALLOWED_SCHEMES = {"http", "https"}

# Block internal/reserved hostnames and IPs that could leak local services.
_BLOCKED_HOSTS = frozenset({
    "localhost", "127.0.0.1", "0.0.0.0", "::1", "0000:0000:0000:0000:0000:0000:0000:0001",
    "169.254.169.254",            # AWS / cloud metadata
    "metadata.google.internal",   # GCP metadata
    "metadata",                   # generic metadata alias
})

# IP ranges that should never be reached from the web tools.
_BLOCKED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
    ipaddress.ip_network("::1/128"),
]


def _normalize_ip(hostname: str) -> list[str]:
    """尝试将 hostname 规范化为 IP 地址列表。

    处理顺序：
    1. 标准 IPv4/IPv6 格式
    2. 十进制/八进制/十六进制整数
    3. DNS 解析
    """
    # 1. 标准格式
    try:
        addr = ipaddress.ip_address(hostname)
        return [str(addr)]
    except ValueError:
        pass

    # 2. 数值格式
    try:
        if hostname.isdigit():
            return [str(ipaddress.ip_address(int(hostname)))]
        if hostname.startswith(("0x", "0X")):
            return [str(ipaddress.ip_address(int(hostname, 16)))]
        if hostname.startswith("0") and len(hostname) > 1:
            return [str(ipaddress.ip_address(int(hostname, 8)))]
    except (ValueError, OverflowError):
        pass

    # 3. DNS 解析
    try:
        infos = socket.getaddrinfo(hostname, None)
        return list(dict.fromkeys(info[4][0] for info in infos))
    except socket.gaierror:
        return []


def _is_blocked_host(hostname: str) -> bool:
    """Return True if hostname is internal/reserved."""
    h = hostname.lower().rstrip(".")
    if h in _BLOCKED_HOSTS:
        return True

    # ● 规范化所有可能的 IP 表示，逐个检查
    for ip_str in _normalize_ip(h):
        try:
            addr = ipaddress.ip_address(ip_str)
            # 处理 IPv4-mapped IPv6 (::ffff:127.0.0.1)
            addrs_to_check = [addr]
            if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped:
                addrs_to_check.append(addr.ipv4_mapped)
            for check_addr in addrs_to_check:
                for net in _BLOCKED_NETWORKS:
                    # 确保 IP 版本与网络版本匹配
                    if isinstance(check_addr, ipaddress.IPv4Address) and isinstance(net, ipaddress.IPv4Network):
                        if check_addr in net:
                            return True
                    elif isinstance(check_addr, ipaddress.IPv6Address) and isinstance(net, ipaddress.IPv6Network):
                        if check_addr in net:
                            return True
        except ValueError:
            continue

    return False


def _guard_url(raw_url: str) -> None:
    """Raise ValueError if URL is disallowed (file://, internal IP, etc.)."""
    try:
        parsed = urlparse(raw_url)
    except Exception as exc:
        raise ValueError(f"Invalid URL: {exc}")

    scheme = (parsed.scheme or "").lower()
    if scheme not in _ALLOWED_SCHEMES:
        raise ValueError(
            f"Disallowed URL scheme '{scheme}'. Only http:// and https:// are permitted."
        )

    hostname = (parsed.hostname or "").lower()
    if not hostname:
        raise ValueError("URL must include a hostname.")
    if _is_blocked_host(hostname):
        raise ValueError(f"Disallowed host: {hostname}")


class _GuardedRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Redirect handler that validates every hop against the SSRF guard."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _guard_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_guarded_opener = urllib.request.build_opener(_GuardedRedirectHandler)


def net_web_search(query: str, num_results: int = 5) -> str:
    """Search the web using Bing HTML endpoint (no API key needed)."""
    try:
        url = f"https://www.bing.com/search?q={urllib.parse.quote(query)}"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            },
        )
        with _guarded_opener.open(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")

        # Detect Bing anti-bot / CAPTCHA pages early
        lower_html = html.lower()
        if any(k in lower_html for k in ("captcha", "verify", "security check", "unusual traffic")):
            return "Search error: Bing blocked the request (CAPTCHA/anti-bot). Try again later."

        results = []
        # Primary selector: b_algo list items
        blocks = re.findall(
            r'<li[^>]*class=["\'][^"\']*b_algo[^"\']*["\'][^>]*>(.*?)</li>',
            html,
            re.DOTALL,
        )
        if not blocks:
            # Fallback: any <li> containing an <h2> and an <a href="http...">
            blocks = re.findall(r'<li[^>]*>(.*?)</li>', html, re.DOTALL)

        parsed = 0
        for block in blocks:
            title_m = re.search(r"<h2[^>]*>(.*?)</h2>", block, re.DOTALL)
            title = re.sub(r"<[^>]+>", "", title_m.group(1)).strip() if title_m else ""
            href_m = re.search(r'href=["\']([^"\']+)["\']', block)
            href = href_m.group(1) if href_m else ""
            if title and href.startswith("http") and "bing.com" not in href:
                results.append(f"- {title}\n  {href}")
                parsed += 1
                if len(results) >= num_results:
                    break

        if not results and not parsed:
            # Nothing parsed at all — likely HTML structure changed
            snippet = re.sub(r"\s+", " ", html[:500]).strip()
            return f"Search error: Unable to parse Bing results (page structure changed?). Snippet: {snippet}"

        return "\n".join(results) or "No results found."
    except Exception as e:
        return f"Search error: {e}"


def net_web_extract(url: str) -> str:
    """Fetch and extract text from a URL."""
    try:
        _guard_url(url)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with _guarded_opener.open(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")
        text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text[:4000] + ("\n... (truncated)" if len(text) > 4000 else "")
    except Exception as e:
        return f"Fetch error: {e}"


registry.register(
    name="net_web_search",
    description="Search the web using Bing. No API key required. Returns titles and URLs.",
    parameters={
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "num_results": {"type": "integer", "description": "Number of results", "default": 5}
        },
        "required": ["query"]
    },
    handler=net_web_search,
    tags=["network", "search"],
    category="network"
)

registry.register(
    name="net_web_extract",
    description=(
        "Fetch a URL and extract plain text. Strips scripts/styles/HTML tags. "
        "Only http(s) external URLs allowed."
    ),
    parameters={
        "properties": {
            "url": {"type": "string", "description": "Full http(s) URL to fetch"}
        },
        "required": ["url"]
    },
    handler=net_web_extract,
    tags=["network", "fetch"],
    category="network"
)
