"""
test_agent.py — unit tests for model-config loading (no vLLM / network needed).

These cover the Pi-style models.json layer added in the pi-redesign branch:
load_model_config() reads models.json by id, with $AGENT_MODEL override and a
.env fallback. The agent loop itself needs a live model, so it is not tested here.
"""

from __future__ import annotations

from src.agent import ModelConfig, load_model_config
from src.prompts import SYSTEM_PROMPT, build_system_prompt


def test_load_model_config_reads_models_json():
    """models.json at the repo root resolves to a ModelConfig with sane fields."""
    load_model_config.cache_clear()
    cfg = load_model_config()
    assert isinstance(cfg, ModelConfig)
    assert cfg.model and cfg.base_url.startswith("http")
    assert cfg.max_tokens > 0 and cfg.context_window > 0


def test_agent_model_env_override(monkeypatch):
    """$AGENT_MODEL selects a different entry from models.json (model swap = config)."""
    monkeypatch.setenv("AGENT_MODEL", "qwen3-8b")
    load_model_config.cache_clear()
    try:
        assert load_model_config().model == "Qwen/Qwen3-8B"
    finally:
        # Don't leak the cached override into other tests.
        load_model_config.cache_clear()


def test_build_system_prompt_none_is_byte_identical():
    """No/empty/whitespace skill → byte-identical SYSTEM_PROMPT (default unchanged)."""
    assert build_system_prompt(None) == SYSTEM_PROMPT
    assert build_system_prompt("") == SYSTEM_PROMPT
    assert build_system_prompt("   \n  \t ") == SYSTEM_PROMPT


def test_build_system_prompt_appends_skill():
    """With skill text → starts with the full base prompt AND contains the skill."""
    out = build_system_prompt("RULE: write a failing test first.")
    assert out.startswith(SYSTEM_PROMPT)
    assert "RULE: write a failing test first." in out
    assert "Learned skills" in out


def test_agent_logging_follows_current_stderr():
    """Regression (audit HIGH — AUDITABILITY): the agent's logging handler must write to
    sys.stderr AT EMIT TIME, not stay bound to whatever stderr existed when logging was
    configured. eval calls run_agent inside redirect_stderr(per-task file); on a reused
    spawn-pool worker, a once-bound handler kept writing to the first task's closed stream
    → 590/627 per-task logs were 0 bytes. Configure once, then log under two different
    redirects: BOTH must receive their line."""
    import io
    from contextlib import redirect_stderr
    from src import agent as A

    A._logging_ready = False
    A.log.handlers.clear()
    A._setup_logging()                       # configure once (like the first run_agent call)
    b1, b2 = io.StringIO(), io.StringIO()
    with redirect_stderr(b1):
        A.log.info("alpha-trace")
    with redirect_stderr(b2):
        A.log.info("beta-trace")
    assert "alpha-trace" in b1.getvalue(), "log did not follow redirect #1"
    assert "beta-trace" in b2.getvalue(), "log did not follow redirect #2 (0-byte-logs bug)"
