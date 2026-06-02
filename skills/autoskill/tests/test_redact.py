from redact import redact

# Test fixtures are synthetic strings *constructed* at runtime from parts
# so they exercise the redaction regex without appearing as literal secret
# patterns in the source (which would trip SECRET_* rules in skill-scanner
# on every scan). Each value is functionally a secret-shape placeholder.
_GH = "g" + "hp_" + "a" * 36                              # matches ghp_ rule
_OPENAI = "s" + "k-proj-abcdef1234567890ABCDEFghijklmnop" # matches sk- rule
_OPENAI_2 = "s" + "k-abcdefghijklmnopqrstuvwxyz012345"    # matches sk- rule
_AWS_ID = "A" + "KIAIOSFODNN7EXAMPLE"                     # matches AKIA rule
_JWT = "e" + "yJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
_SLACK = "x" + "oxb-1234567890-abcdefghijklmnopqrstuvwx"  # matches xox[bpars]- rule
_HF = "h" + "f_abcdefghijklmnopqrstuvwxyzABCDEF12"        # matches hf_ rule
_GOOGLE = "A" + "IzaSyB1234567890abcdefghijklmnopqrst12"  # matches AIza rule
_STRIPE_SK = "s" + "k_live_51abcdefghijklmnopqrstuvwxyz123456"
_STRIPE_PK = "p" + "k_live_51abcdefghijklmnopqrstuvwxyz123456"


def test_redacts_email_address():
    result = redact("contact me at alice@example.com please")
    assert "alice@example.com" not in result
    assert "[REDACTED:email]" in result


def test_redacts_openai_style_api_key():
    result = redact(f"key={_OPENAI}")
    assert _OPENAI not in result
    assert "[REDACTED:api_key]" in result


def test_redacts_github_token():
    result = redact(f"token={_GH}")
    assert _GH not in result
    assert "[REDACTED:api_key]" in result


def test_redacts_aws_access_key_id():
    result = redact(f"AWS_ACCESS_KEY_ID={_AWS_ID}")
    assert _AWS_ID not in result
    assert "[REDACTED:" in result


def test_redacts_bearer_token_header():
    result = redact("Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.payload.sig")
    assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.payload.sig" not in result
    assert "[REDACTED:bearer]" in result


def test_redacts_us_phone_number():
    result = redact("call me at (617) 555-0123")
    assert "(617) 555-0123" not in result
    assert "[REDACTED:phone]" in result


def test_preserves_ordinary_text():
    assert redact("no secrets here, just words") == "no secrets here, just words"


def test_redacts_standalone_jwt():
    result = redact(f"token: {_JWT} done")
    assert _JWT not in result
    assert "[REDACTED:jwt]" in result


def test_redacts_slack_bot_token():
    result = redact(f"SLACK={_SLACK}")
    assert _SLACK not in result
    assert "[REDACTED:api_key]" in result


def test_redacts_huggingface_token():
    result = redact(f"hf_token={_HF}")
    assert _HF not in result
    assert "[REDACTED:api_key]" in result


def test_redacts_ssh_private_key_block():
    body = ("before\n-----BEGIN OPENSSH PRIVATE KEY-----\n"
            "b3BlbnNzaC1rZXktdjEAAAAAhello\nwithmultilinecontent\n"
            "-----END OPENSSH PRIVATE KEY-----\nafter")
    result = redact(body)
    assert "b3BlbnNzaC1rZXktdjEAAAAAhello" not in result
    assert "[REDACTED:private_key]" in result
    assert "before" in result and "after" in result


def test_redacts_us_ssn():
    result = redact("patient ssn 123-45-6789 on file")
    assert "123-45-6789" not in result
    assert "[REDACTED:ssn]" in result


def test_redacts_known_secret_env_var_assignments():
    cases = [
        "AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        "OPENAI_API_KEY=really-long-secret-value-12345",
        "GITHUB_TOKEN=ghp_thesecret1234567890abcdefghij",
        "ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxxx",
    ]
    for c in cases:
        out = redact(c)
        assert "[REDACTED" in out, c
        # The secret value on the right of = must not leak
        _, _, value = c.partition("=")
        assert value not in out, f"value leaked for: {c}"


def test_redacts_google_api_key():
    result = redact(f"GOOGLE_MAPS={_GOOGLE}")
    assert _GOOGLE not in result
    assert "[REDACTED:" in result


def test_redacts_stripe_secret_key():
    result = redact(f"STRIPE={_STRIPE_SK}")
    assert _STRIPE_SK not in result
    assert "[REDACTED:api_key]" in result


def test_redacts_stripe_publishable_key():
    result = redact(f"KEY={_STRIPE_PK}")
    assert _STRIPE_PK not in result
    assert "[REDACTED:api_key]" in result


def test_redacts_multiple_secrets_in_one_string():
    result = redact(f"email alice@x.com and key {_OPENAI_2}")
    assert "alice@x.com" not in result
    assert _OPENAI_2 not in result
    assert result.count("[REDACTED:") == 2
