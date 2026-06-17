import os
from dataclasses import dataclass
from datetime import date, timedelta
import random
from typing import Mapping, Optional

from mail_providers import create_cloudmail_email, get_mail_provider, resolve_mail_email


@dataclass(frozen=True)
class RegistrationIdentity:
    email: str
    password: str
    name: str
    birthdate: str


def prepare_registration_identity(
    session,
    env: Optional[Mapping[str, str]] = None,
) -> RegistrationIdentity:
    if env is None:
        env = os.environ
    provider = get_mail_provider(env)
    if provider == "cloudmail":
        email, password = create_cloudmail_email(session, env)
    else:
        email = resolve_mail_email(env)
        password = str(env.get("TEST_PASSWORD", "your-password") or "")

    profile = generate_registration_profile()
    return RegistrationIdentity(
        email=email,
        password=password,
        name=str(profile["name"]),
        birthdate=str(profile["birthday"]),
    )


def generate_registration_profile() -> dict[str, str | int]:
    first_names = [
        "James", "Robert", "John", "Michael", "David", "William", "Richard",
        "Mary", "Jennifer", "Linda", "Elizabeth", "Susan", "Jessica", "Sarah",
        "Emily", "Emma", "Olivia", "Sophia", "Liam", "Noah", "Oliver", "Ethan",
    ]
    last_names = [
        "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
        "Davis", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Martin",
    ]

    today = date.today()
    age = random.randint(18, 55)
    start = today.replace(year=today.year - age - 1) + timedelta(days=1)
    end = today.replace(year=today.year - age)
    birthday = start + timedelta(days=random.randint(0, (end - start).days))

    return {
        "name": f"{random.choice(first_names)} {random.choice(last_names)}",
        "age": age,
        "birthday": birthday.isoformat(),
    }
