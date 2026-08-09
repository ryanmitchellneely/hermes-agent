# K2-BUSINESS agent stack — PM deep-dive (read-only)

Run 2026-08-09 ~13:30 UTC against `ssh k2vps` (root, live systemd state) and the K2 repo worktree (`arctic-autonomy-dc2e56`). No writes, no Buzz posts, no Sierra calls, no restarts performed.

---

## Chamberlain

- **Mission**: decision-chip / brain-and-body agent on Buzz — Kevin's spine across email/SMS/calls, chat grounding, chip proposals, rulings rail, interjections on client signals, morning brief. Runs on `k2vps` as a family of systemd services under `k2_hub.handlers.chamberlain_*` + `k2_hub.kevin_inbox.*`, posting through `k2_hub/buzz.py: send_chip_message` (chip channel only — general Buzz traffic goes through a separate `send_message` transport).
- **Status: LIVE.** Every Chamberlain timer checked fired clean in the last ~30 min with `"ok": true`:
  - `k2-chamberlain-canary.timer` (daily) — last run 8 min ago, `active_count: 6`, `failing: []`, `ok: true`.
  - `k2-chamberlain-chip-scorer.timer` — last run 4 min ago, `chat_chips_seen: 4`, `ok: true` (but `proposals_logged: 0`, `outcomes_recorded: 0` — the scorer ran clean but had nothing to score this cycle).
  - `k2-chamberlain-spine-health.timer` — last run 6 min ago, `active_count: 6`, `unconsumed_count: 6`, `regressed: []`, `ok: true`.
  - `k2-chamberlain-interjection.timer` — last run 28 min ago, posted a real client-signal remark (Timothy Vose preapproval-letter follow-up), `outcome: success`.
  - `k2-chamberlain-label-digest.timer` (daily evening) — last run 15h ago (normal cadence), posted a 5-item call digest, `ok: true`.
  - `k2-chamberlain-daily-presence.timer`, `k2-chamberlain-attention-brief.timer` — both fired within the last hour, no errors surfaced.
  - The morning brief (`k2-kevin-inbox-brief.service`, daily 07:00 ET) — per `kevin-vault/HANDOFF-2026-08-05-chamberlain-trust-seams.md` §4, the narrator's success is now falsifiable (PR #4420, merged) and **verified clean in production on 08-06/07/08**, resolving a defect that had never once worked cleanly before that.
- **Shipped last ~2 weeks** (30+ commits touching Chamberlain/chat/spine): `#4420` narrator falsifiability fix (the brief-arriving-is-not-proof fix), `#4366` fenced 4 production seams carrying someone else's words, `#4345`/`#4344`/`#4343`/`#4337`/`#4330` — a run of "seam" hardening (stop a model forging a system turn, stop invented lead names, name unnamed numbers, fix the seam census, migrate off the blocklist), `#4295` chamberlain chat seam fenced via 3-arm dose harness, `#4202` made `lab-checked:` mechanical, `#4210`/`#4174`/`#4166`/`#4150`/`#4144`/`#4148`/`#4145`/`#4134` — the spine completion wave (calls→deals, contradiction-asks, promise tracking, brief narrator voice).
- **In flight / carded** (k2 board):
  - `t_f56dede2` — *"Chamberlain: open question — should its evals ever gate (vs report-only)?"* — **blocked 34h**, waiting on Kevin/arm-gate decision. Source: HANDOFF §7.2.
  - `t_83a5fcb5` — *"Chamberlain sphere-drift: 11 cards pending Kevin review + arm-attention-brief decision"* — **blocked 34h**. Attention brief is deliberately UNARMED (env unset + timer line commented) pending a recency-filter fix and a dry run; two known false-positive Sierra tasks still need Kevin to clear by hand.
  - `t_0774a45f` — *"Chamberlain: the listing producer — tools are wired, nothing feeds them"* — **done** on the board, but HANDOFF §7.1 still lists it as an open Kevin decision "unanswered across several sessions." Worth reconciling which is current.
  - Inbox-1017 (`docs/agent-coordination/inbox-for-kevin-claude/1017-chamberlain-training-program-proposal.md`) — **Status: open**; the linked claim `docs/agent-coordination/claims/1017-claim-chat-teaching-capture.md` is **Status: claimed**. Matches memory: training-program proposal still awaiting Kevin.
  - Inbox-1025 (*"register chamberlain harnesses and close the lint blind spot"*) — **Status: open**, also unaddressed.
