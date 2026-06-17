from urllib.parse import urljoin, urlparse


AUTH_BASE_URL = "https://auth.openai.com"


def normalize_continue_url(url: str) -> str:
    value = str(url or "").strip()
    if not value:
        return ""
    if value.startswith("/"):
        return urljoin(AUTH_BASE_URL, value)
    return value


def should_create_account_after_otp(is_new_account: bool, continue_url: str) -> bool:
    if not is_new_account:
        return False
    normalized = normalize_continue_url(continue_url)
    path = urlparse(normalized).path
    return path.rstrip("/") in {"/about-you", "/create-account/about-you"}
