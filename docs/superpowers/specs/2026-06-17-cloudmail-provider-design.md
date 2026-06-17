# Cloud Mail Provider Design

## Goal

Add a second OTP mailbox path for Cloud Mail while keeping the existing inbuck path unchanged.

## Architecture

The script will use an explicit `MAIL_PROVIDER` environment variable. `inbuck` remains available as the legacy provider and keeps using `TEST_EMAIL`, `TEST_PASSWORD`, and `TEST_INBOX_API`. `cloudmail` uses the Cloud Mail public API directly, following the reference project's `genToken`, `addUser`, and `emailList` flow.

## Components

- `mail_providers.py` owns provider selection, OTP polling, Cloud Mail token generation, Cloud Mail mailbox creation, Cloud Mail email list queries, and verification code extraction.
- `registration_identity.py` owns reference-style generated mailbox/password/profile data for the registration flow.
- `codex_team_oauth.py` keeps the OAuth/register flow and delegates OTP waiting to `wait_for_otp`.
- `README.md` documents both mailbox paths and the new Cloud Mail environment variables.
- `tests/test_mail_providers.py` covers provider selection, code extraction, and the Cloud Mail request flow with an injected fake session.

## Data Flow

For `MAIL_PROVIDER=inbuck`, `wait_for_otp` polls:

- `GET {TEST_INBOX_API}/mailbox/{local_part}`
- `GET {TEST_INBOX_API}/mailbox/{local_part}/{message_id}`

For `MAIL_PROVIDER=cloudmail`, `prepare_registration_identity` creates a mailbox with:

- `POST {CLOUDMAIL_API_BASE}/api/public/genToken`
- `POST {CLOUDMAIL_API_BASE}/api/public/addUser`

The returned generated email and password are used for the OpenAI registration. The generated profile name and birthday follow the reference project's `generate_profile` implementation. Then `wait_for_otp` polls:

- `POST {CLOUDMAIL_API_BASE}/api/public/genToken`
- `POST {CLOUDMAIL_API_BASE}/api/public/emailList`

The Cloud Mail provider scans the latest rows first, reading `subject`, `text`, and `content` fields for a six-character or six-digit verification code.

## Error Handling

Missing Cloud Mail configuration raises a clear `ValueError` before polling. HTTP/API failures return no OTP for that polling attempt unless token generation itself is misconfigured or unauthorized. The main script keeps the existing "NO OTP" exit path when no provider returns a code before the retry limit.

## Testing

Unit tests will cover the non-network logic with a fake session:

- provider defaults to `inbuck`
- unknown provider is rejected
- Cloud Mail calls `genToken`, `addUser`, then `emailList`
- Cloud Mail registration identity does not need `TEST_EMAIL` or `TEST_PASSWORD`
- Cloud Mail extracts OTPs from subject/text/content
- inbuck still parses the existing mailbox response shape
