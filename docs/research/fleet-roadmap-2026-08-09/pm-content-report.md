# PM deep-dive: Content/Research agent stack
**Read-only audit, 2026-08-09.** All figures pulled live via `ssh k2vps`, `curl` (GET-only), `hermes kanban`, `hermes cron list`, and file reads. No inference calls made, no timers touched, nothing posted.

---

## Pulp
- **Mission**: posting/conversational operator agent with an adversarial reply-quality panel; owner-facing Telegram lane. Runs **VPS-native on k2vps** (`/opt/juice/`, systemd units `pulp-*`, `buzz-agent-pulp.service`, `juice-pulp-*`). Mac is explicitly out of the loop by design.
- **Status: LIVE**, with one approaching hard cliff and one lagging sub-system.
  - `pulp-telegram.service`: active/running. Had a burst of SSL handshake timeouts 00:33–00:42 UTC today, self-healed via a normal systemd restart at 02:35 UTC — no human action needed, but worth watching if it recurs.
  - All 6 pulp/juice timers on k2vps are `active/waiting` and have fired on schedule in the last ~1.3h (`pulp-arctic-project`, `pulp-calendar-snapshot`, `pulp-proactive`, `pulp-proactive-morning`, `juice-pulp-auth-readiness`, `juice-golden-replay`).
  - Snapshots (`calendar.json`, `arctic.json`, `investing.json`, `amber.json`) all refreshed **today at ~13:00–13:01 UTC**.
  - **Auth**: `pulp_authorize.py status` → `state: authorized`, `expires_at: 2026-08-28T16:17:09Z`. Watchdog heartbeat (`/var/lib/pulp/auth_readiness_status.json`) fired 2026-08-08 14:00 UTC, `days_left: 20.1` (so **~19 days left as of today**), status ok, not yet paged.
  - **Panel counters are stale relative to reply volume.** `/var/lib/pulp/quality_status.json`: overall reply verification ran again this morning (`last_run: 2026-08-09T03:03`, 97 replies verified lifetime), but the adversarial-panel-specific counters (`panel_replies: 19`, `panel_any_block: 12/19 = 63%`, `panel_majority_block: 1`) haven't updated since **`panel_last_run: 2026-08-05T15:45`** — 4 days behind the reply-verification loop it's supposed to be gating. Not broken, but not keeping pace either.
