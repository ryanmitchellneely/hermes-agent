# SIG-20260811-05 — Cua/Lume process-scoped Metal capability shim

```yaml
id: SIG-20260811-05
date: 2026-08-11
title: "Cua/Lume process-scoped Metal capability shim — macOS VM llama.cpp 7-16x (VM-vs-VM, ceiling is host parity)"
source_url: "https://x.com/trycua/status/2087224365284733400"
canonical_repo: "https://github.com/trycua/cua/tree/main/libs/lume/metal-capability-shim"
canonical_docs: "https://cua.ai/blog/gpu-passthrough-macos-vms"
bucket: inference
posture: watch
steal_rank: P2
confidence: high
hardware_fit: [mbp, none]
stacks_touched: [t1000]
related_plans: [t_6e058ca2]
status: open
distill: none

index_title: "Cua/Lume Metal shim — 7-16x is VM-vs-VM; ceiling is host parity, MLX flat. No VM tooling here → watch. Vendor of our installed cua-driver 0.19.3"
index_links: [repo, docs]
status_note: "watch — zero VM tooling on this Mac; MLX lane unaffected; methodology is the steal (`t_6e058ca2`)"
```

## 1. Claim

Cua released an MIT, **process-scoped Metal capability shim** for macOS guests on Apple Silicon. A `Virtualization.framework` macOS guest reports a conservative Metal capability profile (Apple family 5, 32 KB threadgroup memory); llama.cpp reads that and picks slow kernels. The shim intercepts `supportsFamily:` and the threadgroup-memory limit for **one guest process**, answering Apple family 9 / 64 KB, which lets llama.cpp select SIMD-group matrix, SIMD-group reduction and bfloat16 paths.

Headline on one M1 Ultra (48-core GPU, macOS 26.6.1, Tahoe guest): TinyLlama **11.08× / 16.36×**, Gemma 4 12B **7.20× / 14.54×**, Muse Glimmer 30B **7.55× / 8.87×** (prompt / generation).

## 2. What we verified

**Source** — real and unusually well-evidenced. `trycua/cua` **★21,203, MIT**, pushed today. Landed as **PR #3070 `feat(lume): add macOS GPU passthrough`**, merged 2026-08-11T14:25Z, 45 files, +3,358/−0, plus docs PRs #3072 (14:47), #3073 (16:17), #3074 (17:23 — the Muse Glimmer arm, added ~16 min after the post). Checksummed raw `llama-bench` JSON under `evidence/lume-metal-capability-shim/`.

**⚠️ The headline multiples are VM-vs-VM, not VM-vs-host.** The baseline is a *broken* stock guest, and the ceiling is host parity — the post is honest about this, the tweet is not. Their own table:

| Workload (TinyLlama 1.1B Q4_K_M) | Bare-metal host | Stock guest | Unlocked guest | "speedup" | **Unlocked / host** |
|---|---:|---:|---:|---:|---:|
| pp512 | 4,871.99 | 431.86 | 4,786.70 | 11.08× | **98.25%** |
| tg128 | 286.71 | **12.63** | 206.60 | 16.36× | **72.06%** |

Gemma 4 12B QAT Q4_0: pp 517.88 host / 71.66 stock / 515.76 unlocked (**99.59%** of host); tg 52.38 / 3.41 / 49.67 (**94.82%** of host). **There is no upside beyond bare metal — the best possible outcome is "the VM stops being broken."** TinyLlama generation still leaves a real 28% VM gap after the fix.

**⚠️ MLX-LM is flat — measured by them, 1.005× / 0.993×.** MLX-LM 0.31.3 / MLX 0.32.0, `Llama-3.2-3B-Instruct-4bit`: stock guest already 1,656.55 pp / 172.09 tg. **MLX never had the problem.** Their ablation also found that advertising `MTLGPUFamilyMetal3` made MLX request a residency set the paravirtualized device doesn't provide — so the release profile deliberately leaves Metal 3 at stock.

**Their best-case VM ≈ our laptop's native number.** Muse Glimmer 30B unlocked guest = **21.08 tok/s** tg (M1 Ultra, Q4_K-M, 64 GiB guest). Our banked MBP native for the same model = **20.7 tok/s** (`t_e28b2c0e`, Ollama/GGUF-Metal, `eval_count/eval_duration`, `think:false`). Different chip and quant so not controlled — but the order of magnitude settles it: **the shim brings a VM up to roughly where our M3 Max already sits natively.** (Real MLX on the same MBP measured 12.7 tok/s — slower still.)

**Zero applicability today — measured on this Mac:** no `lume`, `lumier`, `tart`, `qemu-system-aarch64`, `prlctl`, `vmrun`, `orb`; no UTM / Parallels / VMware / OrbStack in `/Applications`; no `~/.lume`. Host is macOS 15.5 (24F74), M3 Max, 64 GB — their guest needs macOS 26.x Tahoe.

