"""Reviewed constant list of pooled sandbox hosts (Phase 2 R5).

docs/build-plans/2026-09-03-sandbox-mesh-phase2.md, "Dispatcher side": host
selection is a REVIEWED CONSTANT LIST, never runtime discovery -- "the
wrapper's host choice for a given run remains 'first ELIGIBLE host with free
capacity and matching labels' over the reviewed list, never a live probe of
the fleet to decide membership". This module is that list's loader plus the
pure selector that walks it. Neither function performs a network call, a DNS
lookup, or a subprocess/tailscale probe of any kind -- membership and
eligibility are exactly what the reviewed file says, nothing discovered at
runtime.

Ryan's rulings this module encodes (same order, "Digest pin, per
architecture" + the candidate-host table + Residuals G11): the pool is
amd64-only for now -- ``kevin-spark`` and ``spark-6c82`` are both aarch64
and are excluded by the loader's own arch filter, independent of their own
``enabled`` bit. ``kevin-spark`` is additionally the model host DS4 already
serves from and stays ``enabled: false`` in the reviewed file regardless,
pending the co-residency ruling (Residuals G11) -- this module does not
special-case it by name; the file's own bits are the only gate.

k2vps (the local host) is never an entry in this file -- it is the
dispatcher's existing local-execution fallback when no pool host has
capacity, exactly as today; see :func:`select_pool_host`'s ``None`` return.

Round 3 (2026-09-05, captain's decision from the executed K2-transport-side
critic that fed one sample ``sandbox_hosts.yaml`` to both this loader and
the K2 wrapper's own): the two repos must agree on the file, and the K2
wrapper's loader never read a per-row capacity figure -- so requiring one
here silently DROPPED an otherwise-valid host on this side only (a bare
``int(raw.get("max_in_progress"))`` raised on the missing key and the
``except`` swallowed it as "drop this entry"). A ``sandbox_hosts.yaml`` row
is host identity and transport ONLY, nothing more: ``name, address,
account, identity_file, host_key, enabled, arch``. ``host_key`` and
``identity_file`` are opaque strings on this side -- stored unchanged,
never parsed, never validated, never logged (see
``gateway.kanban_watchers._pool_hosts_log_payload``). The per-host cap now
lives EXCLUSIVELY in config.yaml's
``kanban.max_in_progress_per_profile.<profile>.per_host`` mapping, resolved
via ``kanban_db._resolve_profile_host_cap`` (round 2's unified, fail-closed
resolution rule -- reused verbatim here, not reimplemented):
:func:`select_pool_host`'s ``host_cap`` argument is that resolved figure,
and a host absent from it (or resolving to ``None`` -- "no per_host entry
and no default" for that profile) is REFUSED outright, never treated as
uncapped, since there is no row-level figure left to fall back on.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

try:
    import yaml
except ImportError:  # pragma: no cover - PyYAML is a hard dependency elsewhere
    yaml = None  # type: ignore[assignment]

SANDBOX_HOSTS_FILENAME = "sandbox_hosts.yaml"

# The one new env-var handshake to the spawned worker (phase2 order, "Host
# selection"). The K2 wrapper's transport seat is the only reader.
DSH_POOL_HOST_ENV_VAR = "DSH_POOL_HOST"

# Ryan's ruling (phase2 order, "Digest pin, per architecture"): the pool is
# amd64-only for now.
_POOL_ARCH = "amd64"


@dataclass(frozen=True)
class SandboxHost:
    """One reviewed pool-host entry -- host identity and transport ONLY
    (round 3, 2026-09-05: the per-host capacity figure moved to config.yaml
    and is no longer part of this row at all -- see module docstring).

    Every ``SandboxHost`` :func:`load_sandbox_hosts` hands back has already
    been filtered to ``enabled: true`` and ``arch: amd64`` -- by
    construction, every instance of this class is eligible.

    ``identity_file`` and ``host_key`` are opaque strings: passed through
    unchanged from the reviewed file, never validated (no path existence
    check, no key-format check) and never logged -- see
    ``gateway.kanban_watchers._pool_hosts_log_payload``.
    """

    name: str
    address: str
    account: str
    identity_file: str
    host_key: str
    arch: str


def sandbox_hosts_path(hermes_home) -> Path:
    """Join ``<hermes_home>/sandbox_hosts.yaml`` -- the one reviewed file
    named by the mesh order (docs/build-plans/2026-09-02-agent-sandbox-mesh-
    work-order.md:90), never a second config surface."""
    return Path(hermes_home) / SANDBOX_HOSTS_FILENAME


def load_sandbox_hosts(path) -> List[SandboxHost]:
    """Load, validate, and filter the reviewed sandbox-hosts list.

    Fail closed, always -- this function is the only gate a pool host has
    to pass to become dispatchable, so every ambiguous case returns the
    empty list rather than guessing:

    - a missing file, an unreadable file, invalid YAML, or a top-level
      shape that isn't ``{"hosts": [...]}`` -> ``[]`` (no hosts at all);
    - two entries sharing the same ``name`` -> ``[]`` for the WHOLE file
      (a reviewed list must be unambiguous; silently keeping "the first
      one" would hide a reviewer's mistake instead of surfacing it);
    - one entry missing a usable ``name`` -> that ONE entry is dropped,
      not the file (a typo on one host must not take the rest of the pool
      down).

    Only entries with ``enabled: true`` (the literal YAML boolean -- a
    string or any other truthy value does NOT count, fail closed) AND
    ``arch: amd64`` are returned (Ryan's ruling -- see module docstring); a
    host present in the file but disabled, or present with any other
    ``arch``, is still parsed (so a repeated name still trips the
    duplicate-name refusal) but never returned.

    Round 3 (2026-09-05): a row carries host identity and transport ONLY --
    ``name, address, account, identity_file, host_key, enabled, arch``.
    There is no per-row capacity figure any more (see module docstring);
    the K2 wrapper's own loader never read one, so requiring one here let a
    host that is valid on that side silently vanish on this side -- a row
    without ``max_in_progress`` (or with any other key this loader doesn't
    recognize) now loads exactly like any other row. This loader never
    validates or logs ``identity_file``/``host_key``; it only stores them.

    No network call, no DNS lookup, no subprocess, no tailscale probe --
    this function only ever reads the one local file at ``path``.
    """
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError:
        return []
    if yaml is None:  # pragma: no cover - PyYAML always present in this repo
        return []
    try:
        doc = yaml.safe_load(text)
    except yaml.YAMLError:
        return []
    if not isinstance(doc, dict):
        return []
    raw_hosts = doc.get("hosts")
    if not isinstance(raw_hosts, list):
        return []

    seen_names: set = set()
    parsed: List[SandboxHost] = []
    for raw in raw_hosts:
        if not isinstance(raw, dict):
            continue
        name = raw.get("name")
        if not isinstance(name, str) or not name.strip():
            # No usable identity to dedup or select by -- drop this one
            # entry, not the whole file.
            continue
        name = name.strip()
        if name in seen_names:
            # Duplicate name -- refuse the WHOLE file (structural review
            # error), regardless of what either entry's other fields say.
            return []
        seen_names.add(name)

        enabled = raw.get("enabled") is True  # strict: only the literal `true`
        arch = raw.get("arch") if isinstance(raw.get("arch"), str) else ""
        if not (enabled and arch == _POOL_ARCH):
            continue

        address = raw.get("address") if isinstance(raw.get("address"), str) else ""
        account = raw.get("account") if isinstance(raw.get("account"), str) else ""
        identity_file = (
            raw.get("identity_file") if isinstance(raw.get("identity_file"), str) else ""
        )
        host_key = raw.get("host_key") if isinstance(raw.get("host_key"), str) else ""
        parsed.append(
            SandboxHost(
                name=name,
                address=address,
                account=account,
                identity_file=identity_file,
                host_key=host_key,
                arch=arch,
            )
        )
    return parsed


def select_pool_host(
    hosts: List[SandboxHost],
    running_counts: Optional[Dict[str, int]] = None,
    host_cap: Optional[Dict[str, Optional[int]]] = None,
) -> Optional[str]:
    """Pick the pool host for one dispatch, or ``None`` for "use k2vps
    locally, exactly as today" -- the existing local-execution fallback.
    This function never returns a sentinel for k2vps; it simply selects
    nothing when no pool host has room.

    ``hosts`` -- the reviewed, already-filtered list from
    :func:`load_sandbox_hosts`, walked in THAT list's own order. This is
    the entire selection algorithm: the first entry with free capacity
    wins. Never load-based, never a live probe -- a host's position in the
    reviewed file IS the priority (phase2 order, "Host selection is a
    reviewed constant list").

    ``running_counts`` -- ``{host_name: current_in_progress_count}`` for
    the profile being dispatched, already known to the caller. This
    function never queries a database or a daemon to produce it -- no
    counting, no discovery, happens in here.

    ``host_cap`` -- ``{host_name: cap_or_None}``, the ONLY source of
    capacity as of round 3 (2026-09-05): the reviewed row itself no longer
    carries a ``max_in_progress`` of its own (see module docstring), so
    there is nothing left here for this to narrow -- it simply IS the
    effective cap. Expected to be built by calling
    ``kanban_db._resolve_profile_host_cap(cap, profile, host.name)`` per
    host for the profile being dispatched (round 2's unified resolution
    rule, reused as-is, not reimplemented here). A host absent from
    ``host_cap``, or present with a value of ``None`` -- "no per_host entry
    and no default" for that profile, in
    ``_resolve_profile_host_cap``'s own words -- is REFUSED outright, never
    treated as uncapped: fail closed, since there is no per-row figure left
    to fall back on. Omitting ``host_cap`` entirely refuses every host,
    exactly like passing ``{}``.

    A host not present in ``hosts`` is never selected -- by construction,
    since this function only ever iterates ``hosts`` itself.
    """
    running_counts = running_counts or {}
    host_cap = host_cap or {}
    for host in hosts:
        effective = host_cap.get(host.name)
        if effective is None:
            # No per_host entry and no default for this profile -- fail
            # closed, never fall back to "unconstrained".
            continue
        if running_counts.get(host.name, 0) >= effective:
            continue
        return host.name
    return None


def pool_host_env(selected_host: Optional[str]) -> Dict[str, str]:
    """The env-var overlay for the spawned worker's subprocess environment.

    ``selected_host`` is :func:`select_pool_host`'s return value. Returns
    ``{"DSH_POOL_HOST": <name>}`` when a pool host was selected, or ``{}``
    when ``selected_host`` is falsy -- the env var stays UNSET, exactly
    today's behaviour; the K2 wrapper's transport seat treats unset as
    local (phase2 order's own env-var contract: "unset means local"). This
    function only ever computes the overlay -- it never mutates this
    process's own environment.
    """
    if not selected_host:
        return {}
    return {DSH_POOL_HOST_ENV_VAR: selected_host}
