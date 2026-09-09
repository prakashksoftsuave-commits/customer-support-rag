"""Langfuse tracing glue. Unlike LangSmith, Langfuse's LangChain integration has no global
auto-instrumentation — a callback handler has to be attached to each ``.invoke()`` call. This
module does that attaching so callers (chain.py) don't have to think about it, and so
answer_question()/condense_question() keep working exactly the same whether tracing is on or off.
"""

from functools import lru_cache

from src.rag.config import LANGFUSE_TRACING_ENABLED


@lru_cache(maxsize=1)
def _handler():
    from langfuse.langchain import CallbackHandler

    # No args: reads LANGFUSE_PUBLIC_KEY/LANGFUSE_SECRET_KEY/LANGFUSE_HOST from the environment.
    return CallbackHandler()


def with_tracing(run_config: dict | None) -> dict | None:
    """Merge the Langfuse callback into a LangChain run config. No-op if tracing is disabled —
    callers' own ``tags``/``metadata`` (e.g. week5-trace, streamlit-chat) pass through unchanged
    either way, since Langfuse's handler reads those same standard LangChain config keys."""
    if not LANGFUSE_TRACING_ENABLED:
        return run_config
    cfg = dict(run_config or {})
    cfg["callbacks"] = [*cfg.get("callbacks", []), _handler()]
    return cfg
