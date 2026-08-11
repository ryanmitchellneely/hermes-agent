# SIG-20260808-01 — Cloudflare Computer (agent virtual filesystem)

```yaml
id: SIG-20260808-01
date: 2026-08-08
title: "Cloudflare Computer — give your agent a computer"
index_title: "Cloudflare Computer — agent virtual filesystem"
source_url: "https://x.com/trending_repos/status/2085699382096060827"
canonical_repo: "https://github.com/cloudflare/computer"
canonical_docs: "https://github.com/cloudflare/computer/tree/main/docs"
bucket: harness
posture: watch
steal_rank: P2
confidence: high
hardware_fit: [cloud]
stacks_touched: [t1000]
related_plans: []
status: open
distill: none
```

## 1. Claim
Cloudflare open-sources **Computer**: a virtual filesystem living in a **Durable Object** (SQLite SoT) with pluggable runtimes — container+FUSE, isolate shell (just-bash), isolate JS — so agents get a durable workspace + exec, not only chat tools. Trending (~5k★ in ~day).

## 2. What we verified
- MIT, TypeScript monorepo; **PREVIEW ONLY** — APIs unstable, not production
- Architecture: DO holds authoritative FS; `workspace.runtime.exec(source, { backend })`
- Backends: full Linux container via `computerd` FUSE sync; Worker shell; Worker JS with `node:fs`-shaped API
- Examples: think agent, side-by-side runtime compare, pandoc PDF, artifacts publish
- No unsolicited PRs; design docs forward-looking

## 3. Takeaways
- **Durable workspace SoT** separate from model context is the real idea
- Multi-backend exec behind one API = router for *compute environments*, not just models
- Preview/CF-lock-in — not a T1000 gateway dependency
- Complements local terminal tools; doesn’t replace Mac/Spark HA story
- “Not a real computer” replies = fair for marketing, unfair for DO+VFS design

## 4. Steals

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| S1 | Session/workspace FS as first-class SoT | Stronger per-task scratch dirs + explicit artifact paths | P2 | open |
| S2 | One `exec` entry, pluggable backends | Abstract local vs sandbox vs VPS exec later | P2 | open |
| S3 | Side-by-side runtime compare UI | Optional for coding-lane evals | P2 | open |

**Primary steal:** S1 (workspace SoT hygiene) — conceptual only; no CF adopt.

## 5. Do not
- Depend on preview CF Computer for Pulp/T1000 prod
- Rebuild Distillery around Durable Objects
- curl into gateway host

## 6. Next action
- [x] signal-log only
- [ ] none wired

## 7. Chat blurb
CF Computer = DO-backed agent VFS + pluggable runtimes (preview). Watch; steal workspace-SoT thinking only. Not desk install.
