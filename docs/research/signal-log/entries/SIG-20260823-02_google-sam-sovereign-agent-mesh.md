# SIG-20260823-02 — google/sam (Sovereign Agent Mesh): unofficial Google-org P2P+MCP overlay; join-bananas is the don't

```yaml
id: SIG-20260823-02
date: 2026-08-23
title: "Hasan Toor megaphone of google/sam (Sovereign Agent Mesh) — unofficial Google-org libp2p+MCP overlay. Not a weekend drop (created 2026-04-21, v0.1.0-alpha.7). Join-bananas CTA is a public-mesh tool-share; we already have Tailscale + gateway HA. Watch P2, do not install."
index_title: "google/sam Sovereign Agent Mesh (★598 Apache-2.0, v0.1.0-alpha.7) — unofficial Google-org libp2p+MCP overlay. Tweet 'quietly dropped' is 4 months old. Watch P2. Do not join bananas / curl|sh / sam-node skill install. Tailscale + gateway HA already cover Mac/VPS/Spark reachability."
index_links: [repo, docs]
source_url: "https://x.com/hasantoxr/status/2091203199877468287"
canonical_repo: "https://github.com/google/sam"
canonical_docs: "https://sam-mesh.dev/docs/"
bucket: ops
posture: watch
steal_rank: P2
confidence: high          # fxtwitter verbatim; GH API + README + LICENSE + quickstart + AGENTS.md + install.sh + sam-mesh skill + live bananas/hub GET. No install, no join.
hardware_fit: [none]      # theoretically vps/mbp/spark; we will not run it
stacks_touched: [t1000]
related_plans:
  - "t1000-gateway-ha"
  - "t_f23a816a"          # VPS-primary / existing overlay
  - "t1000-reach"
status: open
status_note: "**OPEN — watch P2, no card, no STEALS row.** Hardware pre-filter N/A (not a PCIe-offload win). Do not join bananas.sam-mesh.dev, do not `curl|sh` install.sh, do not `sam-node skill install`. Name collision with Sovereign Advisory is search noise only."
distill: none
```

## 1. Claim

