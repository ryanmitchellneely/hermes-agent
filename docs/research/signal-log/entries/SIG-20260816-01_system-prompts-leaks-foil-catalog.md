# SIG-20260816-01 — asgeirtj/system_prompts_leaks: public catalog of vendor system prompts (foil library, not a T1000 prompt pack)

```yaml
id: SIG-20260816-01
date: 2026-08-16
title: "asgeirtj/system_prompts_leaks — 63k★ CC0 dump of leaked/extracted system prompts (Claude Fable/Opus 5 + Claude Code/Design/Cowork, ChatGPT 5.6 Sol + Codex, Gemini, Grok 4.5, OpenCode, Pi, Cursor, Perplexity, Qwen 3.8, DeepSeek, Kimi, GLM, …). WaPo interactive (2026-05-11) and CEPS AI World dashboard (2026-07-10) already consume it. Last push 2026-08-15."
index_title: "system_prompts_leaks 63k★ CC0 = foil catalog. Steal = read here before inventing a harness compare. Do NOT paste into T1000."
source_url: "https://github.com/asgeirtj/system_prompts_leaks"
canonical_repo: "https://github.com/asgeirtj/system_prompts_leaks"
canonical_docs: ""
index_links: [repo]
bucket: harness
posture: steal
steal_rank: P2
confidence: high
hardware_fit: [none]
stacks_touched: [t1000]
related_plans:
  - "agent-harness-compare"
  - "SIG-20260813-04"
  - "SIG-20260813-05"
  - "SIG-20260813-06"
  - "SIG-20260807-02"
status: open
status_note: "**OPEN — catalog verified, no ingest.** ★63,008 / forks 10,344 / CC0-1.0 / pushed 2026-08-15. No Hermes folder. Do not clone onto HERMES_HOME or overwrite desk/Grok/Claude-ACP prompts."
distill: none
```

## 1. Claim

Public GitHub archive: “leaked system prompts, captured verbatim — the hidden instructions and rules that ChatGPT, Claude, Gemini, Grok and every other AI chatbot receives before your first message.” README advertises regular updates (Grok 4.5 + Codex GPT-5.6 Sol dated July 26 2026; Claude Code Fable 5 bumped to **v2.1.232** on 2026-08-14).

## 2. What we verified

| Check | Result |
|---|---|
| Repo | `asgeirtj/system_prompts_leaks` · created 2025-05-03 · default `main` · **CC0-1.0** · ★**63,008** · forks **10,344** · watchers 719 · open issues 55 · size ~9.4 MB · last push **2026-08-15 03:58Z** |
| README | Fetched raw (20,384 B). WaPo (2026-05-11) + CEPS AI World (2026-07-10) cite it. Latitude analytics banner at top — ignore. |
| Tree | Vendor dirs: Anthropic (30) · OpenAI (37) · Google (22) · Misc (24) · xAI (12) · Microsoft (5) · Perplexity (5) · Qwen (2) · Kimi (2) · + OpenCode, Pi, Cursor, DeepSeek, GLM, Meta, Mistral, Notion. **No Hermes / T1000 folder.** |
| Recent commits | 08-14 Claude Code Fable 5 → v2.1.232; 08-14 `claude-science.md`; 08-15 rename `claude-agent.md` → `claude.md`; 08-05 `qwen3.8-max.md` |
| Structure skim (headings only, no prompt body copied) | Grok 4.5: tools + Skills + User/Memory taxonomy. Claude Code Fable 5 (~151 KB): Harness / Memory / Scratchpad / Agents / Skills / Cron* / EnterPlanMode / AskUserQuestion. OpenCode (~25 KB): Tone / Tool policy / skill / task. Claude Cowork (~280 KB): computer-use + scheduled tasks + auto-memory. Claude Design (~203 KB): Design Components + skills + verification. |
| Hardware pre-filter | **N/A** (not a PCIe / tok/s claim) |

## 3. Takeaways (max 5)

- This is a **journalism/research dump**, not a product to install. CC0 ≠ “safe to become our system prompt.”
- Vendor prompts **rot weekly** (Claude Code Fable 5: v2.1.224 on 08-07 → v2.1.232 on 08-14). Copying one snapshot into T1000 is instant drift.
- Grok-4.5 file exists; desk is **4.6**. Treat as family foil, not current desk text. **Do not ingest leaked User/Memory blocks** (third-party PII).
- Competitor CLIs we already name in `agent-harness-compare` (Claude Code, Codex, OpenCode, Pi) have files here — **read first, invent second.**
- No Hermes leak in-tree. Don’t go looking for one as a next action.

## 4. Steals

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| S1 | **Foil catalog, not a prompt pack** — when a new coding/agent CLI ships, open *their* file here before writing a compare row | Default first-read for `agent-harness-compare`. One pattern per compare, then stop. Never paste vendor system text into `~/.t1000`. | **P2** | open |
| S2 | Claude Code cron note: stagger off `:00` / `:30` | Optional later glance at `hermes cronjob list` — not this turn, not a card | P2 | watch |

**Primary steal:** S1 (not P1 — no STEALS row, no card)

## 5. Do not

- Clone the repo onto `~/.t1000` or `~/.hermes`.
- Replace Grok / Claude-ACP / q38 / worker system prompts with leaked files.
- Quote or store leaked **user-memory** sections (PII).
- Treat CC0 + WaPo citation as legal cover to ship vendor prompts as ours.
- Open a `steals` card for “read a GitHub repo.”

## 6. Next action

- [x] entry + INDEX
- [ ] none — **no STEALS P0/P1 row, no card**
- [ ] if a future compare needs a foil, start here (Claude Code / OpenCode / Grok 4.5 headings)

## 7. Chat blurb

**SIG-20260816-01** · harness · steal **P2** · high
`asgeirtj/system_prompts_leaks` ★63k CC0 — public vendor-prompt dump (Claude Code/Design/Cowork, Grok 4.5, Codex, OpenCode, …).
**Steal:** foil catalog for harness-compare. **Do not paste into T1000.** No Hermes folder. No card.
