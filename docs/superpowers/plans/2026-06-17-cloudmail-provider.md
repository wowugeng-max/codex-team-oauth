# Cloud Mail Provider Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a selectable Cloud Mail mailbox provider that can create a mailbox, generate registration credentials/profile data, and poll OTP while preserving the existing inbuck provider.

**Architecture:** Put mailbox-provider behavior in `mail_providers.py`, registration identity generation in `registration_identity.py`, and keep `codex_team_oauth.py` focused on the registration/OAuth flow. Cloud Mail uses `genToken`, `addUser`, and `emailList`; inbuck remains a legacy provider using `TEST_EMAIL`, `TEST_PASSWORD`, and `TEST_INBOX_API`.

**Tech Stack:** Python standard library, `curl_cffi.requests.Session` passed in by the existing script, `unittest` for local tests.

---

### Task 1: Provider Tests

**Files:**
- Create: `tests/test_mail_providers.py`

- [ ] **Step 1: Write failing tests**

Create tests for provider selection, OTP extraction, Cloud Mail request flow, and inbuck compatibility. Use fake response/session classes so no external mailbox service is contacted.

- [ ] **Step 2: Run tests and verify red**

Run: `python3 -m unittest tests.test_mail_providers -v`
Expected: failure because `mail_providers` does not exist yet.

### Task 2: Provider Module

**Files:**
- Create: `mail_providers.py`

- [ ] **Step 1: Implement minimal provider module**

Add `get_mail_provider`, `extract_verification_code`, `wait_for_otp`, `_wait_inbuck_otp`, and `_wait_cloudmail_otp`. Reuse the caller's session to avoid adding dependencies.

- [ ] **Step 2: Run tests and verify green**

Run: `python3 -m unittest tests.test_mail_providers -v`
Expected: all tests pass.

### Task 3: Main Script Wiring

**Files:**
- Modify: `codex_team_oauth.py`

- [ ] **Step 1: Replace inline OTP polling**

Import `wait_for_otp`, remove the hard-coded inbuck polling loop, and call `wait_for_otp(EMAIL, s)`.

- [ ] **Step 2: Compile-check script**

Run: `python3 -m py_compile codex_team_oauth.py mail_providers.py`
Expected: exit 0.

### Task 4: Documentation

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Document environment variables**

Explain `MAIL_PROVIDER=inbuck|cloudmail`, the existing `TEST_INBOX_API`, and Cloud Mail's `CLOUDMAIL_API_BASE`, `CLOUDMAIL_ADMIN_EMAIL`, `CLOUDMAIL_ADMIN_PASSWORD`.

- [ ] **Step 2: Final verification**

Run: `python3 -m unittest tests.test_mail_providers -v` and `python3 -m py_compile codex_team_oauth.py mail_providers.py`.
Expected: all tests pass and compile check exits 0.
