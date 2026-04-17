import re

# Order matters: multi-line and prefixed patterns run before narrower ones.
_PATTERNS = [
    (re.compile(r"-----BEGIN [A-Z ]+PRIVATE KEY-----[\s\S]*?-----END [A-Z ]+PRIVATE KEY-----"),
     "[REDACTED:private_key]"),

    # Known-env-var secret assignments: NAME=value  (catches long values only)
    (re.compile(
        r"\b(?:AWS_SECRET_ACCESS_KEY|AWS_ACCESS_KEY_ID|GITHUB_TOKEN|HF_TOKEN"
        r"|ANTHROPIC_API_KEY|OPENAI_API_KEY|FOUNDRY_API_KEY|SCREENPIPE_TOKEN"
        r"|GOOGLE_API_KEY|SLACK_TOKEN|DEEPGRAM_API_KEY)"
        r"\s*=\s*[^\s\"']+"
    ), "[REDACTED:kv_secret]"),

    (re.compile(r"Bearer\s+[A-Za-z0-9_\-\.=]+"), "[REDACTED:bearer]"),

    (re.compile(r"\beyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+"),
     "[REDACTED:jwt]"),

    (re.compile(r"\bxox[bpars]-[A-Za-z0-9\-]{10,}"), "[REDACTED:api_key]"),
    (re.compile(r"\bhf_[A-Za-z0-9]{32,}"), "[REDACTED:api_key]"),
    (re.compile(r"\bsk-[A-Za-z0-9_\-]{20,}"), "[REDACTED:api_key]"),
    (re.compile(r"\b(?:sk|pk|rk)_live_[A-Za-z0-9]{24,}"), "[REDACTED:api_key]"),
    (re.compile(r"\bghp_[A-Za-z0-9]{36}\b"), "[REDACTED:api_key]"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "[REDACTED:api_key]"),
    (re.compile(r"\bAIza[A-Za-z0-9_\-]{35}\b"), "[REDACTED:api_key]"),

    (re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"),
     "[REDACTED:email]"),

    (re.compile(r"\(\d{3}\)\s*\d{3}-\d{4}"), "[REDACTED:phone]"),
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[REDACTED:ssn]"),
]


def redact(text: str) -> str:
    for pattern, placeholder in _PATTERNS:
        text = pattern.sub(placeholder, text)
    return text
