# SIG-20260809-03 — OpenKB: compile documents into a wiki instead of re-searching them

```yaml
id: SIG-20260809-03
date: 2026-08-09
title: "OpenKB (VectifyAI/PageIndex) — LLM compiles docs into an interlinked wiki; no vector DB"
source_url: "https://x.com/oliviscusai/status/2086318229685760115"
posted_at: "2026-08-09T05:06:42Z"
canonical_repo: "https://github.com/VectifyAI/OpenKB"
canonical_docs: "https://openkb.ai"
origin_idea: "https://x.com/karpathy/status/2039805659525644595"
bucket: harness
posture: steal
steal_rank: P1
confidence: high              # Apache-2.0, 3.3k★, README + config example read directly
hardware_fit: [spark, mbp]    # runs against local Ollama — verified in examples/configuration
stacks_touched: [t1000, k2]
related_plans:
  - "llm-wiki"                # our skill already encodes this exact pattern (v2.1.0)
  - "t_043bcb33"              # REF: agent+model doc corpus index — the cold-start map this fixes
  - "B18"                     # DevBot knowledge plane Phase 1 called for an llm-wiki bootstrap
status: open
distill: none
```

## 1. Claim

@oliviscusAI: Karpathy tweeted an idea — *what if an LLM kept compiling everything it reads into one
growing wiki instead of starting from scratch every query* — and **someone actually built it**.
OpenKB compiles what you feed it into summaries, concept pages, and entity pages, all cross-linked
and kept in sync. **No vector DB**; long PDFs are tree-indexed instead of chunked and embedded.

## 2. What we verified

Read: the repo metadata, the full README, and `examples/configuration/README.md`. Not read: the
source, the Skill Factory examples, any benchmark.