[@hasantoxr](https://x.com/hasantoxr/status/2091203199877468287) (Hasan Toor; ~438k followers; "AI & Tech Educator"; **501 likes / 82 RTs / 822 bookmarks / 44 replies / 33.5k views** at read; 2026-08-22 16:37 UTC; note-tweet + vertical video). Fetched verbatim via `api.fxtwitter.com`:

> Google just quietly dropped something big for agent builders
>
> It's called SAM: Sovereign Agent Mesh
>
> A peer-to-peer network where AI agents auto-discover each other, authenticate every packet and call tools across the mesh without a central server
>
> Think of it like BitTorrent, but for your agents
>
> … If you want agents running on your laptop, your VPS, and your Mac Studio to share tools … you're duct-taping SSH tunnels …
>
> 1. Install sam-node (binary or Docker)
> 2. Point it at http://bananas.sam-mesh.dev
> 3. Connect Claude or Gemini to your local MCP endpoint
> 4. Watch your agent discover tools running on other people's nodes
>
> Still early. Not officially supported by Google.
>
> Repo: http://github.com/google/sam

He is a **megaphone**, not an author. Artifact is `google/sam`.

## 2. What we verified

| Check | Result |
|---|---|
| Post body | **verbatim** via fxtwitter + vxtwitter. Video `2091203123364990978` 720×922. Not transcribed — tweet + first-party docs are enough |
| Repo | `google/sam` — **★598 / 85 forks / 12 open issues / 6 watchers**, **Apache-2.0**, created **2026-04-21**, pushed **2026-08-23T19:59Z**, homepage `sam-mesh.dev`. Latest tag **v0.1.0-alpha.7** (2026-08-16, `prerelease:false` on the GitHub release object; name is still alpha). ~1,158 commits. Owner = Google org. **Not a same-day drop** |
| Authors | Top contributor **aojea** (Antonio Ojea) **1,100** commits — known k8s/networking Googler. Live today: PRs #294/#295 "scale_experiment", MCP advertise/probe fixes |
| Disclaimer | README last line, fetched: *"This is not an officially supported Google product."* Tweet admits this; the "quietly dropped" frame does not |
| Architecture | `sam-control-plane` (identity + policy + tokens) · `sam-router` (libp2p bootstrap / GossipSub) · `sam-node` (local P2P client + **MCP HTTP sidecar** on `:8080/mcp`). Identities = Biscuit tokens via Dex OIDC |
| Testnets | Docs: `bananas.sam-mesh.dev` = `main`; `hub.sam-mesh.dev` = latest tag. Live GET `/` `/healthz` `/mcp` on both → **HTTP 404** (via Google). Do **not** read that as "testnet dead" — control plane is not a website. Do not probe further |
| Docs vs tweet | Docs *also* say isolated-by-default / closed-by-default / BYO control plane. **And** the official Quick Start's primary path is `sam-node join https://bananas.sam-mesh.dev` plus `discover_remote_services` / `call_remote_tool` across the **public** mesh. Both are true: *your* tools stay closed until you policy them; *theirs* are callable once they advertise |
| Install | `curl -sL https://sam-mesh.dev/install.sh \| bash` writes `sam-node` / `sam-control-plane` / `sam-router` / `mcp-client` to `/usr/local/bin` (sudo if needed). Fetched: 1,883 B, `set -e` only (no `pipefail` on the advertised one-liner) |
| Agent hook | `sam-node skill install` writes `agents/skills/sam-mesh/SKILL.md` to `~/.claude/skills/` and `~/.gemini/config/skills/`. **Not Hermes.** Skill step 1 is the same `curl\|bash`. Skill teaches `discover_remote_services` + mesh inference |
| Hardware pre-filter | **N/A / pass.** Win is overlay networking, not removing a PCIe host↔device transfer. No tok/s, no batch-size trap |
| Local install / join | **Not run.** Numbers below = **claimed** |
| Duplicate URL | No prior `google/sam` / bananas / Sovereign Agent Mesh entry in this tree |

**The laptop/VPS/Studio pitch, named.** That is the T1000 topology we already run: Tailscale reachability + `t1000-gateway-ha` (one Telegram writer) + `t1000-reach` receipts. SAM would be a **second overlay** whose happy path is a public testnet that lists stranger MCP tools.

Name collision only: "Sovereign Agent Mesh" will pollute searches for Sovereign Advisory / joinsov. Not a product steal.

## 3. Takeaways (max 5)

- **Hasan ≠ the artifact.** Real `google/` repo, Apache-2.0, 4 months old, alpha.7, disclaimer in the README. Cite the repo, not the "quietly dropped" frame.
- **"No central server" is false.** Control plane + router are the hub. Public testnets exist (`bananas`/`hub`). DIY mode is "run your own hub," not BitTorrent.
- **Closed-by-default ≠ join-bananas-is-safe.** Your tools stay private until you advertise. Joining bananas still lets the agent `discover_remote_services` / `call_remote_tool` on whoever *did* advertise. That is the tweet's CTA.
- **We already solved the stated problem.** Mac / VPS / Spark share reachability over Tailscale. Gateway HA is active/passive on purpose. A public agent mesh that auto-discovers stranger tools is hostile to never-send / Ryan-only / write-gates.
- **Skill path is Claude/Gemini, not Hermes** — and it `curl\|sh`s. Hard rule: no `curl\|sh` onto `~/.t1000`.

## 4. Steals (patterns only)

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| S1 | Local MCP as the only waist + closed-by-default advertise | If we ever need cross-host MCP, put it on **Tailscale we already run** and keep advertise off unless Ryan OK. Do not adopt SAM | **P2** | log only |
| S2 | Warm-agent-pool lease (`acquire_worker` / `release_worker`) over ordinary MCP | Citation-only. Kanban already leases workers. Do not rebuild as a mesh service | P2 | log only |
| S3 | SOCKS5 waist so a `network=none` sandbox sees the mesh as the internet | Citation-only. Interesting for a future Firecracker spike; not this quarter | P2 | log only |

**Primary steal (one only):** S1 — and it is a *don't-fork-the-overlay* rule, not a build. No STEALS.md row (P2).

## 5. Do not

- **Do not join `bananas.sam-mesh.dev` or `hub.sam-mesh.dev`.** Public mesh + `discover_remote_services` = stranger tools in the agent loop.
- **Do not `curl -sL https://sam-mesh.dev/install.sh \| bash`.** Hard rule. Do not `sam-node skill install` into `~/.claude` or anywhere under `~/.t1000`.
- **Do not stand up `sam-control-plane` / Helm `sam-mesh` as a second overlay on Tailscale.** `autoApproveEnrollment` defaults **true** on the chart.
- **Do not treat this as official Google product, or as a joinsov/Sovereign feature.** Org path + disclaimer; name collision is search noise.
- **Do not card it.** Board is deep; this is a park.

## 6. Next action (mechanical)

- [x] write entry + regenerate INDEX
- [ ] no STEALS.md row (P2)
- [ ] no kanban card
- [ ] no skill / plan patch

## 7. Chat blurb

**SIG-20260823-02** · ops · watch **P2** · high
google/sam Sovereign Agent Mesh — real unofficial Google-org repo (★598 Apache-2.0, alpha.7, created Apr 21). Tweet "quietly dropped" + join-bananas-this-weekend is the don't.
**Steal:** none to build. If we ever want cross-host MCP, do it on Tailscale we already run.
⛔ No `curl\|sh`. No bananas. No second overlay.
Entry: `docs/research/signal-log/entries/SIG-20260823-02_google-sam-sovereign-agent-mesh.md`
