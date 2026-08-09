# W4 DECISION PACKET — stay B vs pivot D (Kevin-box end-state)

Written 2026-08-09 by ryan-claude (replaces t_618701e2's claimed-but-never-written file —
see that card's falsification comment). Numbers only; no pivot occurs from this document.
Governance §7: Kevin-box residency change requires BOTH Ryan and Kevin acks on t_a97cf1e6.

## The question
Kevin Spark's end-state: **B** — keep the specialization split (DS4 Flash code lane on Kevin
box, 120b general lane on Ryan box) through a 2-week soak — or **D** — Kevin box mirrors the
Ryan stack (gpt-oss:120b, identical digest already on both disks) + qwen3-coder:30b as the
on-demand code lane, giving symmetry and real failover.

## The numbers (all verified, sources on the cards)

| Evidence | Result | Source |
|---|---|---|
| D-test: qwen3-coder:30b, 20 FILE-fence goldens (Flash's own protocol) | **PASS 20/20, p50 wall 7.31s vs Flash 24.54s (3.4x faster)**, free floor ≥19GB, clean TTL unload | t_0da022de |
| DSpark spec-dec on upstream CUDA (B's unique lever) | **NEGATIVE-FINAL: Metal-only decode** (159 metal-tagged dspark lines, 0 cuda @ b0309611); A/B 16.23 vs 16.39 tok/s = 1.01x noise; rolled back | t_716141c4 |
| Width ladders | Prior ladder ≈ nothing (agg 14-15 → ~16 tok/s); K3 re-run Kevin-gated + moot under D; R12 re-scoped to keep_alive policy (annex pending) | t_fd210e86 / t_89c72b32 / t_9c7208c2 |
| ctx raise | 65536 live + verified both ends; KV +0.67 GiB total (MLA); 58k-tok prompt → 200, 147k → correct 400 | t_01ac807e |
| Supervision | ds4.service systemd, Restart=on-failure, enabled, NRestarts=0; soak on final flags since 08-09 07:38 EDT | t_253717ee / t_0908420e |
| Spec-dec future | Entrpi fork claims 28.6 tok/s on identical GB10+0731 weights → fork is the ONLY spec-dec route on this hardware | t_43e997d2 (Kevin-gated) |

## What D gains / forfeits
**Gains:** hardware symmetry, real failover (identical 120b digests), one engine to operate,
~67 GB freed on Kevin box, and a code lane measured 3.4x faster than Flash on Flash's own goldens.
**Forfeits:** DSpark spec-dec (now proven unavailable on upstream CUDA — the forfeit is empty)
and the nominal DS4 long-ctx lane (both boxes now serve ≥65k anyway).

## Standing defaults (re-affirmed, not up for silent change)
98 GB hybrid quant: **NO**. Engine side-door: **NO** this cycle (llama-server, never vLLM, if ever).

## Recommendation
**Open D for dual acknowledgment.** Every axis D needed to win on, it won with margin, and
B's one unique lever is dead on this hardware. Fable's original tilt ("D is likely the better
end-state if numbers hold") is confirmed by measurement.

## How to ack (t_a97cf1e6)
- Ryan: **ACK pivot-D lodged 2026-08-09 08:06, contingent on Kevin's ack.**
- Kevin: comment `ACK pivot-D` or `ACK stay-B` (+ any conditions) on t_a97cf1e6.
- If both ACK D: implementation happens via NEW worker cards (residency migration wave,
  announced windows, rollback plans) — never on the ack card itself. Early-revisit triggers
  and the 2-week soak clock survive the pivot.
