#!/usr/bin/env python3
"""Task-tier router on TypeSafe Jev.

Maps a task description to a model tier + starting reasoning depth using Jev
as the classifier. Low-confidence answers fall back to the main agent.

Usage:
    python3 model-router.py "task description"
    python3 model-router.py            # read task lines from stdin
"""
import json
import sys

from typesafe_sdk import Choice, Score, TypeSafeClient

# Tier table: adjust models and criteria to your own setup.
TIERS = {
    "mechanical": {
        "model": "gpt-5.6-luna", "effort": "low",
        "desc": "Path enumeration, field extraction, tag audits, frozen-text diffing; if a tool can do it, do not delegate",
    },
    "general": {
        "model": "gpt-5.6-sol", "effort": "medium",
        "desc": "Routine rewrites from an approved master draft, source checks, like-for-like data cleanup",
    },
    "engineering": {
        "model": "gpt-5.6-terra", "effort": "medium",
        "desc": "Code and infra localization, well-specified implementation tasks, reproducible fixes",
    },
    "review": {
        "model": "gpt-5.6-sol", "effort": "high",
        "desc": "Fact re-verification, conflicting-metric arbitration, final acceptance of deliverables (engineering re-checks may use the coding model)",
    },
    "deep": {
        "model": "main agent (escalate to flagship if needed)", "effort": "high~xhigh",
        "desc": "Faults unresolved after several rounds, cross-cutting strategy trade-offs, strong narrative-technical coupling, major uncertainty",
    },
}

STATE_TMPL = (
    "Task dispatch for a media/content project. Available tiers and their criteria:\n"
    + "\n".join(f"- {k}: {v['desc']}" for k, v in TIERS.items())
    + "\n\nTask description: {task}"
)

EFFORT_RUBRIC = [
    "1.0 requires checking assumptions, counterexamples, cross-file logic (acceptance level)",
    "0.7 routine multi-step work, medium reasoning",
    "0.4 mechanical checks, complete input, fixed rules",
    "0.0 pure lookup or single-step operation",
]


def route(client, task: str) -> dict:
    r = client.system_one(
        state=STATE_TMPL.format(task=task),
        questions={
            "tier": Choice(
                instructions="Which tier does this task belong to, per the tier criteria? "
                             "Note: if a plain tool/script can do it, choose the mechanical tier instead of delegating.",
                criteria={k: v["desc"] for k, v in TIERS.items()},
            ),
            "effort_need": Score(
                instructions="Reasoning-depth requirement of this task, 0 to 1",
                criteria=EFFORT_RUBRIC,
            ),
        },
    )
    tier = r.answers["tier"]
    effort = r.answers["effort_need"].score
    conf = tier.confidence
    result = {
        "tier": tier.choice,
        "model": TIERS[tier.choice]["model"],
        "effort_hint": TIERS[tier.choice]["effort"],
        "jev_effort_score": round(effort, 2),
        "confidence": round(conf, 2),
        "probabilities": tier.probabilities,
    }
    # Gate: low confidence escalates to the main agent
    if conf < 0.6:
        result["gate"] = "LOW CONFIDENCE -> handle in the main agent, or re-describe the task"
    return result


if __name__ == "__main__":
    tasks = sys.argv[1:] or [ln.strip() for ln in sys.stdin if ln.strip()]
    try:
        client = TypeSafeClient()
    except Exception:
        sys.exit(
            "Missing TypeSafe API key.\n"
            "  1. Get a key at https://typesafe.ai\n"
            "  2. export TYPESAFE_API_KEY=<your key>   (or put it in your agent's .env)\n"
            "Then re-run this command."
        )
    with client:
        for t in tasks:
            res = route(client, t)
            print(f"Task: {t[:60]}")
            print(json.dumps(res, ensure_ascii=False, indent=2))
            print("-" * 60)
