# SIG-20260811-02 — Hermes Browser Use mode collapses 12 browser tools into one `browser_exec`, and it is ALREADY the live default on this desk

```yaml
id: SIG-20260811-02
date: 2026-08-11
title: "Luke The Dev amplifies the Nous Research announcement that Hermes Browser Use mode replaces 12 browser tools with a single browser_exec driven by the Browser Use CLI, claimed 48-66% token reduction with no accuracy drop. Verified live: the mode is not something to adopt — it is the DEFAULT and it is already active in this session"
index_title: "Hermes Browser Use mode: 12 browser tools -> 1 browser_exec, Nous claims 48-66% fewer tokens. NOTHING TO STEAL — verified ALREADY LIVE on this desk (browser.backend unset = enabled by default; this session's 34-tool selection contains browser_exec and ZERO built-in browser_*). Measured the local schema delta ourselves off the live registry: 12 tools 11,332 chars (~2,833 tok) -> browser_exec 3,196 chars (~799 tok) = -71.8% SCHEMA overhead. Two real costs found: first call pays a cold uvx download (103 packages), and browser_exec is only offered to sessions that ALSO hold terminal, because it runs model-written Python on the host"
source_url: "https://x.com/iamlukethedev/status/2086902520249827583"
canonical_repo: ""
canonical_docs: "https://hermes-agent.nousresearch.com/docs/user-guide/features/browser"
index_links: [docs]
bucket: harness
posture: adopt
steal_rank: P1
confidence: high          # post fetched verbatim via fxtwitter; every claim below measured live off this machine — config, source, the live tool registry, uvx resolution, and the official docs
hardware_fit: [mbp]
stacks_touched: [t1000]
related_plans:
  - "SIG-20260808-05"     # Hermes Agent Dock — the other Hermes-native surface signal
  - "SIG-20260807-04"     # oh-my-hermes — third-party layer we declined; this is the first-party equivalent done right
status: open
status_note: "**Nothing to steal — this is a CONFIRM-AND-DOCUMENT signal.** Browser Use mode is the Hermes DEFAULT, not an opt-in: `is_browser_use_cli_mode()` returns true when `browser.backend` is unset AND the CLI is runnable (`tools/browser_use_cli.py:107-133`). `~/.t1000/config.yaml` has **no `backend` key** and `uvx` is at `~/.local/bin/uvx` (0.11.9), so it is ON. Proven live rather than inferred: instantiating the real tool selection printed `Final tool selection (34 tools)` containing `browser_exec` and **zero** built-in `browser_*`. Measured the local schema cost off `registry.get_schema()`: the 12 built-ins total **11,332 chars (~2,833 tok)** vs `browser_exec` **3,196 chars (~799 tok)** = **-71.8%** on the schema axis (the post's 48-66% is end-to-end, a different and broader measure — do not conflate). TWO REAL COSTS: (1) no installed `browser-use` binary, so the first call shells out to `uvx` and paid a **103-package** cold download in this session's probe; (2) per the docs, `browser_exec` is offered **only to sessions that also have `terminal`**, because it executes model-written Python on the host — locked-down surfaces (a messaging-only Pulp lane) silently keep the 12 built-ins and none of the savings. Camofox is a hard exception: no CDP endpoint, always falls back."
distill: none
```

## 1. Claim

[@iamlukethedev](https://x.com/iamlukethedev/status/2086902520249827583) (11,817 followers;
170 likes / 23,164 views at read time), 2026-08-10, quoting the @NousResearch announcement:

> Hermes used to expose 12 separate browser tools. Browser Use mode turns those 12 tools into one.
> Instead of burning a tool call on every click, scroll, and interaction, the agent writes a script
> and executes the whole flow. **In Nous Research's tests, that cut token usage by 48 to 66% with no
> accuracy drop.** Enable it with `browser: backend: browser-use`, or run `hermes tools` and select
> Browser Use. Powered by @browser_use CLI 3.0.

The quoted first-party post is the same claim in Nous's own words. **The amplifier adds nothing** —
no independent measurement, no config detail beyond the docs. Logged because the subject is *our own
runtime*, not because the tweet has content.

## 2. What we verified — all live on this machine, nothing installed, nothing changed

