# Calendar + Pulp — VPS-native, **NO Mac runtime**

## Invariant
**Mac must never be involved** in Pulp TG, calendar read/write, proactive, bridges, or snapshots.
Deploy/push from Mac is OK; runtime = **k2vps only**.

## Write lane (no invitees)
| | |
|---|---|
| Account | `personal` primary |
| Invitees | never |
| Default | free (`transparent`), prefix `[Work]` |
| Host | k2vps `/opt/juice/bridges/calendar_write_no_guests.py` |
| Tokens | `/opt/t1000/home/google_accounts/{personal,joinsov}.json` |
| Ceremony | `cal add: Title \| start \| end` on Pulp TG |
| Via | `vps-local` (synchronous; no Mac poll) |

## Snapshot
- `pulp-calendar-snapshot.timer` hourly on k2vps
- Output: `/var/lib/pulp/snapshots/calendar.json` `source=vps-native`

## Mac LaunchAgents
Disabled (renamed `*.disabled-mac`):
- `com.ryan.pulp-t1000-bridge`
- `com.ryan.pulp-calendar-snapshot`

## ask t1000
Previous Mac worker path is **disabled**. Do not re-enable Mac LA. Future: VPS-local tools only if needed.
