# SIG-20260808-02 — Codex Router (multi-model into Codex + subagents)

```yaml
id: SIG-20260808-02
date: 2026-08-08
title: "Codex Router — external models + Flash subagents in Codex"
source_url: "https://x.com/av1dlive/status/2085700091017593226"
canonical_repo: "https://github.com/duolahypercho/codex-router"
canonical_docs: ""
bucket: router
posture: steal
steal_rank: P1
confidence: medium
hardware_fit: [cloud, mbp]
stacks_touched: [t1000]
related_plans: ["local-inference-fleet", "Fable model-stack review", "SIG-20260807-04 OMH"]
status: open
distill: none
```

## 1. Claim
Viral setup: cancel expensive Claude; use **DeepSeek V4 Flash** (and others) as **Codex subagents** via **codex-router** — local credential-isolating router merges external models into Codex picker; “toggle subagent models → all selected.”

## 2. What we verified
- Repo MIT, JS, ~900★; independent community (not OpenAI-endorsed)
- Routes Anthropic/Kimi/DeepSeek/xAI/opencode/Qwen/GLM/etc. into Codex App/CLI via Responses API
- Guided install curl|sh; preserves Codex login; keys via local hidden prompt
- Subagent multi-model is the productized flex in the tweet
- Aligns with Ryan’s “orchestration > one model” and cost discipline — **but** expands API-key surface if abused

## 3. Takeaways
- **Subagents ≠ same model as parent** is the cool, shippable idea
- Router as local sidecar (credential isolation) > scattering keys in every app
- Flash-class for width/subagents; keep frontier/subscription for hard parent (matches McNab width lane)
- Codex-specific install is not Hermes SoT — pattern ports, not dependency
- Hype “cancelled $200 Claude” = marketing; keep subs if they earn keep

## 4. Steals

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| S1 | **Parent strong / subagents cheap-fast** | Hermes `delegate_task`: default child model = Flash/coder/local; parent stays Grok/Claude | P1 | open |
| S2 | Local router sidecar, isolated creds | Optional later; prefer Hermes-native provider config first | P2 | open |
| S3 | Picker shows only authed models | Don’t list dead Spark/Ollama routes | P1 | open |

**Primary steal:** S1 (heterogeneous subagent models)

## 5. Do not
- curl codex-router into T1000/Hermes gateway
- Add provider API keys culture (Ryan: subscriptions + local first)
- Replace xAI/Claude subs without measuring quality
- Feed K2 Distillery product

## 6. Next action
- [x] entry + INDEX + STEALS
- [ ] when implementing model router: explicit **delegate/default child model** ≠ parent
- [ ] no install

## 7. Chat blurb
Codex-router hype = multi-model Codex + Flash subagents. Steal **cheap/fast subagents under strong parent** for Hermes delegate; don’t install their curl stack or key farm.
