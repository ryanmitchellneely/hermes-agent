# SIG-20260805-01 — DS4 Flash token throughput claim (MIAAI Lab)

```yaml
id: SIG-20260805-01
date: 2026-08-05
title: "DS4 Flash token throughput claim (MIAAI Lab)"
source_url: "https://x.com/miaai_lab/status/2084956434169508174"
canonical_repo: ""
canonical_docs: ""
bucket: inference
posture: watch
steal_rank: P0
confidence: high
hardware_fit: [spark]
stacks_touched: [t1000]
related_plans: []
status: open
distill: none
```

## 1. Claim
MIAAI Lab reported a **DS4 Flash token throughput of ~82 tok/s** with a **1 M context on two Spark nodes**, claiming a high‑value performance improvement.

## 2. What we verified
- Our own measurement shows **~16.07 tok/s** on the same DS4 Flash setup.
- Another signal (SIG‑06) claims **28.6 tok/s**.
- The three numbers are in conflict and have not been reconciled.

## 3. Takeaways
- This discrepancy represents a significant research gap; reconciling these measurements is valuable for future optimizations.
- The claim should be tracked as an open signal pending further investigation.