**Not in a shipped `lume` release.** Latest tag is `lume-v0.5.3`, published 12:24Z — **two hours before #3070 merged**. The shim is a build-from-source artifact (`./Scripts/build.sh` in the monorepo), not something `cua.ai/lume/install.sh` gives you.

**Same vendor already runs on this desk.** `cua-driver` **0.19.3** is installed — `/Applications/CuaDriver.app`, symlinked at `~/.local/bin/cua-driver`, installed 2026-08-10 21:10 — and that is exactly the latest release (`cua-driver-rs-v0.19.3`, 2026-08-10T13:41Z). It is the backend for our `computer_use` tool. Not running right now.

**Four cua-driver PRs merged today (22:46Z)** that will land in the *next* driver release and touch our computer-use ladder: #3013 implicit lifecycle sessions, #3015 capability manifests across permission profiles, #3041 agent-guidance alignment with lifecycle sessions, and **#3068 `fix(cua-driver): verify foreground focus before input`** — that last one is directly in the background-vs-foreground delivery ladder we operate.

## 3. Takeaways

- **7–16× is a repair, not a speedup.** Ceiling is host parity (98.25% / 99.59% pp; 72.06% / 94.82% tg). Anyone quoting "16× faster inference" from this is quoting a fixed regression.
- **Our MLX lane gets nothing from this even hypothetically** — MLX-LM was already fast in the stock VM.
- **Nothing to run here today** — no macOS VM tooling on the fleet, and the guest requirement is Tahoe.
- **The methodology is the actual steal.** Medians of N with disclosed ranges, a **ratio-to-host column**, discarded-and-rerun contaminated series, checksummed raw JSON, model+binary hashes, explicit "shared host" disclosure. That is the bench-provenance contract `t_6e058ca2` is trying to write.
- **Vendor coupling is real and previously untracked** — we run their driver at the current version and their driver changes weekly.

## 4. Steals

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| S1 | **Ratio-to-ceiling column** — every speedup row also reports % of a known-good reference, not just × over baseline | Add a required `pct_of_reference` field to the `t_6e058ca2` bench contract. Our spec-dec arms all report × over a baseline that may itself be degraded (DS4 today runs its rollback binary at ~half banked) with no ceiling anchor | **P1** | open |
| S2 | **Capability-report vs capability-reality gap** — the platform under-reports, the app believes it, and the slow path is chosen silently | Generalize as a preflight class: assert advertised capability against measured behaviour before benching. Sibling of the live `/v1/models`-is-truth rule and of the `config.context_length` claim-vs-runtime check | P2 | open |
| S3 | **Track the cua-driver changelog** — we run 0.19.3 and four behaviour-changing PRs merged today | One-line watch on the next `cua-driver-rs` release, specifically #3068 foreground-focus verification vs our background-first ladder | P2 | open |

**Primary steal (one only):** **S1**

## 5. Do not

- **Do not quote "11–16× faster LLM inference on Apple Silicon"** as a fleet-relevant number. It is VM-vs-broken-VM; the ceiling is the bare metal we already run on.
- **Do not stand up a macOS VM to chase inference throughput.** Best case is ~parity with the MBP we already have; a VM is only interesting if *isolation* is the goal.
- **Do not run `defaults write com.apple.gpusw.ParavirtualizedGraphics ForceUnrestrictedDeviceFeatureLevel -bool true`** casually — that is a **host-wide** preference change on Ryan's Mac, not a guest-scoped one, and it is a prerequisite for the shim.
- **Do not expect it to help MLX** — measured flat by the authors, and the Metal 3 variant actively broke MLX residency.
- **Do not install `lume` "to try it"** — the shim is not in the 0.5.3 release; it is a source build, and there is no VM here to attach it to.

## 6. Next action (mechanical)

- [x] add/update STEALS.md rollup
- [x] kanban comment `t_6e058ca2` (S1 — ratio-to-ceiling)
- [ ] no card (board is deep; nothing here is broken or runnable on this fleet)
- [ ] AUTOMATION-ROADMAP row — n/a

## 7. Chat blurb

Cua shipped an MIT process-scoped Metal capability shim for macOS VMs: a `Virtualization.framework` guest reports Apple family 5 / 32 KB, so llama.cpp picks slow kernels; the shim answers family 9 / 64 KB and llama.cpp switches to SIMD-matrix/bfloat16. 7–16× — but **VM-vs-VM**, and the ceiling is host parity (98–99.6% pp, 72–95% tg). **MLX-LM measured flat** (1.005×) — our student-lab lane is untouched. Their best 30B VM number (21.08 tok/s) ≈ our banked MBP native (20.7). No VM tooling exists on this Mac and the guest needs Tahoe, so: **watch**. The real steal is their **ratio-to-host column** → `t_6e058ca2`. Side note: their `cua-driver` **0.19.3** is installed here and is our `computer_use` backend — four behaviour-changing driver PRs merged today, including foreground-focus verification before input.
