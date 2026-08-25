# SIG-20260813-05 — DeepSeek ships first-party agent harness (`dsh`, MIT, ~40k★ same day); Tech2Wild shows V4 Flash local (dspark) inside it at ~75–94 tok/s

```yaml
id: SIG-20260813-05
date: 2026-08-13
title: "Tech2Wild: 'Deepseek Harness has Deepseek v4 Flash Local running at 75 tok/s' + screenshot of official DeepSeek Harness web UI. Verified: deepseek-ai/deepseek-harness — first-party OSS agent harness (created 2026-08-13, MIT, ★~39.9k at read, TypeScript, Cordis plugin architecture, 'Everything is a Plugin', developer preview with breaking-change warning). UI footer in shot: model DeepSeek V4 Flash (dspark), TTFT avg 3.5s, ~94 tok/s, 8 turns / 47 steps, LLM 4m50s, tool 2m22s, cache hit 0%, input ~956K tok. Pair with our DS4 Flash lane + agent-harness-compare — not a pull-into-T1000."
index_title: "DeepSeek Harness (dsh) first-party same-day MIT ★~40k — plugin/Cordis agent OS. Community shot: Flash (dspark) ~75 tweet / ~94 UI footer tok/s. Competitive intel + harness patterns; do NOT adopt as desk brain. Steal = plugin composition + trajectory UI + honest step metrics footer."
source_url: "https://x.com/Tech2Wild/status/2087943310493048842"
source_url_2: "https://x.com/Tech2Wild/status/2087942252584681784"
canonical_repo: "https://github.com/deepseek-ai/deepseek-harness"
canonical_docs: "https://github.com/deepseek-ai/deepseek-harness/blob/master/README.md"
index_links: [repo]
bucket: harness
posture: steal
steal_rank: P1
confidence: high
hardware_fit: [spark, mbp, none]
stacks_touched: [t1000]
related_plans:
  - "agent-harness-compare"
  - "B17"
  - "flash-lane-doctrine"
  - "SIG-20260808-06"   # DS4 / Entrpi family
  - "SIG-20260813-04"   # Bot Mode same day multi-agent UX wave
status: open
status_note: "**OPEN — competitive harness, no install.** Same-day viral first-party repo; star count is real GitHub API but treat as hype-week. Numbers are third-party screenshot, not our fleet. Primary steal is product patterns (plugin seams, trajectory tab, footer telemetry), not replacing Hermes."
distill: none
```

## 1. Claim

[@Tech2Wild](https://x.com/Tech2Wild/status/2087943310493048842) (41 likes / ~3.1k views): *“Deepseek Harness has Deepseek v4 Flash Local running at 75 tok/s”* quoting own *“Really Liking the Harness… pairs perfect with Deepseek v4 Flash Local.”*

Screenshot is the **DeepSeek Harness** desktop/web shell (`deepseek HARNESS`), not Hermes.

## 2. What we verified

| Check | Result |
|---|---|
| Repo | `deepseek-ai/deepseek-harness` — **MIT**, created **2026-08-13T11:56Z**, pushed same day, language **TypeScript**, description *“DeepSeek Harness: Everything is a Plugin.”* |
| Stars (API) | **~39,866** / forks ~3,120 at read — first-party org, still **developer preview** README: *THERE WILL BE COMPATIBILITY-BREAKING CHANGES* |
| Run | `npx @deepseek-ai/dsh web` → `http://127.0.0.1:3080` |
| Architecture claim | Cordis plugin host ([cordiverse/cordis](https://github.com/cordiverse/cordis)); topic `dsh-plugin` for ecosystem |
| Screenshot UI | Workspaces · Chat/Trajectory · tool chips (`web_search`, `web_fetch` missing until restart after preset change) · model picker **DeepSeek V4 Flash (dspark)** |
| Footer metrics (read off image) | 8 turns · 47 steps · LLM 4m50s · Tool 2m22s · **TTFT avg 3.5s · ~94 tok/s** · Cache hit 0% · Input ~956K tok |
| Tweet vs footer | Tweet **75** tok/s; footer **~94** — treat as same run ballpark, **claimed not fleet-measured** |
| Our DS4 context | kevin-spark DS4 Flash lane exists; 75–94 decode-ish is in the range of *good* Flash numbers people publish, still needs our bench contract |

Hardware pre-filter: N/A (harness product), Flash itself is on our Spark class.

## 3. Takeaways (max 5)

- DeepSeek is no longer “model only” — they shipped a **competing agent OS** the same week as Hermes Bot Mode / subagent orchestra. Harness war, not just weight war.
- **Plugin = unit of composition** (Cordis) is the ideological opposite of Hermes “narrow core + skills/CLI.” Useful foil for `agent-harness-compare`.
- Trajectory tab + **step/TTFT/tok/s/cache footer** is better default observability than our worker cards often get — steal the *footer shape*, not the app.
- `web_fetch` only after session restart when preset mounts at process start — classic “config not hot” footgun; document for any plugin host we build.
- Do **not** curl\|npx this onto the desk control plane.

## 4. Steals

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| S1 | **Session footer telemetry** — turns · steps · LLM wall · tool wall · TTFT · tok/s · cache% · in/out tokens | Add to kanban worker completion summary + optional TG notify line (MESH-TEL cousin) | **P1** | open |
| S2 | Trajectory / tool-trace as first-class tab next to Chat | When reviewing agent UX, prefer trace tab over scrolling chat for debug | P2 | watch |
| S3 | First-party model vendor ships harness → treat as competitive SoT in harness-compare, not install candidate | One row in agent-harness-compare matrix: dsh / Hermes / Claude Code | P2 | fold |

**Primary steal:** S1

## 5. Do not

- Install `npx @deepseek-ai/dsh` as T1000 brain or default coding lane.
- Quote 75/94 as *our* Flash decode without a named spark bench row.
- Assume ★40k means stable API (README promises breaks).

## 6. Next action

- [x] entry + INDEX
- [x] STEALS S1
- [ ] optional: comment S1 onto MESH-TEL / `t_d1669cdd` when touched
- [ ] no card

## 7. Chat blurb

**SIG-20260813-05** · harness · steal **P1** · high  
DeepSeek Harness (`dsh`) first-party MIT same-day ★~40k. Shot: Flash (dspark) ~75–94 tok/s + rich footer metrics.  
**Steal:** session footer telemetry shape. No install.