### It is already on, and the tweet's "enable it with" framing is misleading

`tools/browser_use_cli.py:107-133`:

> *"Browser Use mode is the **DEFAULT**: an unset `browser.backend` ("") enables it whenever the
> browser-use CLI is runnable (installed binary or uvx). Set `browser.backend: off` for the built-in
> browser_* tools."*

`~/.t1000/config.yaml` `browser:` block, read live — **there is no `backend` key at all**:

```yaml
browser: {inactivity_timeout: 120, command_timeout: 30, record_sessions: false,
          allow_private_urls: false, engine: auto, auto_local_for_private_urls: true,
          cdp_url: '', dialog_policy: must_respond, dialog_timeout_s: 300,
          camofox: {...}, pilot_safety_mode: false, cloud_provider: browser-use}
```

`hermes config get browser.backend` → **empty**. `_find_cli()` finds no `browser-use` binary but
does find `uvx` (`/Users/ryan/.local/bin/uvx`, 0.11.9), so the mode resolves **on**.

**Proven, not inferred.** Building the real tool selection in-process printed:

```
🛠️  Final tool selection (34 tools): browser_exec, clarify, close_terminal, computer_use, ...
```

`browser_exec` present; **zero** built-in `browser_*` tools. Following the tweet's instruction and
setting `backend: browser-use` would change **nothing**.

### The local schema delta, measured off the live registry

`registry.get_schema()` for every registered `browser_*` tool, `len(json.dumps(...))`:

| tool | chars | | tool | chars |
|---|---:|---|---|---:|
| `browser_cdp` | 3,494 | | `browser_type` | 470 |
| `browser_dialog` | 1,669 | | `browser_click` | 431 |
| `browser_vision` | 1,160 | | `browser_scroll` | 375 |
| `browser_console` | 997 | | `browser_press` | 364 |
| `browser_snapshot` | 948 | | `browser_get_images` | 296 |
| `browser_navigate` | 917 | | `browser_back` | 211 |

```
12 built-in browser tools : 11,332 chars  (~2,833 tok)
browser_exec              :  3,196 chars  (~  799 tok)
delta                     : -8,136 chars  (-71.8%)
```

**Exactly 12**, matching the post's count.

⚠️ **Do not report -71.8% as confirmation of Nous's 48-66%.** They measure different things. Ours is
**static schema overhead per request**. Theirs is **end-to-end token usage on a benchmark**, which
also folds in the per-click round trips that a scripted flow eliminates — a bigger effect, but one
that depends entirely on task mix. On a desk where the browser is rarely used, the schema saving is
the only one that reliably accrues; on a browser-heavy run their number is the relevant one. Neither
figure was reproduced against the other's methodology.

### Versions — and a non-defect worth writing down so nobody re-chases it

```
uvx browser-use --version           -> 0.1.8
uvx browser-use@0.13.7 --version    -> 0.1.8      <- same, so this is the CLI's OWN version string
uv pip list                         -> browser-use 0.13.7, browser-use-sdk 3.4.2
PyPI browser-use latest             -> 0.13.7 (uploaded 2026-07-27)
docs / post                         -> "Browser Use CLI 3.0"
```

Three different numbers for the same thing. Pinning the package to latest still self-reports
`0.1.8`, which proves the CLI carries an internal version independent of the distribution — **not a
stale resolution and not a broken install.** "CLI 3.0" appears to be a generation name; do not treat
it as a version to match.

## 3. Takeaways (max 5)

