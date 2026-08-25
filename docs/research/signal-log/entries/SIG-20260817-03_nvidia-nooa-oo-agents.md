# SIG-20260817-03 — NVIDIA NOOA (labs-OO-Agents): agent = Python class; `...` methods are LLM. Research preview. Don’t pip install.

```yaml
id: SIG-20260817-03
date: 2026-08-17
title: "Sumanth_077: 'NVIDIA open-sourced the Pythonic way to build AI agents' — NOOA (NVIDIA Object Oriented Agents). Agent = one Python class: fields=state, methods=capabilities, docstrings=prompts, types=contracts. Real method bodies stay deterministic; `...` bodies become LLM-driven. Model acts by writing Python in a Jupyter-style REPL with self/imports. pytest/trace/refactor. Honest README: research software, not a sandbox. Paper arXiv 2607.20709 (Jul). Repo NVIDIA-NeMo/labs-OO-Agents."
index_title: "NVIDIA NOOA: agent=class, `...`=LLM, CodeAct REPL. July paper, 0.x research. Watch — Prime-class, not a desk install. Don't pip install nooa."
source_url: "https://x.com/Sumanth_077/status/2089356754702463167"
canonical_repo: "https://github.com/NVIDIA-NeMo/labs-OO-Agents"
canonical_docs: "https://arxiv.org/abs/2607.20709"
index_links: [repo, docs]
bucket: harness
posture: watch
steal_rank: P2
confidence: high
hardware_fit: [none]
stacks_touched: [t1000]
related_plans:
  - "agent-harness-compare"
  - "SIG-20260807-02"
status: open
status_note: "**OPEN — recap of a July paper, no install.** Tweet + screenshot + first-party README/safety fetched. ★1,731 Apache-2.0 (badge), created 2026-07-20, still pushing today. Hardware N/A. Don't `uv add nooa` onto HERMES_HOME. Don't run unsandboxed REPL."
distill: none
```

## 1. Claim

[@Sumanth_077](https://x.com/Sumanth_077/status/2089356754702463167) (76.7k fol; 202 likes / 48 RT / 204 bookmarks / 18k views; note tweet):

NVIDIA open-sourced **NOOA** — collapse prompts / tool schemas / callbacks into **one Python class**. Methods with a real body stay Python; methods with `...` are LLM-implemented at runtime. Model writes Python in a REPL with `self`. Test with pytest.

Screenshot is the official README hero (Apache 2.0 badge, SupportAgent example).

## 2. What we verified

| Check | Result |
|---|---|
| Repo | `NVIDIA-NeMo/labs-OO-Agents` created **2026-07-20** · pushed **2026-08-17 18:37Z** · ★**1,731** / 235 forks · LICENSE present (badge Apache-2.0; GitHub SPDX NOASSERTION) |
| Paper | [arXiv 2607.20709](https://arxiv.org/abs/2607.20709) — ~1 month old. Tweet is a recap, not a ship |
| Blog | [Six agent harness capabilities…](https://developer.nvidia.com/blog/six-agent-harness-capabilities-for-higher-model-performance/) |
| Install | `uv add nooa` / `pip install nooa` + extras `cli` / `memory` / `bench` |
| Safety (README, load-bearing) | **Research software.** AST checks + module deny-lists are **defense-in-depth, not containment.** `open()` / `importlib` / reflection escape. Containment = container / VM / [OpenShell](https://github.com/NVIDIA/OpenShell). Do not run on primary filesystem |
| Hardware pre-filter | **N/A** |

## 3. Takeaways (max 5)

- Same family as **Prime Agent CodeAct** (persistent IPython) — `SIG-20260807-02`. Not a new axis.
- The cute trick is **`...` vs real body** as the LLM/deterministic split. T1000 already splits tools (deterministic) vs skills (procedural markdown). Don’t rewrite the house OS as classes.
- pytest-able agents is a **library** story. Desk SoT is gateway + kanban + never-auto-send.
- They are more honest than the tweet: **not a sandbox.**
- 0.x / RELEASING.md (community writeups): public API can change.

## 4. Steals

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| S1 | **Deterministic method vs `...` LLM method** in one object | Optional one-row add to `agent-harness-compare` (NOOA next to Prime). Do not port the REPL onto the desk | **P2** | watch |

**Primary steal:** S1 (not P1 — no STEALS row, no card)

## 5. Do not

- `uv add nooa` / `pip install nooa` onto `~/.t1000` or as a Telegram brain.
- Run the Jupyter-style REPL unsandboxed on the MBP / Spark.
- Treat “NVIDIA open-sourced agents” as a reason to replace Hermes skills with Python classes.
- Dual-drive NOOA + T1000.

## 6. Next action

- [x] entry + INDEX
- [ ] none — **no STEALS P0/P1 row, no card**

## 7. Chat blurb

**SIG-20260817-03** · harness · **watch P2** · high
NVIDIA NOOA: agent = Python class, `...` = LLM, CodeAct REPL. July paper. Research, not a sandbox.
**Do not pip install.** Prime-class, not a desk OS.
