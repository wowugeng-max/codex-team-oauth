import os
import random
import re
import string
import time
from typing import Mapping, Optional


SUPPORTED_PROVIDERS = {"inbuck", "cloudmail"}


def get_mail_provider(env: Optional[Mapping[str, str]] = None) -> str:
    if env is None:
        env = os.environ
    provider = str(env.get("MAIL_PROVIDER", "inbuck") or "inbuck").strip().lower()
    if provider not in SUPPORTED_PROVIDERS:
        raise ValueError("MAIL_PROVIDER must be one of: inbuck, cloudmail")
    return provider


def resolve_mail_email(env: Optional[Mapping[str, str]] = None) -> str:
    if env is None:
        env = os.environ

    return str(env.get("TEST_EMAIL", "your-test-email@example.com") or "").strip()


def create_cloudmail_email(session, env: Optional[Mapping[str, str]] = None, *, max_retry: int = 30):
    if env is None:
        env = os.environ

    base = str(env.get("CLOUDMAIL_API_BASE", "") or "").rstrip("/")
    admin_email = str(env.get("CLOUDMAIL_ADMIN_EMAIL", "") or "")
    admin_password = str(env.get("CLOUDMAIL_ADMIN_PASSWORD", "") or "")
    role_name = str(env.get("CLOUDMAIL_ROLE_NAME", "") or "").strip()
    proxy = str(env.get("CLOUDMAIL_PROXY", "") or "")

    if not base or not admin_email or not admin_password:
        raise ValueError(
            "CLOUDMAIL_API_BASE, CLOUDMAIL_ADMIN_EMAIL, and CLOUDMAIL_ADMIN_PASSWORD are required"
        )

    domain = _resolve_cloudmail_domain(env, admin_email)
    if proxy and hasattr(session, "proxies"):
        session.proxies = {"http": proxy, "https": proxy}

    token = _cloudmail_gen_token(session, base, admin_email, admin_password)
    for _ in range(max_retry):
        email = _generate_cloudmail_local_part() + "@" + domain
        password = _generate_cloudmail_password()
        user_obj = {"email": email, "password": password}
        if role_name:
            user_obj["roleName"] = role_name

        res = session.post(
            f"{base}/api/public/addUser",
            json={"list": [user_obj]},
            headers={
                "Authorization": token,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=20,
            verify=False,
        )
        if res.status_code == 401:
            token = _cloudmail_gen_token(session, base, admin_email, admin_password)
            res = session.post(
                f"{base}/api/public/addUser",
                json={"list": [user_obj]},
                headers={
                    "Authorization": token,
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                timeout=20,
                verify=False,
            )

        if res.status_code != 200:
            raise ValueError("Cloud Mail addUser HTTP " + str(res.status_code) + ": " + str(res.text)[:200])

        data = res.json()
        if data.get("code") == 200:
            return email, password

        if "exist" in str(data).lower() or "已存在" in str(data):
            continue
        raise ValueError("Cloud Mail addUser failed: " + str(data)[:200])

    raise ValueError("Cloud Mail addUser failed after retrying generated addresses")


def extract_verification_code(*contents: str, allow_digits: bool = True) -> str:
    for content in contents:
        code = _extract_one_verification_code(str(content or ""), allow_digits=allow_digits)
        if code:
            return code
    return ""


def wait_for_otp(
    email: str,
    session,
    env: Optional[Mapping[str, str]] = None,
    *,
    attempts: int = 30,
    sleep_seconds: float = 2,
) -> str:
    if env is None:
        env = os.environ
    provider = get_mail_provider(env)
    if provider == "cloudmail":
        return _wait_cloudmail_otp(email, session, env, attempts=attempts, sleep_seconds=sleep_seconds)
    return _wait_inbuck_otp(email, session, env, attempts=attempts, sleep_seconds=sleep_seconds)


def _wait_inbuck_otp(
    email: str,
    session,
    env: Mapping[str, str],
    *,
    attempts: int,
    sleep_seconds: float,
) -> str:
    inbox_api = str(env.get("TEST_INBOX_API", "http://your-mailbox-service.example/api/v1") or "").rstrip("/")
    mailbox = email.split("@", 1)[0]

    for i in range(attempts):
        if sleep_seconds:
            time.sleep(sleep_seconds)

        r2 = session.get(f"{inbox_api}/mailbox/" + mailbox, timeout=10)
        if r2.status_code == 200:
            messages = r2.json()
            if messages:
                message_id = str(messages[-1].get("id", "") or "")
                if message_id:
                    r3 = session.get(f"{inbox_api}/mailbox/" + mailbox + "/" + message_id, timeout=10)
                    if r3.status_code == 200:
                        body = ((r3.json().get("body", {}) or {}).get("text", "") or "")
                        otp = extract_verification_code(body)
                        if otp:
                            print("  OTP: " + otp)
                            return otp

        if i % 5 == 0:
            print("  wait... (" + str(i + 1) + "/" + str(attempts) + ")")

    return ""


def _wait_cloudmail_otp(
    email: str,
    session,
    env: Mapping[str, str],
    *,
    attempts: int,
    sleep_seconds: float,
) -> str:
    base = str(env.get("CLOUDMAIL_API_BASE", "") or "").rstrip("/")
    admin_email = str(env.get("CLOUDMAIL_ADMIN_EMAIL", "") or "")
    admin_password = str(env.get("CLOUDMAIL_ADMIN_PASSWORD", "") or "")
    proxy = str(env.get("CLOUDMAIL_PROXY", "") or "")

    if not base or not admin_email or not admin_password:
        raise ValueError(
            "CLOUDMAIL_API_BASE, CLOUDMAIL_ADMIN_EMAIL, and CLOUDMAIL_ADMIN_PASSWORD are required"
        )

    if proxy and hasattr(session, "proxies"):
        session.proxies = {"http": proxy, "https": proxy}

    token = _cloudmail_gen_token(session, base, admin_email, admin_password)
    for i in range(attempts):
        if sleep_seconds:
            time.sleep(sleep_seconds)

        rows, unauthorized = _cloudmail_email_list(session, base, token, email)
        if unauthorized:
            token = _cloudmail_gen_token(session, base, admin_email, admin_password)
            rows, _ = _cloudmail_email_list(session, base, token, email)

        for row in rows:
            otp = extract_verification_code(
                str(row.get("subject") or ""),
                str(row.get("text") or ""),
                str(row.get("content") or ""),
                allow_digits=False,
            )
            if not otp:
                otp = extract_verification_code(
                    str(row.get("subject") or ""),
                    str(row.get("text") or ""),
                    str(row.get("content") or ""),
                    allow_digits=True,
                )
            if otp:
                print("  OTP: " + otp)
                return otp

        if i % 5 == 0:
            print("  wait... (" + str(i + 1) + "/" + str(attempts) + ")")

    return ""


def _cloudmail_gen_token(session, base: str, admin_email: str, admin_password: str) -> str:
    res = session.post(
        f"{base}/api/public/genToken",
        json={"email": admin_email, "password": admin_password},
        timeout=20,
        verify=False,
    )
    if res.status_code != 200:
        raise ValueError("Cloud Mail genToken HTTP " + str(res.status_code) + ": " + str(res.text)[:200])

    data = res.json()
    if data.get("code") != 200:
        raise ValueError("Cloud Mail genToken failed: " + str(data)[:200])

    token = (data.get("data") or {}).get("token")
    if not token:
        raise ValueError("Cloud Mail genToken did not return token")
    return str(token)


def _cloudmail_email_list(session, base: str, token: str, email: str):
    payload = {
        "toEmail": email,
        "type": 0,
        "isDel": 0,
        "timeSort": "desc",
        "num": 1,
        "size": 50,
    }
    res = session.post(
        f"{base}/api/public/emailList",
        json=payload,
        headers={
            "Authorization": token,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        timeout=20,
        verify=False,
    )
    if res.status_code == 401:
        return [], True
    if res.status_code != 200:
        return [], False

    data = res.json()
    if data.get("code") != 200:
        return [], False

    rows = data.get("data")
    if isinstance(rows, list):
        return [row for row in rows if isinstance(row, dict)], False
    return [], False


def _extract_one_verification_code(content: str, *, allow_digits: bool) -> str:
    if not content:
        return ""

    normalized = str(content)
    normalized = re.sub(r"<head\b[\s\S]*?</head>", " ", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"<style\b[\s\S]*?</style>", " ", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"<script\b[\s\S]*?</script>", " ", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"<!--.*?-->", " ", normalized, flags=re.DOTALL)
    normalized = re.sub(r"<[^>]+>", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()

    m = re.search(r"(?<![A-Z0-9-])([A-Z0-9]{3}-[A-Z0-9]{3})(?![A-Z0-9-])", normalized, re.IGNORECASE)
    if m:
        return m.group(1).upper()

    m = re.search(r"(?<![A-Z0-9])([A-Z0-9]{6})(?![A-Z0-9])", normalized, re.IGNORECASE)
    if m:
        code = m.group(1).upper()
        if not code.isalpha() and (allow_digits or not code.isdigit()):
            return code

    m = re.search(
        r"(?:verification code|验证码|your code|code is|code below|enter this code)[^A-Z0-9]{0,20}([A-Z0-9-]{6,8})\b",
        normalized,
        re.IGNORECASE,
    )
    if m:
        code = m.group(1).upper()
        if allow_digits or not code.replace("-", "").isdigit():
            return code

    if allow_digits:
        for code in re.findall(
            r"(?:verification code|验证码|your code|code is|code below|enter this code)[^\d]{0,40}(\d{6})",
            normalized,
            re.IGNORECASE,
        ):
            if code != "177010":
                return code
        for code in re.findall(r"(?<![A-Z0-9])(\d{6})(?![A-Z0-9])", normalized, re.IGNORECASE):
            if code != "177010":
                return code

    return ""


def _normalize_cloudmail_domain_suffix(value: str) -> str:
    domain = str(value or "").strip().lower().strip(".")
    if not domain:
        return ""
    if "." not in domain:
        raise ValueError("CLOUDMAIL_DOMAIN_SUFFIX must be a domain such as mx.example.com")
    if not all(ch.isalnum() or ch in {"-", "."} for ch in domain):
        raise ValueError("CLOUDMAIL_DOMAIN_SUFFIX only supports letters, numbers, hyphens, and dots")
    return domain


def _resolve_cloudmail_domain(env: Mapping[str, str], admin_email: str) -> str:
    domain = _normalize_cloudmail_domain_suffix(env.get("CLOUDMAIL_DOMAIN_SUFFIX", ""))
    if not domain and "@" in admin_email:
        domain = _normalize_cloudmail_domain_suffix(admin_email.split("@", 1)[1])
    if not domain:
        raise ValueError("CLOUDMAIL_DOMAIN_SUFFIX is required when admin email has no domain")
    return domain


def _generate_cloudmail_password(length: int = 14) -> str:
    chars = string.ascii_letters + string.digits + "!@#$%"
    password = [
        random.choice(string.ascii_uppercase),
        random.choice(string.ascii_lowercase),
        random.choice(string.digits),
        random.choice("!@#$%"),
    ]
    password += [random.choice(chars) for _ in range(max(0, length - 4))]
    random.shuffle(password)
    return "".join(password)


def _generate_cloudmail_local_part() -> str:
    first_names = [
        "alex", "aaron", "adam", "adrian", "alan", "albert", "andrew", "anthony",
        "ben", "brandon", "brian", "bruce", "caleb", "cameron", "charles", "chris",
        "daniel", "david", "derek", "edward", "elijah", "ethan", "evan", "frank",
        "gabriel", "george", "henry", "ian", "jack", "jacob", "james", "jason",
        "jeremy", "john", "jonathan", "jordan", "joseph", "justin", "kevin", "leo",
        "liam", "logan", "lucas", "mason", "matthew", "michael", "nathan", "nicholas",
        "noah", "oliver", "owen", "patrick", "peter", "ray", "richard", "robert",
        "ryan", "sam", "samuel", "scott", "steven", "thomas", "tony", "victor",
        "william", "zack", "amy", "anna", "ava", "bella", "chloe", "claire",
        "diana", "ella", "emily", "emma", "eva", "grace", "hannah", "isabella",
        "jane", "jessica", "julia", "kate", "katie", "lily", "linda", "lucy",
        "mia", "natalie", "nina", "olivia", "rachel", "rose", "sarah", "sophia",
        "stella", "susan", "victoria", "violet", "zoe", "yuki", "mei", "xin",
    ]
    last_names = [
        "smith", "johnson", "williams", "brown", "jones", "miller", "davis", "wilson",
        "anderson", "thomas", "taylor", "moore", "martin", "lee", "walker", "hall",
        "allen", "young", "hernandez", "king", "wright", "lopez", "hill", "scott",
        "green", "adams", "baker", "nelson", "carter", "mitchell", "perez", "roberts",
        "turner", "phillips", "campbell", "parker", "evans", "edwards", "collins", "stewart",
        "sanchez", "morris", "rogers", "reed", "cook", "morgan", "bell", "murphy",
        "bailey", "rivera", "cooper", "richardson", "cox", "howard", "ward", "torres",
        "peterson", "gray", "ramirez", "james", "watson", "brooks", "kelly", "sanders",
        "price", "bennett", "wood", "barnes", "ross", "henderson", "coleman", "jenkins",
        "perry", "powell", "long", "patterson", "hughes", "flores", "washington", "butler",
        "simmons", "foster", "gonzales", "bryant", "alexander", "russell", "griffin", "diaz",
        "hayes", "myers", "ford", "hamilton", "graham", "sullivan", "wallace", "woods",
        "wang", "zhang", "liu", "chen", "yang", "huang", "zhao", "wu", "zhou", "xu",
        "sun", "ma", "zhu", "hu", "guo", "lin", "he", "gao", "liang", "luo",
    ]

    first = random.choice(first_names)
    last = random.choice(last_names)
    style = random.choice(["dot", "plain", "underscore", "hyphen"])
    if style == "dot":
        base = first + "." + last
    elif style == "underscore":
        base = first + "_" + last
    elif style == "hyphen":
        base = first + "-" + last
    else:
        base = first + last

    if random.random() < 0.2:
        middle = random.choice(string.ascii_lowercase)
        joiner = random.choice(["", ".", "_"])
        base = first + joiner + middle + joiner + last

    if random.random() < 0.35:
        digits = "".join(random.choices(string.digits, k=random.choice([2, 3, 4])))
        if random.random() < 0.5:
            base = base + digits
        else:
            base = base + random.choice([".", "_"]) + digits

    return base[:64]
