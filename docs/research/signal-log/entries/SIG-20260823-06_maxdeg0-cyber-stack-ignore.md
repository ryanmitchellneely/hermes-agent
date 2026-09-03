# SIG-20260823-06 — MAXdeg0 AI cyber stack (recon / Nuclei / Garak): do not install

```yaml
id: SIG-20260823-06
date: 2026-08-23
title: "MAXdeg0 'AI cybersecurity stack' — Metatron recon / Nuclei templates / Garak jailbreaks. Do not install. Ignore."
index_title: "MAXdeg0 cyber stack listicle — Metatron recon + Nuclei template-run + NVIDIA Garak jailbreaks. Ignore. Do not install or point at a target."
source_url: "https://x.com/MAXdeg0/status/2091411890412954061"
canonical_repo: ""
canonical_docs: ""
bucket: noise
posture: ignore
steal_rank: —
confidence: high          # fxtwitter verbatim; no repo bodies ingested
hardware_fit: [none]
stacks_touched: [none]
related_plans:
  - "SIG-20260823-05"     # same-day RE/pentest pack; same disposition
status: wont
status_note: "**WONT — ignore.** Hardware pre-filter N/A. Offensive-cyber (recon + vuln-template execution + jailbreak runner). Logged so a re-paste does not fork. Do not install. Do not point any of these at a target."
distill: none
```

## 1. Claim

[@MAXdeg0](https://x.com/MAXdeg0/status/2091411890412954061) (MAX; ~7.5k followers; **906 likes / 128 RTs / 1,376 bookmarks / 39.3k views** at read; 2026-08-23 06:27 UTC; note-tweet + video). Fetched verbatim via `api.fxtwitter.com`:

> THREE OPEN SOURCE AI CYBERSECURITY STACK
>
> METATRON: point it at a target, it recon's, analyzes, and reports on its own — fully OFFLINE
>
> NUCLEI: describe a vulnerability in plain English, it writes and runs the actual detection template
>
> GARAK BY (NVIDIA): throws thousands of known prompt injection and jailbreak attempts at an LLM until one breaks through.

## 2. What we verified

| Check | Result |
|---|---|
| Post | verbatim via fxtwitter + vxtwitter. Video not transcribed |
| Repos | **Not fetched.** Thread promised “links below”; we did not follow them |
| Hardware pre-filter | N/A |
| Duplicate URL | none |

High-level names only: Nuclei is a known ProjectDiscovery scanner; Garak is NVIDIA’s published LLM probe harness. No further inventory.

## 3. Takeaways (max 5)

- Influencer “dangerous stack” bait. Not a T1000 artifact.
- The CTA is point-at-a-target recon + auto-run detection templates + automated jailbreaks. Park.
- No steal. We already refuse offensive-cyber install from signals.

## 4. Steals (patterns only)

| ID | Pattern | T1000-shaped action | Rank | Status |
|----|---------|---------------------|------|--------|
| — | none | Logged so a re-paste updates this entry | — | wont |

**Primary steal (one only):** none.

## 5. Do not

- Do not install Metatron, Nuclei, or Garak from this tweet.
- Do not point any scanner at a host, app, or model.
- Do not write or run vulnerability templates, recon playbooks, or jailbreak suites.
- Do not fork a new SIG on re-paste — update this one.

## 6. Next action (mechanical)

- [x] write entry + regenerate INDEX
- [ ] no STEALS.md row
- [ ] no card

## 7. Chat blurb

**SIG-20260823-06** · noise · ignore
Metatron / Nuclei / Garak promo. Do not install. Do not point at a target.
Entry: `docs/research/signal-log/entries/SIG-20260823-06_maxdeg0-cyber-stack-ignore.md`