- **Shipped last ~2 weeks**: mesh card `t_a4982b65` "Implement LAB-0015: Pulp panel grounding+safety → gpt-oss:120b shadow" — done. `t_a87c1e70` "Arctic opens/clicks/replies beyond queue snapshot" — done. `t_91b0d2ab` "Pulp meeting briefs + remember ceremony nudge" — done. `t_cdec6dce` "Pulp: calendar domain or honest gap" — done. `t_0d23fcdc` "investing day P&L in snapshot" — done. `t_f4cd0a55` "rescue Pulp + fleet blueprint to sovereign-consulting main" — done.
- **In flight / carded**:
  - `t_f18d325e` — **HUMAN: Renew Pulp auth via TTY ceremony (before 2026-08-28)** — blocked, needs Ryan on an interactive TTY (`pulp_authorize.py` refuses non-TTY by design). Calendar hold already exists Tue 08-18 08:00–08:30 CT.
  - `t_9bfcbb2f` — "Pulp residuals: proactive cal + invest freshness + arctic gap + auth~08-28" — todo, polish-tier (proactive-morning calendar day-filter still reads as nonsense per Ryan's own 👎 feedback; investing freshness voice; open `arctic_engagement` access gap).
  - `t_72bfb2f6` — "Fold Pulp into a T1000 role; R5 expiry decides the panel" — todo, architectural — the panel's fate (arm enforce-mode vs. die) is explicitly gated on the R5 expiry evidence bar, not yet resolved.
- **Top 3 gaps/risks**:
  1. **Auth cliff 2026-08-28, ~19 days out, requires a human-typed TTY ceremony** — cannot be automated by design (anti-agent-pipe rule). Card is filed and a calendar hold exists 10 days before the cliff, so the mechanics are in place, but this is still a manual dependency that has zero slack if Ryan misses the 08-18 hold.
  2. **Panel counters 4 days stale** vs. the reply-verification loop running daily — if the panel is meant to be evidence for the R5 enforce-mode decision (`t_72bfb2f6`), a 4-day gap in that specific evidence stream weakens the case either way.
  3. **Known-nonsense proactive-morning calendar slice** is still live in production (Ryan flagged it 2026-08-06, unfixed as of `t_9bfcbb2f`) — a genuine "live" claim that fails a real quality check today.
- **Next 3 moves**:
  1. Ryan runs the TTY ceremony at the 08-18 calendar hold (or earlier) — `ssh -t k2vps /opt/juice/venv/bin/python /opt/juice/bridges/pulp_authorize.py`.
  2. Fix the proactive-morning calendar day-filter (same CT day-filter fix as `domain_calendar`) — small, scoped, already specified in `t_9bfcbb2f`.
  3. Decide/close `t_72bfb2f6` (fold into T1000 role vs. keep standalone) once R5 expiry evidence is in — the panel-counter staleness above should feed that decision.
- **Verdict: MAINTAIN.** Shipped, running, self-healing on transient faults, and generating real quality signal — but it is one missed human ceremony away from a hard auth failure, and the panel evidence stream feeding its own architectural fate is stale. Not a KILL, not ready to INVEST further until the R5 decision lands.

---

## Popper
- **Mission**: read-only Sovereign Labs research runner — cheap, non-critical experiments (few-shot rescue, embedding routers, panel calibration, tool-selection, etc.) — explicitly **not on the critical path** (`detail.critical_path` is always false by contract). Two-part infrastructure: harness `buzz-agent-t1000.service` on **k2vps** (isolated OS user `t1000lab`, `/opt/t1000-lab/labs/`), inference tier on **CadensPC** (RTX 4060, `100.85.154.33`, Tailscale) as its primary "Cadens" backend, with Spark as an occasional escalation target.
- **Status: DECAYING on the research-output axis, LIVE on the infra axis.**
  - `buzz-agent-t1000.service`: active/running for 2 days (since 2026-08-07 03:30), stable memory (60MB), but logs show a **recurring WebSocket relay disconnect/reconnect loop** (multiple drops within minutes on 2026-08-08) — self-healing, not paging, but noisy.
  - Cadens warm-status heartbeat (`/var/lib/juice/cadens_warm_status.json`, hourly): fired **2026-08-09T13:15:43Z, status ok**, `hermes3:8b resident ctx=4096` — fresh.
  - `curl http://100.85.154.33:11434/api/ps`: confirms `hermes3:8b` loaded and serving right now.
  - **No new lab experiment has run in 6 days.** Every experiment directory under `/opt/t1000-lab/labs/experiments/` (lab-0001 through lab-0021, 16 total, none numbered 0016–0019) has an mtime between 2026-07-29 and **2026-08-03** — nothing since. LAB-0024 (the next queued experiment) does not yet exist as a directory; its mesh card has **crashed twice** (see below).
  - CadensPC hardware itself was only inventoried for the first time **today** (2026-08-09) by a same-day mesh card — this box ran effectively undocumented before that.
  - The Windows `\OllamaServe` scheduled task **already exists** on CadensPC (`Task To Run: ollama.exe serve`, `Logon Mode: Interactive only`, `Schedule Type: At logon time`) — its last-run timestamp (2026-08-03 22:05:44) matches the box's `LastBootUpTime` exactly, meaning it started at that boot and has stayed up since (confirmed live: `ollama.exe` PID 11224 currently running). **This contradicts today's mesh-card audit language ("NOT done, see gate")** — the boot supervision the card is asking Ryan to gate already existed; the card's own "not done" framing is stale evidence, not current reality.
- **Shipped last ~2 weeks**: LAB findings 0001–0021 (all pre-dating this window except 0020/0021 on 08-02/08-03) — REFUTED: intent-model-bench, price-phrase-parse, restraint-bench, heartbeat-gap-model, checklist-scope-v4; CONFIRMED/promising: fewshot-rescue (LAB-0002), embedding-router (LAB-0005); PARTIAL: tool-selection (LAB-0021, gpt-oss:120b native PASS, hermes3 native PARTIAL). Mesh `t_c7f2534a` "enable Desktop Kanban plugin + prove stock /kanban" — done.
- **In flight / carded**:
  - `t_47f30baf` — "CadensPC lab lane: 8B eval/embed tier + headless autostart gate" — created **today**, Ryan gave in-session OK to install the boot Scheduled Task; per the SSH evidence above the task already exists (predates the card), so this card's remaining scope is really the eval/scoreboard-lane migration + embed-host decision, not the boot task itself.
  - `t_1edac8a4` — "Register LAB-0024 (distill 120b judge → 8b LoRA) + aarch64 adapter smoke test" — **blocked, crashed twice** (`pid 98619 not alive`, then `pid 31489 not alive`), model just repointed to `gpt-oss:120b` (spark) after `qwen2.5-coder:32b` failed 4/4 smoke configs on worker duty. Not yet re-attempted since the repoint.
- **Top 3 gaps/risks**:
  1. **6-day research dry spell** — the harness and inference tier are both healthy, but nothing has actually shipped a finding since 08-03. LAB-0024 is the queued next step and has failed twice.
  2. **CadensPC was undocumented until today** — no prior hardware inventory, no known supervision story until this session's audit; the "not done" framing on the boot task in `t_47f30baf` is itself evidence the mesh card content isn't being checked against live SSH state before being filed.
  3. **Logon-triggered (not boot-triggered) task** on a family gaming PC — if the machine loses power and nobody logs in interactively, `ollama serve` will not restart on its own; there's no headless/boot-independent supervision yet, which is exactly what `t_47f30baf` is trying to add (eval lane, embed host) without yet closing this specific gap.
- **Next 3 moves**:
  1. Correct `t_47f30baf`'s "not done" language against the SSH evidence above (task already exists), then decide only the remaining real gate: eval/scoreboard-lane migration off Ryan's Spark (fixes the KEEP_ALIVE=-1 eviction bug already diagnosed).
  2. Retry LAB-0024 smoke test on the repointed `gpt-oss:120b` worker; if it crashes a third time, that's the failure-limit — escalate rather than silently re-queue.
  3. Re-baseline "shipped last 2 weeks" expectations — either resource a new lab run this week or explicitly park the research cadence with a stated reason.
- **Verdict: MAINTAIN, borderline PARK on the research cadence specifically.** Infra is solid and cheap; actual research throughput has stalled for a week and the queued next experiment is failing. Worth one more push (retry LAB-0024) before downgrading further.

---

## Student-model program
- **Mission**: MLX-distill the Spark teacher (gpt-oss:120b + hermes3:8b) into an 8-14B student model, eventually served on a Mac mini. Runs as **4 T1000 crons on the Mac**, workdir `~/Documents/student-lab` (git-tracked; **not** `~/Documents/T1000/docs/student/` — that path does not exist, and RUNBOOK.md itself states "Canonical home is `~/Documents/student-lab/docs/` — never `~/Documents/T1000/` (contested tree)"). Raw evidence lives separately in `~/.sovereign/juice/` (episodes.jsonl etc.) — confirmed **not** a decoy, this is the live Juice store the crons read from.
- **Status: LIVE but gated — Phase 0/B automation is running daily, Phase C is blocked on data, and one of today's 4 crons just failed.**
  - `hermes cron list` shows 4 active student crons: daily watch (`dc7fe30cce4b`, 08:10 CT), weekly teacher eval (`c64e17ec4062`, Mon 07:30), corpus live capture (`12741168607c`, daily 07:50), outcome-loop review queue (`71bf4b152c63`, weekdays 17:00).
  - **Today's daily-watch run failed**: `2026-08-09T08:11:30 error: RuntimeError: [Errno 32] Broken pipe`. Corpus live capture ran fine today (07:55, ok). Weekly teacher eval and outcome-loop both look healthy on their last completed runs (08-07/08-09 respectively) but haven't fired again since (by schedule).
  - `docs/STATUS.md` (rolling, dated 2026-08-08): **trainable pointers = 2** (floor is ≥500), episodes total ~1,660 (telemetry only, not trainable), live episodes ~93, **labeled outcome_slot = 0**, golden R0-signed v1 = 30 (fixed, saturated), **research golden v2 = 100 confirmed live** (`RYAN_LABELED_UNSIGNED`, hit the ≥100 target — 1 of 3 Phase-C unlock gates met).
  - `capture-index.jsonl` (the actual pointer file) = **2 lines**, matching STATUS.md exactly and confirming the corpus-pointer blocker is real and unmoved since 08-08.
  - **A second auth cliff, distinct from Pulp's**: RUNBOOK.md G7 — "re-authorize live capture" due before **2026-08-23** (daily watch alerts under 5 days). This is a live-Gmail-capture auth for the student pipeline, separate from Pulp's Telegram/converse auth expiring 2026-08-28.
- **Shipped last ~2 weeks**: teacher eval harness verified end-to-end (tunnel + PYTHONPATH + SPARK_ENABLED fixes); MLX serving spike passed (Llama-3.1-8B-4bit, ~102 tok/s, 4.7GB peak); G1 corpus-source decision (Juice-first) + G2 re-sign closed (certified restore, 30/30 gate passed); Option-B outcome-loop built (hash+classification only, no raw body — keeps Juice's R0 raw-free scope intact); golden set grown 30→97→100 via a two-instrument split (signed v1 stays locked at 30; unsigned research-v2 grew to 100); 4 calendar holds set (weekly review, Phase C go/no-go 09-04, Phase D mini-order hold 10-15).
- **In flight / carded**:
  - `t_848b57b7` — "Mac mini student model: distill Spark teacher to MLX student" — **blocked**, explicitly Ryan-gated ("not free-fire"), re-blocked by audit on 08-07. 14 comments of real progress logged against it (G1–G7 gate tracking) even while the card itself sits blocked.
  - Related: `t_1edac8a4` (LAB-0024, Popper) is explicitly cross-referenced in the card body as "same family, different target; reconcile before running either" — a real dependency between Popper and the student program that isn't otherwise tracked anywhere else.
- **Top 3 gaps/risks**:
  1. **Corpus pointers stuck at 2 of a 500 floor** — nearly four orders of magnitude short, and the number hasn't moved in the one day since STATUS.md was last updated. This is the hardest real blocker to Phase C.
  2. **Second auth cliff (2026-08-23) that's easy to conflate with Pulp's (2026-08-28)** — both are ~2-3 weeks out and both require Ryan action; nothing currently cross-links them into a single "auth renewals due this month" view.
  3. **Today's daily-watch cron failed with a broken pipe** — likely transient (network/tunnel), but it's the cron that's supposed to be the early-warning system for the other two risks above, so a failure there is worth a same-day recheck, not a shrug.
- **Next 3 moves**:
  1. Re-run or check tomorrow's daily-watch cron output to confirm the broken-pipe error was transient and not a tunnel regression.
  2. Grow corpus pointers — either widen capture volume or accept a longer timeline to 500; right now there's no visible plan to close a 2→500 gap other than "keep capturing daily."
  3. Put the 2026-08-23 (student) and 2026-08-28 (Pulp) auth cliffs on one shared view/reminder so they don't collide or get missed independently.
- **Verdict: MAINTAIN.** Genuinely useful automation is running daily and the golden-set-100 milestone is real progress, but Phase C is data-starved (2/500) and this is the second of three systems in this report carrying a live, unmerged auth-cliff risk this month.

---

## Advisory intel pipeline
- **Mission**: Fathom call recordings (Ryan's Sovereign Advisory calls) → Spark gpt-oss:120b → 4-part private brief, posted to a Buzz channel. **Correction to the brief given for this task**: this pipeline runs on **k2vps**, not a separate "sovereign VPS / sov-consulting-core-01" — there is no SSH alias for that host in `~/.ssh/config`, and the canonical doc (`tools/juice/ADVISORY-INTEL.md` per memory) plus live systemd state both confirm k2vps. Verified directly via `ssh k2vps`, not marked unverifiable.
- **Status: LIVE**, healthy, currently idle for lack of new input (not for lack of function).
  - `juice-advisory-pull.timer`: `active (waiting)`, enabled, running continuously since 2026-08-07 03:30 UTC, next trigger ~1.5h at query time. **RECONCILED (t_31a094d0): 2h is authoritative** — `OnCalendar=*-*-* 0/2:00:00 America/Chicago` and the Description ("every 2 hours") agree, and the deploy unit (`/opt/juice/deploy/systemd/`) matches the live unit byte-for-byte. The heartbeat's `expected_interval_seconds: 10800` (3h) is **not** a competing cadence — it is a deliberate staleness-tolerance margin, per the service-unit comment ("3h > the 2h timer, so jitter can't trip a false-stale in the cockpit"), absorbing `RandomizedDelaySec=300` + systemd latency. No code change warranted; changing 10800→7200 would make stale-detection too tight and cause false cockpit alarms.
  - Heartbeat (`/var/lib/juice/fathom_pull_status.json`): `fired_at: 2026-08-09T13:02:24Z, status: ok` — fired and succeeded ~26 minutes before this check.
  - State file (`/var/lib/juice/fathom_state.json`): `last_poll: 2026-08-09T13:02:24Z`, one processed recording ID retained (dedup window rolls off older IDs by design — 48h re-list per poll).
  - Brief output directory (`/var/lib/juice/advisory-intel/`, mode 640, root-owned): **5 briefs on disk**, most recent **2026-08-05** (Brandon Rende, David P, 3× impromptu Zoom). No new brief since — because there have been no new Fathom-recorded calls in 4 days, not because the pipeline is failing. Every poll since has correctly found nothing to process and reported `ok`.
- **Shipped last ~2 weeks**: pipeline itself shipped/ratified 2026-08-01 (full-brief delivery to private Sov Adv channel, Ryan-ratified trade-off over content-free-only); root-cause fix for the "no info" brief bug (gpt-oss terseness, forcing system prompt) landed same window. No new engineering changes visible in this session — it has been running unattended and correctly since.
- **In flight / carded**: **visibility marker filed (t_31a094d0).** Advisory previously had zero kanban presence; card `t_31a094d0` is now the designated visibility marker — its comment thread records pipeline status here, so a silent-broken advisory build will now surface to mesh triage via the board instead of only a memory note. Verified live 2026-08-10: timer active/waiting, heartbeat `fired_at` ok, deploy-vs-live units identical.
- **Top 3 gaps/risks**:
  1. **Zero kanban tracking** — if this pipeline breaks, there is no card that will surface it to the mesh triage process; the only guardrail is the `OnFailure=juice-advisory-pull-failure.service` OOB page, which is real but is the sole safety net.
  2. **Encryption-at-rest on the VPS disk is a known, documented, still-open hardening gap** (per canonical doc) — raw transcripts never leave the box by design, but the box's disk itself isn't encrypted.
  3. **Timer-description vs heartbeat-interval mismatch** (2h stated vs 3h configured) is cosmetic today but is exactly the kind of doc/code drift that causes false "it's been silent too long" alarms later.
- **Next 3 moves**:
  1. File a lightweight mesh card for this pipeline so it has kanban visibility like the other three systems — currently the only content/research build with zero board presence.
  2. Reconcile the "every 2 hours" description string against the actual 10800s heartbeat interval (pick one, fix the other).
  3. No functional work needed otherwise — next real signal is whichever comes first: a new Fathom call, or the OOB failure page.
- **Verdict: MAINTAIN.** This is the cleanest system in the review — small, well-instrumented (heartbeat + OnFailure + dedup-by-ID), and correctly idle rather than broken. The only real gap is process (no kanban card), not engineering.

---

## Cross-cutting observations
- **Two live auth cliffs this month, on two different systems, not cross-linked anywhere**: Pulp converse/remember auth expires **2026-08-28** (~19 days), student-model live-capture auth expires **2026-08-23** (~14 days). Both have watchdogs that alert on their own timeline; neither view shows the other.
- **Mesh-card language is sometimes stale relative to live SSH state** — the CadensPC boot-task card (`t_47f30baf`, filed today) asserts the Scheduled Task "NOT done," but the task has existed since 2026-08-03 and matches the box's last boot exactly. Worth a habit of `schtasks`/`systemctl` verification before a card's status prose is trusted, consistent with the standing "Verify from the authority, not the proxy" lesson already in memory.
Kanban coverage is uneven across the four systems: Pulp and the student program each have 2-3 active cards; Popper has 2; Advisory now has 1 visibility-marker card (`t_31a094d0`). Advisory is functioning fine today, and the marker card closes the prior gap where it was the one system that would go silent-broken longest before anyone noticed via the board.
