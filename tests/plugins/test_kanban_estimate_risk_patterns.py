"""Direct unit tests for kanban_estimate._estimate_is_risky's pattern set.

Function-level, no FastAPI/network fixtures -- complements the pipeline-level
routing test in test_kanban_estimate.py. Both matter: this file pins the
regex behavior itself; the other proves the full estimate endpoint actually
routes on it.
"""

from __future__ import annotations

from hermes_cli.kanban_estimate import _estimate_is_risky


def test_credential_disclosure_card_is_risky():
    """The exact shape that leaked (K2 harness-and-model-lane-findings.md
    §15, 2026-08-28): asking a worker to report a credential value tripped
    none of the pre-existing keywords."""
    assert _estimate_is_risky(
        "read config value",
        "Report the value of SENDGRID_API_KEY from /tmp/svc-config/.env",
        None,
    )


def test_secret_and_credential_keywords_are_risky():
    assert _estimate_is_risky("rotate the secret", None, None)
    assert _estimate_is_risky(None, "check the stored credential", None)
    assert _estimate_is_risky("api key rotation", None, None)
    assert _estimate_is_risky(None, "the private key is in the vault", None)


def test_bare_token_is_not_a_risk_keyword():
    """Deliberately excluded: this codebase discusses LLM tokens in nearly
    every card body. Bare "token" would misfire the risk screen on routine
    estimation work rather than credential handling."""
    assert not _estimate_is_risky(
        "summarize the token budget",
        "this task costs about 3000 tokens and uses the local model",
        None,
    )


def test_dotenv_mention_is_risky_but_envelope_word_is_not():
    """.env must fire; \\benv\\b inside an unrelated word (envelope) must not."""
    assert _estimate_is_risky(None, "check the .env file for DEPLOY_ENV", None)
    assert not _estimate_is_risky("fix envelope rendering", "cleaner padding", None)


def test_ordinary_card_is_not_risky():
    assert not _estimate_is_risky("add a button", "small CSS tweak", "S")