| Fact | Value |
|---|---|
| Repo | `VectifyAI/OpenKB` — **3,338★**, 356 forks, Python, **Apache-2.0** |
| Age | created **2026-04-04**, last push **2026-07-22**, tags through `v0.5.0-rc1` |
| Engine | [PageIndex](https://github.com/VectifyAI/PageIndex) tree index for PDFs ≥20 pages; `markitdown` for short docs |
| Output | plain `.md` with `[[wikilinks]]` — **Obsidian-opens natively**; pages follow Google OKF |
| Extras | `openkb skill new` (Skill Factory), `visualize`, `deck new`, web Workbench on `:7566` |
| **Local models** | **verified**: `model: ollama/llama3.1` + `litellm: {timeout: 1200, drop_params: true}` |

**The tweet's framing is ~4 months late.** "Someone actually built it" reads as a fresh drop; this is
an April project with 3.3k stars that hasn't been pushed in 18 days. Nothing wrong with it — but it
is not new information about the frontier, it is new information *to us*.

## 3. The finding that matters more than the repo — we already have this, twice, and neither is compiling

| Implementation | State (measured 2026-08-09) |
|---|---|
| Hermes skill **`llm-wiki` v2.1.0** (`~/.t1000/skills/research/llm-wiki`) | Cites the **same Karpathy gist**. `WIKI_PATH` **unset**, `~/wiki` **does not exist**. Never run. |
| OMC wiki in **KRT** (`kevin-real-estate-tools/.omc/wiki`) | **Live** — 604 files, 5.6 MB, last write **03:10 today** |
| **T1000 research corpus** (`docs/research/`) | **195 markdown files, 1.1 MB, no wiki of any kind** |

And the K2 wiki is not doing what OpenKB describes. Split by filename:

```text
604 files = 581  session-log-*.md   (auto-captured, one per agent session)
             22  curated pages      (k2-hub-architecture, engineering-conventions, two-brain, …)
              1  log.md             (151 KB append-only journal)
```

**96% of it is session logs.** The 22 curated pages were hand-authored by agents, not *compiled*
from documents. So what we run is an **append-only session journal with some doctrine pages beside
it** — it accumulates transcripts, not knowledge. The compile step — read source → summarize →
cross-reference against existing concepts → update the wiki — is the part we have never built, and
it is the entire point of the pattern.

That is the gap this signal names. The repo is optional; the gap is real either way.

### Corroborating symptom from this morning

`AGENT-MODEL-DOC-INDEX.md` §7 — the file whose whole job is to stop a cold session re-deriving the
research — listed **5 entries when 12 existed on disk**. It is hand-maintained, so it drifts the
moment someone writes an entry and forgets the index. That is precisely the failure a compile step
removes, and it does not require installing anything.

## 4. Two things this does not fix — and one correction to me

**Backup exposure, unchanged.** `.omc/` is gitignored in KRT (`.gitignore:288 → **/.omc/`), so
**0 of those 604 files are tracked**. The 581 session logs are legitimately scratch; the 22 curated
pages are not. Same class of exposure as the research corpus, on a Mac with FileVault off.

**Correction to what I told you this morning:** I said `t_498126c6` was the open card for committing
the research corpus, "blocked on your OK." It is **done** — completed 2026-08-07 21:35 — and its
body scopes only `SIG-20260806-01 … SIG-20260807-04`. `t_b4c3d9d5` (T1000 backup hour) is also
done. Meanwhile `git status docs/research` right now:

```text
 M  AGENT-MODEL-DOC-INDEX.md · signal-log/{INDEX,STEALS}.md · SIG-20260807-04
 ?? 8 entries (SIG-20260808-01 … SIG-20260809-02) + UNFINISHED-WORK-2026-08-08 + distillery sweep
```

So the newer corpus has **no open card at all**. Both cards closed with the work only partly done,
and I mis-reported it as blocked-on-you. Flagged, not carded — the board is at 44 blocked / 19 todo.

## 5. Steals (patterns only)

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| **S1** | **Compile the index, don't hand-maintain it** | Extend `scripts/signal_log_new.py` to regenerate `INDEX.md` **and** `AGENT-MODEL-DOC-INDEX.md` §7 from `entries/` frontmatter. ~30 lines, zero new dependencies, kills the staleness class permanently | **P1** | open |
| S2 | **Raw → compiled is a real layer; session logs are not it** | Our wiki accumulates transcripts. Add one compile pass over the 22 curated pages + `docs/research/` before adding any more auto-capture | P1 | open |
| S3 | **Skill Factory** — distill a portable agent skill from a corpus | Shape matches `agent-skills-estate`. Watch only: an estate already carrying ~100 skills does not need a skill generator pointed at it | P2 | open |

**Primary steal (one only): S1.** It is the cheapest, it fixes a failure we measured today, and it
is true whether or not OpenKB is ever installed.

### Bounded spike, if Ryan wants it (NOT started)

`pip install openkb` in a **throwaway venv** (never the T1000 venv), `model: ollama/gpt-oss:120b`
pointed at Spark `:11435`, compile `docs/research/` into a scratch dir. **Zero API keys** — the
config example confirms local runtimes are a supported path, so this does not touch the no-keys
rule. It also gives the 120b an actual batch job: compile is latency-tolerant and token-heavy, which
is exactly the workload profile the idle local fleet is good for and the interactive desk is not.

## 6. Do not

- **Do not `pip install openkb` into the T1000 venv.** It pulls `litellm`, `markitdown`, `pymupdf`;
  `litellm` is pinned against `openai==2.44.0` upstream. Throwaway venv or nothing.
- **Do not set `PAGEINDEX_API_KEY`.** Cloud OCR is optional; local PageIndex is the default and
  needs no key. Adding one violates the standing no-provider-keys rule.
- **Do not expose the Workbench.** README: *"Auth is off by default (local-first)."* On a tailnet
  box that is an open read of the whole KB. `OPENKB_API_TOKEN` or loopback only.
- Do not use the OAuth escape hatch — the supported subscription providers are `chatgpt/*` and
  `github_copilot/*`, and Copilot is out by doctrine.
- Do not run Skill Factory against the estate before `agent-skills-estate` has audited what is there.
- Do not read this as "our wiki is broken." It works; it is just a journal, not a compiler.

## 7. Next action (mechanical)

- [x] `INDEX.md` + `STEALS.md`
- [x] kanban comment `t_043bcb33` (corpus index REF) — S1 + the measured index-drift and git state
- [ ] no new card — the uncommitted-corpus gap and the S1 script are both offered to Ryan, not filed

## 8. Chat blurb

`SIG-20260809-03` · `harness` · **steal P1** · [OpenKB](https://github.com/VectifyAI/OpenKB) 3,338★
Apache-2.0, April project, runs on local Ollama with no keys. The steal is not the repo: **we own
this pattern twice already** (`llm-wiki` skill never run; KRT `.omc/wiki` live but **581 of 604
files are session logs**) and neither one compiles. Primary steal **S1 — generate the index from
`entries/` instead of hand-editing it**, which is exactly the drift that put 5 of 12 entries in the
cold-start map this morning.
