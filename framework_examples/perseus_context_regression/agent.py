"""A deterministic Perseus + Invarium context-regression demo.

Perseus (https://perseus.observer) is a context engine for AI agents. Before an
agent session starts, Perseus pre-loads context — files, memory, and services —
and injects a stable ``context_hash`` into the session metadata. That hash is the
fingerprint of *exactly what the agent was given to reason over*. The promise of a
context engine is simple: **same context in, same behavior out** — and when the
context changes, the behavior should change *predictably*.

This example shows the regression Invarium is built to catch. A retrieval agent is
supposed to ground every answer in the pre-loaded Q3 document by calling
``retrieve`` before it answers. When the context silently drifts — a broken
include, a stale memory store, an expired service token — the Q3 doc falls out of
the bundle, the agent answers from the model's prior instead, and the reply still
*looks* confident and complete. An exact-text test passes. Invarium fails it,
because it asserts on what the agent **did** and on the ``context_hash`` it ran
against, not on what it **said**.

Everything here is deterministic (no LLM, no API key, standard library only), so
the demo reproduces identically in CI and on anyone's laptop. The message and
metadata shapes match what a real Perseus adapter surfaces, so Invarium's
``PythonAdapter`` reads it the same way.

Two behaviors live behind one env flag, mirroring a real before/after regression:

- ``PERSEUS_CONTEXT_DRIFT`` unset -> v1 "good": Perseus pre-loads the Q3 doc, the
  agent grounds its answer via ``retrieve`` -> ``answer``.
- ``PERSEUS_CONTEXT_DRIFT=1`` -> v2 "regressed": the Q3 doc is missing from the
  loaded context. The agent skips ``retrieve`` and answers from its prior, still
  claiming the summary "completed successfully".
"""

from __future__ import annotations

import hashlib
import json
import os

from invarium import AgentResult, ToolCall


# --- The Perseus side: pre-load context and fingerprint it --------------------

# The context bundle Perseus assembles for the session. In production these come
# from files, a Perseus Vault memory store, and live services; here they are
# inlined so the demo is fully deterministic.
_BLESSED_CONTEXT: dict[str, str] = {
    "reports/q3.md": (
        "# Q3 Revenue\n"
        "Total revenue: $4.2M (+18% QoQ). Net new logos: 37. "
        "Churn: 1.9%. Largest segment: mid-market."
    ),
    "memory/company_facts.md": "Fiscal year ends December. Reporting currency: USD.",
}


def _drifted() -> bool:
    return os.environ.get("PERSEUS_CONTEXT_DRIFT", "") not in ("", "0", "false", "False")


def perseus_preload() -> tuple[dict[str, str], str]:
    """Simulate Perseus pre-loading context and injecting a ``context_hash``.

    Returns the loaded bundle and a stable SHA-256 hash over its sorted contents —
    the same fingerprint Perseus injects into session metadata.
    """
    bundle = dict(_BLESSED_CONTEXT)
    if _drifted():
        # The regression: the Q3 doc dropped out of the loaded context.
        bundle.pop("reports/q3.md", None)

    canonical = json.dumps(bundle, sort_keys=True, separators=(",", ":"))
    context_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return bundle, context_hash


def _context_hash_for(bundle: dict[str, str]) -> str:
    canonical = json.dumps(bundle, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# The hash the agent is *expected* to run against — the one you blessed. In real
# Perseus usage you pin the hash of the context bundle you certified.
EXPECTED_CONTEXT_HASH: str = _context_hash_for(_BLESSED_CONTEXT)


# --- The agent side: run with the pre-loaded context --------------------------

class PerseusContextAgent:
    """A tiny retrieval agent that runs against Perseus-preloaded context.

    ``.run(prompt)`` returns an Invarium ``AgentResult`` whose ``metadata`` carries
    the ``context_hash`` Perseus injected — exactly the free-form metadata channel
    Invarium preserves end to end (adapter -> normalization -> JSON traces).
    """

    def run(self, prompt: str) -> AgentResult:
        bundle, context_hash = perseus_preload()
        metadata = {
            "context_hash": context_hash,
            "loaded_files": sorted(bundle),
        }

        if "reports/q3.md" in bundle:
            # v1 "good": ground the answer in the retrieved doc, then answer.
            doc = bundle["reports/q3.md"]
            tool_calls = [
                ToolCall(
                    name="retrieve",
                    args={"path": "reports/q3.md"},
                    output=doc,
                    success=True,
                ),
                ToolCall(
                    name="answer",
                    args={"grounded_in": ["reports/q3.md"]},
                    output="grounded summary",
                    success=True,
                ),
            ]
            final_output = (
                "Q3 revenue was $4.2M, up 18% QoQ, with 37 net new logos and 1.9% churn. "
                "Summary grounded in reports/q3.md."
            )
        else:
            # v2 "regressed": Q3 doc missing from context. Skip retrieval and answer
            # from the model's prior — while still claiming the work completed.
            tool_calls = [
                ToolCall(
                    name="answer",
                    args={"grounded_in": []},
                    output="ungrounded summary",
                    success=True,
                ),
            ]
            final_output = (
                "Q3 revenue grew strongly quarter over quarter with healthy net new logos "
                "and low churn. Analysis completed successfully."
            )

        return AgentResult(
            input=prompt,
            final_output=final_output,
            tool_calls=tool_calls,
            steps=len(tool_calls),
            metadata=metadata,
        )


def build_agent() -> PerseusContextAgent:
    return PerseusContextAgent()