- **Top 3 gaps/risks**:
  1. Two Kevin-decision cards have sat blocked 34h+ (evals-gate-or-not, sphere-drift arm decision) — not urgent-broken, but the queue is starting to age past the "quick decision" window.
  2. Chip-scorer's `proposals_logged: 0 / outcomes_recorded: 0` this cycle — worth watching whether that's normal quiet or a sign the chip pipeline upstream has gone quiet (chip-poller itself is firing fine).
  3. Board vs. HANDOFF disagreement on the "listing producer" item (done vs. still-open) — a small provenance gap, but exactly the kind of thing that causes duplicate work later.
- **Next 3 moves**: (1) Kevin clears the two 34h-blocked cards (evals-gate ruling + sphere-drift arm decision + the 2 stuck Sierra false-positive tasks); (2) reconcile listing-producer status between kanban and the HANDOFF doc; (3) inbox-1017/1025 need a Kevin pass — both are pure decision/registration asks, not build work.
- **Verdict: INVEST.** This is the most actively-shipped, most-verified-in-production build in the stack — six-plus weeks of continuous hardening, a real falsifiability fix that closed a previously-never-verified claim, and every health probe green right now.

---

## Buzz fleet (7-agent roster on k2vps)

- **Mission**: the Nostr-relay-based multi-agent chat substrate every other K2 agent build rides on (chip channel, content-lab council, presence, review digests). Roster is `kevin-claude, codex-kevin, grok-kevin, juice` plus others, read from `BUZZ_AGENT_ROSTER` env (name:pubkey pairs) — presence is checked against the **relay**, not systemd, specifically because a systemd-active agent can still be a dead socket (`k2-hub/src/k2_hub/handlers/buzz_agent_presence.py` docstring cites a real incident, "upstream block/buzz#2641," hit twice in one day).
- **Status: LIVE.**
  - `k2-buzz-agent-presence.timer` — last run 2 min ago: all 4 rostered agents (`kevin-claude`, `codex-kevin`, `grok-kevin`, `juice`) reported **online**, `missing: []`, `alert_posted: false`.
  - `k2-buzz-chat-responder.timer`, `k2-buzz-chip-poller.timer`, `k2-buzz-relay-readiness.timer` — all fired within the last ~3 minutes, no failures.
  - `k2-buzz-review-digest.timer` (open PRs + inbox needing a person) — last fired Fri 08-07 12:09 UTC (`prs: 32, inbox: 119, posted: true`); this is a **Mon–Fri 08:00 ET** timer, so the "2 days ago" gap is the expected weekend skip, not decay — next fire is Monday.
- **Shipped last ~2 weeks**: mostly indirect — Buzz is the substrate Chamberlain and content-lab ship on top of (see their commit lists above), rather than having its own standalone commit stream in this window. `#4147` gave the learning table a writer Kevin actually uses (Buzz-routed); `#3958` rebuilt the episode label rail for Buzz "where Kevin actually is" (post-Slack-decommission).
- **In flight / carded**: no dedicated Buzz-fleet cards found on the k2 board under chamberlain/buzz/cockpit/content filters beyond the Chamberlain-specific ones above — the fleet itself reads as stable infra, not actively backlogged.
- **Top 3 gaps/risks**:
  1. No standalone Buzz-fleet health surfacing besides presence + relay-readiness — those two are solid, but there's no single roster-wide "is everyone actually answering" check the way content-lab has its own liveness probe (see below). Presence proves the socket is open, not that each agent is coherent.
  2. `k2-ci-queue-monitor.service` is currently **failed** (`gh: Resource not accessible by personal access token, HTTP 403`) — not Buzz itself, but it's adjacent infra on the same box and a second failed unit alongside `juice-triage-digest` (see cockpit section) — two failed units total on k2vps right now.
  3. Roster is env-driven (`BUZZ_AGENT_ROSTER`) by design (good — avoids code changes to add a member) but that also means a silently-stale env var would produce a clean "0 missing" result even if a 5th agent should exist and never got added. Worth a periodic cross-check against `/opt/buzz/keys/MANIFEST.txt`.
