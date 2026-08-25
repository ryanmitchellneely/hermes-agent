# SIG-20260813-08 — 0xSero: Fable orchestrates a fleet of local models (mainly Deepseek-v4-flash-0731) to save Fable tokens at same quality, slower

```yaml
id: SIG-20260813-08
date: 2026-08-13
title: "0xSero (61.8k followers): 'Fable orchestrates a fleet of local models, mainly Deepseek-v4-flash-0731. Saves me a lot of Fable tokens and gets the same results, albeit slower.' Screenshot attached (Fable + local fleet UI). Directly validates our desk doctrine: strong cloud chair + local workers (Flash/120b) for token burn; quality bar = same results, accept latency. Not a new engine — a routing posture we already run (orchestrator Flash / worker 120b / code Flash)."
index_title: "Fable+local Flash fleet (0xSero): same results, fewer Fable tokens, slower. Confirms parent-strong/local-workers posture we already ship. Steal = explicit token-arbitrage success criterion in router scoreboards — not a new stack."
source_url: "https://x.com/0xSero/status/2087832297059889414"
canonical_repo: ""
canonical_docs: ""
bucket: router
posture: steal
steal_rank: P1
confidence: high
hardware_fit: [spark, mbp]
stacks_touched: [t1000]
related_plans:
  - "t1000-model-desk"
  - "flash-lane-doctrine"
  - "SIG-20260808-02"  # parent strong / subagents cheap
  - "B22"
status: open
status_note: "**OPEN — doctrine confirm.** Screenshot path banked at fetch; numbers are qualitative (saves tokens, slower, same results). No install. Primary steal = write token-arbitrage as an explicit scoreboard axis."
distill: none
```

## 1. Claim

[@0xSero](https://x.com/0xSero/status/2087832297059889414) (225 likes / 83 bookmarks / ~12.2k views):

> Fable orchestrates a fleet of local models, mainly **Deepseek-v4-flash-0731**.  
> Saves me a lot of Fable tokens and gets the **same results, albeit slower**.

## 2. What we verified

- Post + media fetched (fxtwitter + image bytes on disk).
- Model id **Deepseek-v4-flash-0731** is exactly our Flash family naming (kevin-spark DS4 lane / signal log family).
- Claim shape matches our already-shipped posture: expensive chair (Fable/Grok/Opus) + local workers; success = **quality parity**, not tok/s parity.
- No independent tok/s or pass-rate table in the tweet — qualitative.

## 3. Takeaways (max 5)

- Token arbitrage is a **first-class product feature** people brag about, not just our cost law.
- **Slower is OK** if results match — kill pure-speed scoreboards as the only gate.
- Flash-0731 is the community default local workhorse in this meme — keep our Flash doctrine current.
- Orchestration layer (Fable here, Hermes/kanban for us) owns routing; locals don’t need to be “the brain.”
- Complements Subagent Orchestra: fleet can be **models** or **agents** — same parent control problem.

## 4. Steals

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| S1 | **Token-arbitrage success criterion** — “same results, fewer paid tokens, accept latency” as explicit router/eval axis | Add to standings/scoreboard: paid_tokens_saved × quality_hold vs pure tok/s | **P1** | open |
| S2 | Name the local default in the story (Flash-0731) so fleet is greppable | Keep flash-lane-doctrine + worker pins honest in chat | P2 | already mostly |

**Primary steal:** S1

## 5. Do not

- Pivot desk default brain to Flash because Sero did for Fable workers.
- Claim “same results” without our golden/repair battery.

## 6. Next action

- [x] entry + INDEX + STEALS
- [ ] fold S1 into router scoreboard notes when next touched — no new card

## 7. Chat blurb

**SIG-20260813-08** · router · steal **P1** · high  
Fable + local Flash-0731 fleet: same quality, fewer Fable tokens, slower.  
**Steal:** make token-arbitrage an explicit scoreboard axis. Confirms our posture.
