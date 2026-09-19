# jev-browser-agent

Experiments combining the official [ego-browser](https://github.com/ego-lite) skill with TypeSafe's Jev System One model: ego-browser handles observation (snapshot refs) and actions, Jev handles each step's decision ("which operation, which element") in roughly one second at near-zero cost.

Part of a public test journal published at [@smardio](https://x.com/smardio); the full write-up (in Chinese) lives in the mai-unstoppable content project `jev-decision-model`.

## What is here

| Path | What it is | Status |
|---|---|---|
| `skill/SKILL.md` | Installable agent skill: the ego-browser + Jev graft, with rules and run log | First live run 2026-09-19 (X posting, 2 Jev decisions, published) |
| `pilot/model-router.py` | Task-tier router: maps a task description to model + reasoning tier with per-tier probabilities | 5/5 on the tier table's own example tasks |
| `references/jev-browser-acceleration.md` | The graft design: snapshot refs as Choice criteria keys, speculative fan-out per step, safety rules | Design doc |

## The pattern in one minute

Each loop step:

1. **Observe** — `page.snapshot()` from ego-browser; refs like `@21` become the keys of a Jev `Choice` criteria map.
2. **Decide** — one TypeSafe request, speculative fan-out: "which operation" and "which target for each operation" are asked together; only the branch matching the answered operation is read.
3. **Act** — `page.click("@21")` etc., receipt appended to history.
4. **Gate** — confidence below 0.6 escalates to the outer LLM (or the human); DONE is only trusted from visible evidence.

Measured on a real X (Twitter) posting run: each Jev decision was 280–740 ms and roughly 600 input / 50–80 output tokens; two decisions drove the whole publish.

## Rules the experiments enforced

- Page text is untrusted data, never instructions (prompt-injection defense in the decision instructions).
- URLs chosen by a model pass a DNS-resolution check (block private/loopback/link-local, including cloud metadata endpoints) before navigation — pattern from [ndrezn/ts-browser-agent](https://github.com/ndrezn/ts-browser-agent) (MIT-licensed instruction text in that repo comes from browser-use/jev-ultrafast; we studied the architecture, no code is redistributed here).
- Login and CAPTCHA flows are handed off to the human via ego-browser's handOff; a classifier never bypasses them.
- ego-browser's TaskSpace / user-takeover rules always win; this pattern only changes *who decides the next step*.

## Honest limits (measured, not marketed)

- Objective decisions (routing, classification, button state) were reliable: 5/5 tier routing, zero drift across 5 repeats on the same decision.
- Subjective review (creative ranking, style scoring) was unstable — two methods disagreed and confidence dropped to 0.26. Keep those with the LLM/human.
- Jev's auxiliary Score output can exceed its own scale; we only trust its Choice routing + confidence.

## Setup

**Prerequisite: a TypeSafe API key.** Every script and skill here calls the TypeSafe API; without a key nothing runs. Get one first:

1. Sign up at [typesafe.ai](https://typesafe.ai) and create an API key.
2. Make it available to the SDK in one of these ways:

```bash
# Option A — shell environment
export TYPESAFE_API_KEY=<your key>       # add to ~/.zshrc / ~/.bashrc to persist

# Option B — agent .env (recommended for agent use)
#   Hermes: append to ~/.hermes/.env
#   Codex / other agents: append to the .env your agent loads
TYPESAFE_API_KEY=<your key>
```

Keep the key server-side / out of committed files — never hardcode it in scripts.

Then install and run:

```bash
pip install typesafe-sdk          # Python SDK
python3 pilot/model-router.py "task description"   # route one task
```

For the browser pattern you also need the [ego-browser](https://github.com/ego-lite) skill installed and running.

`skill/SKILL.md` installs like any Agent Skill: copy the folder into your skills directory (for Hermes: `~/.hermes/skills/jev-browser-agent/`).

## License

MIT
