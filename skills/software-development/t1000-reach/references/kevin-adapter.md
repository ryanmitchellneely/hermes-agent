# Kevin / Chamberlain adapter (A3)

## Rail

| Piece | Truth |
|-------|--------|
| Transport | k2vps Telegram Bot API |
| Bot | `@K2SellsBot` (display **Chamberlain**) |
| Chat | `TELEGRAM_KEVIN_CHAT_ID` → **private** user (getChat: first_name Kevin, last N*) |
| Env | `/etc/k2-hub.env` — never print token/chat values |
| Framing | `🏛️ Chamberlain · from Ryan / T1000\n{subject}\n\n{body}` |
| Code | `scripts/peers/kevin.sh` · remote runner scp’d per fire |
| Inbox | `~/Documents/kevin-real-estate-tools/docs/agent-coordination/inbox-for-kevin-claude/` |

## Commands

```bash
R=~/.t1000/bin/reach
"$R" kevin status
"$R" kevin notify -- --dry-run --subject "S" --body "B"
REACH_KEVIN_FIRE=1 "$R" kevin notify -- --fire --subject "S" --body "B"
REACH_KEVIN_FIRE=1 "$R" kevin notify -- --fire --subject "S" --body "B" --file /path.pdf
"$R" kevin inbox -- --subject "S" --body "B"   # no Telegram
```

## Dual gate (live send)

1. `--fire` on CLI  
2. `REACH_KEVIN_FIRE=1` (or `true`) in env  

Either alone → refuse (`fire_gate`). Also refuse if HA shows dual T1000 gateways or VPS env not ready.

## Human attention (load-bearing)

**Ryan 2026-08-04:** Kevin texts Ryan; may not use Telegram day-to-day.

| Evidence | Means |
|----------|--------|
| `ok:true` + `message_id` | Telegram accepted delivery to that private chat |
| getChat first_name Kevin | Account labeling matches expected principal |
| Ryan’s lived habit | Human may never open TG |

**Reporting language:**

- ✅ “Sent to Kevin’s Chamberlain Telegram account (`message_id=24872`); inbox `171-….md` written.”
- ❌ “Kevin got the text” / “Kevin was notified” (implies human read)

For **human-critical** pings: after TG+inbox, offer Ryan to relay on his normal SMS/iMessage thread (imsg may be FDA-blocked on agent — don’t thrash).

## Proven message_ids

| When | id | What |
|------|-----|------|
| 2026-08-03 | 24326 | Competitive intel PDF (Adamation) |
| 2026-08-04 | 24872 | Mesh A3 smoke text |

## Related

- Desk long-form: `sovereign-desk` → `references/kevin-chamberlain-delivery.md`
- Mesh plan open Q: Kevin primary human surface Buzz vs TG vs SMS
