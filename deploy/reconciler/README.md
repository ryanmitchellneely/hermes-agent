# Desired-state reconciler (P0 Distillery pattern)

**Config = desired state.** One repairer converges reality.

| Command | Behavior |
|---------|----------|
| `juice-doctor` | Readiness + reconciler report. Drift → exit 1. Refuse → exit 2. |
| `juice-doctor --fix` | Converge repairable drift; **refuse** standing HA violations. |
| `python -m hermes_cli.reconciler [--fix] [--json]` | Engine entrypoint used by the VPS timer. |

## Files

| Path | Role |
|------|------|
| `deploy/reconciler/desired-state.yaml` | Declarative desired state (checked in) |
| `hermes_cli/reconciler.py` | Probe / evaluate / repair / heartbeat / alert |
| `deploy/reconciler/juice-doctor-reconcile.{service,timer}` | VPS self-heartbeat every 5m |
| `tests/hermes_cli/test_reconciler.py` | Proof drills |

## Standing HA invariant (encoded, not prose)

- Topology: **Mac-primary / VPS-standby**, single Telegram writer.
- Reconciler **REFUSES** (does not repair into):
  - `dual_gateway_live`
  - `mac_hand_start_while_vps_serving`

## Install (VPS)

```bash
# from Mac, after rsync of T1000 tree to /opt/t1000/src
ssh k2vps 'cp /opt/t1000/src/deploy/reconciler/juice-doctor-reconcile.service \
              /opt/t1000/src/deploy/reconciler/juice-doctor-reconcile.timer \
              /etc/systemd/system/ && \
           systemctl daemon-reload && \
           systemctl enable --now juice-doctor-reconcile.timer && \
           systemctl start juice-doctor-reconcile.service'
```

## Proof

```bash
cd ~/Documents/T1000
./venv/bin/python -m pytest tests/hermes_cli/test_reconciler.py -q
```

## Heartbeat / alert paths

- `~/.t1000/reconciler/heartbeat.json` (or `/opt/t1000/home/reconciler/` on VPS via HERMES_HOME)
- `~/.t1000/reconciler/last-alert.json` — unrepaired drift after grace, or immediate on REFUSE

Mac-resident: LaunchAgent probes for `ai.hermes.gateway` + failover heartbeat only.
VPS-first: timer unit + systemctl repairs.