1. **This is a confirm-and-document signal, not a steal.** The single most useful outcome is that
   nobody spends a session "enabling" a mode that has been on the whole time. The tweet's `browser:
   backend: browser-use` snippet is a no-op here.
2. **-71.8% schema overhead is real and permanent**, paid on every single request whether or not the
   browser is touched. That is the part of the claim that applies to this desk unconditionally.
3. **⚠️ First call pays a cold `uvx` download.** There is no installed binary; the probe in this
   session pulled **103 packages** before printing a version. A latency-sensitive first browser call
   will look broken. Pinning/pre-warming is the one genuine action item here.
4. **⚠️ `browser_exec` is coupled to `terminal` by design.** Per the docs: *"Because Browser Use mode
   executes model-written Python on your machine, the `browser_exec` tool is only offered to sessions
   that also have terminal access. Platforms configured without the terminal toolset (e.g. a
   locked-down messaging surface) keep the default browser tools instead."* This is both a security
   property and a silent asymmetry — restricted lanes get **none** of the savings and nothing warns
   you.
5. **Camofox is a hard exception** — Firefox-based, no CDP surface for the harness to attach to, so
   it always falls back to the 12 built-ins regardless of `backend`.

## 4. Steals (patterns only)

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| **S1** | **A default-on feature whose first invocation pays an unbounded cold download is a latency trap** | Install `browser-use` into a stable env (or `uv tool install browser-use`) so `_find_cli()` hits the `shutil.which("browser-use")` branch instead of `uvx`. Removes a 103-package pull from the first browser call and pins the version instead of silently floating to PyPI latest | **P1** | open |
| S2 | **Price any toolset directly off the live registry rather than guessing** — `registry.get_schema(name)` + `len(json.dumps(...))` gives exact per-tool schema cost | Reusable for the capability-projection card `t_6c3fd131`, whose whole premise is lowering the ~35.7k worker prompt floor. This is the measurement instrument for "what does each toolset actually cost" — and it is ~10 lines | **P1** | open |
| S3 | Security fact: model-written Python on the host is gated behind `terminal` co-presence | Worth an explicit note wherever restricted surfaces are configured (Pulp/VPS messaging lanes) — they keep the 12 built-ins by design. Confirm before assuming any token-saving applies there | P2 | open |

**Primary steal (one only):** **S1**

## 5. Do not

- **Do not "enable" it.** `browser.backend` unset already means on. Setting `browser-use` explicitly
  is valid but changes nothing here; the only meaningful write is `backend: "off"` to opt *out*.
- **Do not quote 48-66% as a measured T1000 number.** It is Nous's benchmark on their task mix. Our
  own measured, reproducible figure is **-71.8% schema**, a narrower claim.
- **Do not treat `--version -> 0.1.8` as a broken/stale install.** Pinning to 0.13.7 prints the same
  string. See §2.
- **Do not expect it on Camofox**, or on any surface configured without `terminal`.
- **Do not read the amplifier as independent corroboration.** It is a restatement of the first-party
  post with no added measurement.

## 6. Next action (mechanical)

- [x] add/update STEALS.md rollup
- [x] regenerate `INDEX.md`
- [ ] kanban — **no card.** Board is at 51 blocked / 17 ready and nothing here is broken. S1 is a
      one-command install that needs Ryan's word, not a card.
- [ ] AUTOMATION-ROADMAP row — n/a
- [x] patch skill — **`hermes-agent/references/configuration.md`**. Precise gap (my first read of
      this was too broad and is corrected here): `SKILL.md` has **0** occurrences of "browser", and
      4 reference files *do* mention browser generally — but **none** mention `browser_exec`,
      "Browser Use mode", `browser-use`, or `browser.backend`. So the skill that exists to configure
      Hermes had no coverage of the browser toolset's most consequential switch, whose default is
      non-obvious (unset = ON). Added a **Browser Use mode** section: the backend truth table, the
      Camofox exception, how to *verify* which mode is live (config alone cannot tell you — unset is
      the enabled state, so absence looks like nothing), the measured schema numbers, the registry
      pricing snippet, and both gotchas.

## 7. Chat blurb

The post is a restatement of Nous's own announcement with nothing added — but the subject is our
runtime, so it was worth checking, and the check inverted the framing. Browser Use mode isn't
something to enable; **`browser.backend` unset means ON, and it's already live in this session** —
the real tool selection came back with `browser_exec` and zero built-in `browser_*`. Measured our own
delta off the live registry: the 12 built-ins cost **11,332 chars (~2,833 tok)** of schema against
`browser_exec`'s **3,196 (~799)** — **-71.8%**, paid on every request whether we browse or not. Two
costs the announcement doesn't mention: there's no installed binary, so the first call shells out to
`uvx` and pulled **103 packages**; and `browser_exec` is only offered to sessions that also hold
`terminal`, since it runs model-written Python on the host — so restricted lanes keep the 12 tools
and get none of the savings.
