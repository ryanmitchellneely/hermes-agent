# K2SharedKanban

This directory is **K2SharedKanban** — the shared kanban for every project and every
agent (Ryan's, Kevin's, DevBot, the mesh workers). Renamed 2026-09-08 by Ryan's ruling;
it used to be called "the T1000 kanban mesh", which confused people.

- **What it is:** the 17 boards under `boards/` (slugs unchanged: `k2`, `devbot`, `mesh`,
  `models`, `infra`, `harness`, `arctic`, …). Board slugs and card ids did not change.
- **What T1000 is:** only the engine that serves this directory — the Hermes fork running
  as unix user `t1000` under the `t1000-gateway` / `t1000-serve` units. Its name is not the
  board system's name.
- **How to drive it:** `k2kanban <verb> …` (`/usr/local/bin/k2kanban` here, `~/.local/bin/k2kanban`
  on Ryan's Mac). It runs `hermes kanban` as `t1000` with `HERMES_HOME=/opt/t1000/home`.
  Never run `hermes` as root in this home: root-owned files here break every t1000 process
  with EACCES (179 files chowned back 2026-08-21, 14 more 2026-09-08).
- **Canonical doc:** kevin-real-estate-tools `docs/knowledge-base/k2-shared-kanban.md`.
