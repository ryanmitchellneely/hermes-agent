# Reach mesh — team controls (2026-08-03)

Merged from parallel security / ops / DX review before A0/A1 build.

## Security MUST

1. Receipt on every `reach` call — no silent success  
2. Per-peer adapters + credentials only  
3. Fail-closed Kevin notify if dual Telegram writers possible  
4. Pulp: auth-gated, no send/Sierra/mail — no `pulp_core` import into T1000 gateway  
5. Spark is compute-only (status/tunnel/models)

## Security MUST-NOT

6. No Kevin-tenant MCP / `kermes:write` for T1000  
7. No identity fusion (T1000 ↔ Juice ↔ Pulp ↔ Popper ↔ Carlton/Chamberlain)  
8. No second Telegram bot/gateway for mesh tests  
9. No A2A write verbs without Kevin-ratified peer map  
10. No unceremonied Popper lab writes / auto-enqueue  

## Ops

11. Split Juice **auth** vs **model/tunnel** facets in status  
12. HA strip orthogonal: Mac gateway + HB age + VPS inactive  
13. Gateway-up ≠ Spark-up  
14. Missing peer in `all status` = error row, not omit  
15. VPS promote ≠ full mesh green (Mac-only deps still fail)

## DX

16. Skill home: `~/.t1000/skills/software-development/t1000-reach/`  
17. CLI always JSON stdout; exit 0 iff `ok=true`  
18. Unknown peer/verb → structured error, exit 2  
19. Wrap existing tunnel/juice scripts — don’t fork logic  
20. Natural language maps to the same CLI  

## Build order (do not skip)

A0 skeleton → A1 spark → A2 juice → A3 kevin → A4 pulp → A5 popper → B `all status`

Kevin human notify (Chamberlain Telegram) was proven 2026-08-03 (PDF msg path) — still implement behind explicit Ryan send OK + single-writer HA check.