- **Next 3 moves**: (1) fix or reissue the `gh` token behind `k2-ci-queue-monitor` (403, unrelated to Buzz proper but sitting on the same infra map — flagging since it's a live failed unit); (2) consider a lightweight "did each fleet member answer a real mention this week" probe, mirroring what content-lab already does for its judges; (3) no fleet-specific backlog exists on the board — if none is wanted, that's a fine steady-state, but worth a confirming pass.
- **Verdict: MAINTAIN.** Solid, unglamorous infra — no active development needed, health checks are green, but it's the dependency every other build here rides on, so it deserves proactive maintenance attention, not neglect.

---

## Fleet cockpit (`fleet_status.py`)

- **Mission**: one-pane health view across the Juice/T1000/Buzz-adjacent fleet — heartbeats, inference nodes, Pulp grounding stats, triage accuracy, live-auth countdowns. Lives at `/opt/juice/bridges/fleet_status.py` on k2vps (NOT under `/opt/k2-hub/k2-hub/scripts/` as the task brief guessed — that path doesn't exist; confirmed correct location via full-filesystem search and matches the 2026-07-30 memory pointer).
- **Status: LIVE, with two active alerts.** Ran it read-only (`python3 fleet_status.py`) — output as of 13:28 UTC:
  - ✅ inference (Spark tunnel) up, cadenspc node up, agents `juice`/`pulp`/`t1000` all up.
  - ⚠️ **`juice_triage_digest: FAIL, 1.4h ago`** — confirmed via `systemctl status`: the underlying `juice-triage-digest.service` is in `systemctl list-units --state=failed` right now. Root cause: `triage_projection.py --real --profile sovereign_advisory` **timed out after 1500 seconds** (25 min). This is a live failed unit, not a stale alert.
  - ⚠️ **`deploy_truth: MISSING`** — heartbeat file was never written. Not a regression (nothing to compare against), but an unmonitored gap.
  - ⚠️ **`sovereign_labs_runner: DEGRADED, 5.5h ago`**.
  - Everything else (Pulp grounding: 97 replies verified, 56% first-pass clean; triage accuracy 100%/27 reviewed; live-auth: juice 17.5d left, pulp 19.1d left) reads healthy.
- **Shipped last ~2 weeks**: this script lives outside the K2 repo (it's Juice/T1000-owned, under `/opt/juice/bridges/`), so it doesn't show up in `git log` on this repo — no K2-repo commits touch it directly. It is the piece of this 4-build set that sits furthest from K2-repo governance.
- **In flight / carded**: no k2-board cards found under chamberlain/buzz/cockpit/content grep — cockpit itself isn't tracked on the k2 kanban board (consistent with it being a Juice/personal-agent asset, not a K2-repo-owned one).
- **Top 3 gaps/risks**:
  1. **`juice_triage_digest` is actively FAILED right now** (timeout, not a transient blip — 25-minute hard timeout hit) — this is the one genuine "something is currently broken" finding in this whole sweep.
  2. `deploy_truth` heartbeat has **never** been written — if that's meant to track deploy state, it's silently never-instrumented, which is exactly the failure mode CLAUDE.md's observability-principle doc warns against ("every system must heartbeat + surface + auto-alert").
  3. The cockpit script isn't versioned in the K2 repo at all, so there's no PR trail, no code review, and no board tracking for it — it's effectively off the record-keeping system this repo enforces for everything else (see CLAUDE.md "Where durable facts live").
- **Next 3 moves**: (1) diagnose the `triage_projection.py` 1500s timeout (likely an LLM/tunnel slowness or a stuck query — worth a look before it recurs); (2) either wire up `deploy_truth` heartbeat-writing or remove the alert if it's not meant to fire yet; (3) consider whether `fleet_status.py` should get a K2-repo home (or at minimum a k2-board card) so it isn't invisible to the durable-facts discipline the rest of this stack follows.
- **Verdict: MAINTAIN**, with a **fix-now** flag on the triage-digest timeout — the cockpit itself is doing its job (surfacing the failure), the underlying failure needs a human look.

---

## Content-lab council (3-LLM judge)

- **Mission**: replaces the paid-vision-API hero-render judge with a Buzz-native LLM council — posts a render + rubric to `#content-lab`, `@mention`s judge agents by nostr pubkey, reads back a JSON verdict. Only `kevin-claude` reliably sees images today (`codex-acp` sandbox blocks local fetch, `grok-acp` advertises `image:false`) — so today it's effectively a one-strong-judge council with room to grow. Code: `k2-hub/src/k2_hub/content_engine/content_lab.py` (the judge) + `content_lab_health.py` (liveness monitor, ADR-061 bootstrap-guard #3).
- **Status: LIVE.**
  - `k2-content-lab-council.timer` (every 6h liveness ping) — last run 49s before check completed, `content-lab council: answered (1/2 judges answered)`, exit 0/SUCCESS.
  - `test_judge_throttles_before_every_post` (in `k2-hub/tests/test_content_lab.py`) confirms the self-throttle rule (`content_lab._throttle`, a stamp-file-based min-interval gate, fail-open by design) is asserted to run before every dispatch — matches CLAUDE.md's citation of it as the enforced-not-prose example.
  - Only 1 of 2 judges answered on the latest liveness ping — worth watching but not itself a failure (the module's own doc says today's council is deliberately single-strong-judge; a second judge going quiet on one ping isn't necessarily new).
- **Shipped last ~2 weeks**: `#4366` fenced the last 4 production seams carrying someone else's words (touches content-lab's judge-verdict path too), `#3795` liveness self-test + heartbeat + hardened verdict import (this is the health-monitor build itself), `#3749` self-throttle as a system rule + KB operational-rules page, `#3732` seated the council (collect every judge, harshest verdict governs), `#3730` moved the hero judge onto the Buzz LLM council (the founding commit, ending the paid-API starvation problem), `#3625` hero engine base (judged renders + self-improving prompt loop).
- **In flight / carded**: two content-related cards on the k2 board are **blocked/unassigned**, not active work:
  - `t_55bdbaae` — *"PARK: T1 Content Engine until ONE-bet resolves"*.
  - `t_b18cbb4f` — *"Content: Kevin — is 2715 Forest Rd the KW brokerage address or your residence?"*.
  - `t_d4ae1f59` — *"Content: inbox-2051 W3/W4 execution — Friday 2026-08-08 veto deadline"* (this deadline has now passed — worth checking if it needs re-triage).
  - Two content cards show **done**: `t_0774a45f`-adjacent listing-producer note doesn't apply here, but `t_5a1bbb59` — *"Content: wire self_consistency.py into gate.py"* — done.
- **Top 3 gaps/risks**:
  1. Only one reliable vision judge today (`kevin-claude`) — the "council" is aspirational plural; a real second vote needs either `codex-acp`'s sandbox fixed or another ACP agent with real `image:true`.
  2. `t_d4ae1f59`'s veto deadline (Fri 08-08) has passed with the card still blocked/unassigned — needs a status check, not necessarily a fire alarm.
  3. `t_55bdbaae` parks the entire T1 Content Engine pending an "ONE-bet" resolution that isn't detailed in the card body I could see — worth confirming that's still the right hold reason.
- **Next 3 moves**: (1) chase the passed veto deadline on `t_d4ae1f59`; (2) revisit whether the ONE-bet block on `t_55bdbaae` still applies; (3) if a second real vision-capable ACP judge becomes available, wire it into `K2_CONTENTLAB_JUDGES` to make the "council" genuinely plural.
- **Verdict: MAINTAIN.** Core liveness and throttle discipline are solid and well-tested; the surrounding content-engine backlog is intentionally parked pending business decisions, not decaying from neglect.

---

## Cross-cutting: decay signals found (explicit)

- **2 failed systemd units on k2vps right now**: `juice-triage-digest.service` (1500s timeout, feeds the fleet cockpit's own ALERTS section) and `k2-ci-queue-monitor.service` (`gh` 403 — CI infra, not one of the 4 target builds but flagged since it's live-red).
- **No failed units among Chamberlain, Buzz-fleet, or content-lab-council services** — every timer directly owned by these three builds fired clean in the last few minutes to few hours, well within its declared cadence.
- **Aging Kevin-decision cards**: `t_f56dede2` and `t_83a5fcb5` (both Chamberlain) blocked 34h+ waiting on a human call — not broken, but past the point where "still fresh" applies.
- **One passed deadline**: content card `t_d4ae1f59`'s Fri 08-08 veto deadline has come and gone with the card still blocked/unassigned.
- **`deploy_truth` heartbeat**: never written — a silent instrumentation gap on the cockpit's own dashboard.
- Everything else checked (buzz-review-digest's 2-day gap, label-digest's 15h gap, content-visibility-bridge's multi-day gap) matched its declared weekly/daily/business-day cadence — **not** decay, just normal quiet periods. Flagging this explicitly since a naive "hasn't fired in N hours" read would have false-positived on all three.

## Where these should feed the twice-daily Kevin digest

Could not confirm a live "twice-daily" digest distinct from the existing daily `k2-kevin-inbox-brief` (07:00 ET) and the Mon–Fri `k2-buzz-review-digest` (08:00 ET) — no K2-repo commit or systemd timer matched a "twice-daily" cadence in this sweep (checked `sovereign_digest_cron`, which turned out to be the Fathom-meeting distiller, not a fleet-state digest). If a new twice-daily digest to Kevin has landed elsewhere (Juice/T1000 side, per the memory pointer framing), the natural feed points are: Chamberlain's canary/spine-health `ok`/`failing` fields (already structured JSON), the Buzz presence watchdog's `missing: []` roster check, and the content-lab council's `answered (n/m)` liveness ratio — all three already emit machine-readable health that a digest could summarize without new instrumentation.
