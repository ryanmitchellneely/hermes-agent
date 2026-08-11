# SIG-20260809-03 — OpenKB: compile documents into a wiki instead of re-searching them

```yaml
id: SIG-20260809-03
date: 2026-08-09
title: "OpenKB (VectifyAI/PageIndex) — LLM compiles docs into an interlinked wiki; no vector DB"
index_title: "OpenKB — compile docs into an interlinked wiki, no vector DB (we own this pattern twice, neither compiles)"
index_links: [repo]
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
status_note: "spiked 08-09 — verdict holds (pattern-mine, no adopt); see entry §9"
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

---

# 9. SPIKE RESULT — 2026-08-09 (bounded, throwaway, no keys)

**Verdict: the compile layer works on local hardware; the query layer does not. Model choice is
the whole ballgame, and it is not the obvious one.**

Ran for real: `openkb 0.4.5` in a throwaway venv (`/tmp/openkb-spike-20260809`, 593 MB, disposable),
3 signal-log entries as the corpus, Spark Ollama via the MBP tunnel `:11435`. **Zero API keys, no
`.env` written, nothing installed into `~/.t1000` or the T1000 venv.**

## 9.1 Config that works (verbatim)

```yaml
# .openkb/config.yaml
language: en
model: ollama/qwen3-coder:30b
pageindex_threshold: 20
concurrency: 2
litellm:
  drop_params: true    # Ollama rejects several OpenAI-only params
  timeout: 3600        # default timeout aborts a local compile mid-call
  num_retries: 2
```
Plus `export OLLAMA_API_BASE=http://127.0.0.1:11435`. `openkb init` **still prompts for an API key
even with `--model`** — pipe stdin (`printf '\n\n\n' | openkb init --model ... --language en`) or it
aborts. The `No LLM API key found` warning on every `add` is cosmetic for local models.

## 9.2 The result that matters: gpt-oss:120b FAILED, qwen3-coder:30b PASSED

| | `ollama/gpt-oss:120b` | `ollama/qwen3-coder:30b` |
|---|---|---|
| Wall time, 3 docs | 99 s | 171 s |
| Summaries | **3 written, ALL EMPTY** (104–221 B, frontmatter only) | 3 populated (~2.5 KB each) |
| Concept pages | **0** — `Failed to parse concepts plan` ×3 | **9** |
| Entity pages | **0** | **9** |
| Cross-doc synthesis | none | **yes** — `update: agent-width` (doc 2 updating doc 1's concept) |
| CLI exit | `[OK] added to knowledge base` ×3 | `[OK]` ×3 |

**gpt-oss:120b is a reasoning model and does not honor OpenKB's JSON output contract.** It burns the
budget on reasoning and emits prose. The salvaged fragment written to disk proves it verbatim:

```
The user asks: Write a summary page for this document in Markdown. Return a JSON object with keys ": "description"
   }
```

**This is the same failure class as DS4 Flash's empty `content` / full `reasoning_content`** that
`reasoning_effort=none` fixed on the code lane — a third instance of the same trap.

**Direct LiteLLM calls do NOT reproduce it** (all four combos below returned valid JSON), because an
explicit *"Return ONLY valid JSON, no prose"* is enough to steer it. OpenKB's prompts are not.
Do not "verify the plumbing" and conclude the model works — the plumbing was never the problem.

| call | latency | content | reasoning |
|---|---|---|---|
| `ollama/` | 11.4 s | 1124 B ✅ | 0 |
| `ollama/` + `reasoning_effort=low` | 7.3 s | 1048 B ✅ | 0 |
| `ollama_chat/` | 17.6 s | 1215 B ✅ | 1817 |
| `ollama_chat/` + `reasoning_effort=low` | 14.6 s | 2401 B ✅ | 142 |

## 9.3 ⚠️ `openkb add` reports `[OK]` on a silently empty compile

All three gpt-oss docs printed `[OK] ... added to knowledge base`, `index.md` listed all three, and
**every page body was blank.** Only the `concepts-plan` step warned; the empty *summary* was silent.
A scheduled compile on a reasoning model would produce a confident, growing, empty wiki.
**Any adoption must assert non-empty page bodies, not exit code.**

## 9.4 Accuracy — numbers held, relationships did not

Checked generated claims against source entries. **Numbers were faithful**, including hedges:
`+27%` ✅ (source line 1/28), `2.4–3.3× prefill` ✅ (line 39, and the page correctly said
*"claimed by the fork"*), `62.5 agg tok/s` ✅, `2.9 tokens/step at 74% accept` ✅ (line 31),
worktree isolation ✅ (lines 37/52). No invented figures found.

**One clear factual error, and it is a linking error.** `entities/qwen3.md` contradicts its own
frontmatter one line later:

> frontmatter: *"developed by **Alibaba**"* → body: *"Qwen3 is a family of large language models
> developed by **[[entities/nvidia]]**."*

NVIDIA appears in the same source (they published the KV-transfer work), so cross-linking grabbed the
nearest entity and manufactured a false relationship. **The compiled-wiki risk is fabricated edges,
not fabricated numbers.**

## 9.5 The staleness finding — sharper than the tool

`concepts/agent-width.md` presents McNab's 62.5 agg tok/s as *"demonstrating that hardware can
support high concurrency"* — with **no trace of our own N=1→4 ladder showing almost no aggregate
gain.** That is not a hallucination: the disconfirming result **lives only on kanban `t_9c7208c2`
and was never written back into `SIG-20260807-03`.**

**A compiled wiki is exactly as current as the entries, and will propagate a claim we have already
disproven, in confident prose, with citations.** Write results back to entries before compiling
anything. This strengthens S1 and adds: **measurement results belong in the entry, not only the card.**

## 9.6 Layer 2 (generators) fails on a local 30B

```
openkb query "..." → [ERROR] Query failed: Max turns (50) exceeded   (126 s)
```
The agentic tool loop did not converge in 50 turns. Clean split:
**Layer 1 (compile) = local-viable. Layer 2 (query/chat/Skill Factory) = not, on a 30B coder.**
This is the same eval-vs-worker split as Flash (9/9 vs 1/13): local models do single-shot structured
generation well and multi-turn agentic loops badly.

## 9.7 Ops notes

- **Cold load of `gpt-oss:120b` = ~158 s** of a 159 s call (decode itself 37.2 tok/s). Budget cold
  start separately from throughput; it dwarfs it.
- `qwen3-coder:30b` sits at **48.0 GB resident** (not its 18.6 GB file) once ctx is allocated, and
  **evicted `gpt-oss:120b`**. A compile job is not free on a box someone else is using.
- Compile cost ≈ **57 s/doc** at concurrency 2 → ~13 min for the 14 signal entries, ~3 h for all
  197 research files. Batch/overnight work, not interactive.

## 9.8 Revised verdict

**Unchanged: pattern-mine, do not adopt as a runtime.** The spike did not surface a reason to run
OpenKB on the estate — it surfaced three things worth more than the tool:

1. A **third instance** of the reasoning-model empty-output trap → belongs in the model desk doctrine.
2. **Silent-empty-success** as a failure mode any compile job we build must assert against.
3. **Fabricated edges** as the real cost of auto-cross-linking, and **entry staleness** as the thing
   that makes a compiled wiki actively misleading rather than merely incomplete.

S1 (generate `INDEX.md` from `entries/` frontmatter) is still the cheap win and needs none of this.
