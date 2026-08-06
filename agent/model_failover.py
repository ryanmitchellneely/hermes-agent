"""Model failover policy: ordered chain, two-strike demote, cooldown, sticky revert.

P2 Distillery/openclaw pattern. Complements existing try_activate_fallback /
restore_primary_runtime with explicit:

  - two strikes before demoting a provider into cooldown
  - sticky failover with probe-based auto-revert to preferred
  - route decision log
  - sustained-failover alert when running on fallback > N hours

This module is the policy brain; wire points call record_failure / select /
maybe_revert rather than re-implementing counters in the hot path.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence


class FailClass(str, Enum):
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"  # 429
    BILLING = "billing"  # 402
    AUTH = "auth"
    SERVER = "server"  # 5xx
    OTHER = "other"


# Failures that count toward demotion strikes
_STRIKE_CLASSES = {
    FailClass.TIMEOUT,
    FailClass.RATE_LIMIT,
    FailClass.BILLING,
    FailClass.SERVER,
}


@dataclass
class ProviderState:
    provider: str
    model: str = ""
    strikes: int = 0
    cooldown_until: float = 0.0  # monotonic
    demoted: bool = False
    last_error: str = ""
    last_fail_class: str = ""


@dataclass
class RouteDecision:
    ts: float
    action: str  # select | demote | cooldown_skip | revert | alert_sustained
    provider: str
    model: str = ""
    reason: str = ""
    detail: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FailoverConfig:
    strikes_to_demote: int = 2
    cooldown_sec: float = 60.0
    # How long on fallback before alerting (seconds). Default 2 hours.
    sustained_failover_alert_sec: float = 2 * 3600
    preferred_provider: str = ""
    preferred_model: str = ""
    chain: List[Dict[str, str]] = field(default_factory=list)  # [{provider, model}]


ProbeFn = Callable[[str, str], bool]  # (provider, model) -> healthy


class ModelFailoverPolicy:
    """Per-route failover state machine."""

    def __init__(
        self,
        config: FailoverConfig,
        *,
        clock: Optional[Callable[[], float]] = None,
        log_path: Optional[Path] = None,
        alert_path: Optional[Path] = None,
    ) -> None:
        self.config = config
        self._clock = clock or time.monotonic
        self.log_path = log_path
        self.alert_path = alert_path
        self._states: Dict[str, ProviderState] = {}
        self._active_provider = config.preferred_provider
        self._active_model = config.preferred_model
        self._on_fallback_since: Optional[float] = None
        self.decisions: List[RouteDecision] = []

        # Seed chain providers
        for entry in config.chain:
            p = (entry.get("provider") or "").strip().lower()
            m = (entry.get("model") or "").strip()
            if p and p not in self._states:
                self._states[p] = ProviderState(provider=p, model=m)
        pref = (config.preferred_provider or "").strip().lower()
        if pref and pref not in self._states:
            self._states[pref] = ProviderState(
                provider=pref, model=config.preferred_model or ""
            )

    def _state(self, provider: str) -> ProviderState:
        key = provider.strip().lower()
        if key not in self._states:
            self._states[key] = ProviderState(provider=key)
        return self._states[key]

    def _log(self, action: str, provider: str, reason: str = "", **detail: Any) -> None:
        st = self._state(provider)
        dec = RouteDecision(
            ts=time.time(),
            action=action,
            provider=provider,
            model=st.model or self._active_model,
            reason=reason,
            detail=detail,
        )
        self.decisions.append(dec)
        if self.log_path is not None:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.log_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(dec.to_dict()) + "\n")

    def record_failure(
        self,
        provider: str,
        fail_class: FailClass | str,
        *,
        error: str = "",
        model: str = "",
    ) -> bool:
        """Record a failure. Returns True if the provider was just demoted."""
        if isinstance(fail_class, str):
            try:
                fail_class = FailClass(fail_class)
            except ValueError:
                fail_class = FailClass.OTHER

        st = self._state(provider)
        if model:
            st.model = model
        st.last_error = error
        st.last_fail_class = fail_class.value

        if fail_class not in _STRIKE_CLASSES:
            self._log("select", provider, reason=f"non_strike:{fail_class.value}")
            return False

        st.strikes += 1
        self._log(
            "strike",
            provider,
            reason=fail_class.value,
            strikes=st.strikes,
            need=self.config.strikes_to_demote,
        )
        if st.strikes >= self.config.strikes_to_demote:
            st.demoted = True
            st.cooldown_until = self._clock() + self.config.cooldown_sec
            st.strikes = 0
            self._log(
                "demote",
                provider,
                reason=fail_class.value,
                cooldown_sec=self.config.cooldown_sec,
            )
            return True
        return False

    def record_success(self, provider: str, *, model: str = "") -> None:
        """Clear strikes after a successful call (two-strike window resets)."""
        st = self._state(provider)
        if model:
            st.model = model
        if st.strikes or st.demoted:
            self._log("success", provider, reason="clear_strikes", had_strikes=st.strikes)
        st.strikes = 0
        # Do not clear demoted/cooldown here — that is maybe_revert's job.

    def mark_on_fallback(self, provider: str, *, model: str = "") -> None:
        """Start/continue the sustained-failover clock when leaving preferred."""
        pref = (self.config.preferred_provider or "").strip().lower()
        p = (provider or "").strip().lower()
        st = self._state(p)
        if model:
            st.model = model
        self._active_provider = p
        self._active_model = model or st.model
        if pref and p and p != pref:
            if self._on_fallback_since is None:
                self._on_fallback_since = self._clock()
            self._log("select", p, reason="fallback_active", model=self._active_model)
        elif p == pref:
            self._on_fallback_since = None
            self._log("select", p, reason="preferred_active", model=self._active_model)

    def in_cooldown(self, provider: str) -> bool:
        st = self._state(provider)
        now = self._clock()
        if st.demoted and now < st.cooldown_until:
            return True
        if st.demoted and now >= st.cooldown_until:
            # Cooldown expired — eligible for probe/revert; stay demoted until probe
            return False
        return False

    def select(self) -> Optional[Dict[str, str]]:
        """Pick the best available provider from preferred + chain.

        Skips providers in cooldown (no re-burning timeouts).
        """
        ordered: List[tuple[str, str]] = []
        pref = (self.config.preferred_provider or "").strip().lower()
        if pref:
            ordered.append((pref, self.config.preferred_model or ""))
        for entry in self.config.chain:
            p = (entry.get("provider") or "").strip().lower()
            m = (entry.get("model") or "").strip()
            if p and (p, m) not in ordered and p != pref:
                ordered.append((p, m))

        for provider, model in ordered:
            if self.in_cooldown(provider):
                self._log("cooldown_skip", provider, reason="in_cooldown")
                continue
            st = self._state(provider)
            # If still marked demoted but cooldown expired, allow only after probe
            # handled by maybe_revert; for select we allow non-preferred chain.
            if st.demoted and provider == pref:
                self._log("cooldown_skip", provider, reason="demoted_awaiting_probe")
                continue
            self._active_provider = provider
            self._active_model = model or st.model
            if provider != pref and self._on_fallback_since is None:
                self._on_fallback_since = self._clock()
            if provider == pref:
                self._on_fallback_since = None
            self._log("select", provider, reason="available", model=self._active_model)
            return {"provider": provider, "model": self._active_model}

        self._log("select", "", reason="chain_exhausted")
        return None

    def maybe_revert(self, probe: Optional[ProbeFn] = None) -> bool:
        """Sticky auto-revert to preferred when cooldown expired and probe succeeds."""
        pref = (self.config.preferred_provider or "").strip().lower()
        if not pref:
            return False
        st = self._state(pref)
        now = self._clock()
        if not st.demoted:
            # Already on preferred path
            if self._active_provider == pref:
                return False
            # Preferred never demoted — snap back
            self._active_provider = pref
            self._active_model = self.config.preferred_model or st.model
            self._on_fallback_since = None
            self._log("revert", pref, reason="preferred_healthy")
            return True

        if now < st.cooldown_until:
            return False

        model = self.config.preferred_model or st.model
        if probe is not None:
            try:
                healthy = bool(probe(pref, model))
            except Exception:
                healthy = False
            if not healthy:
                # Extend cooldown lightly so we don't hammer
                st.cooldown_until = now + min(30.0, self.config.cooldown_sec)
                self._log("revert", pref, reason="probe_failed")
                return False

        st.demoted = False
        st.strikes = 0
        st.cooldown_until = 0.0
        self._active_provider = pref
        self._active_model = model
        self._on_fallback_since = None
        self._log("revert", pref, reason="probe_ok" if probe else "cooldown_expired")
        return True

    def check_sustained_failover(self) -> bool:
        """If on fallback longer than threshold, write alert. Returns True if alerted."""
        if self._on_fallback_since is None:
            if self.alert_path and self.alert_path.exists():
                try:
                    self.alert_path.unlink()
                except OSError:
                    pass
            return False
        elapsed = self._clock() - self._on_fallback_since
        if elapsed < self.config.sustained_failover_alert_sec:
            return False
        self._log(
            "alert_sustained",
            self._active_provider or "",
            reason="fallback_too_long",
            elapsed_sec=elapsed,
        )
        if self.alert_path is not None:
            self.alert_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "status": "alert",
                "ts": time.time(),
                "iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "active_provider": self._active_provider,
                "preferred_provider": self.config.preferred_provider,
                "elapsed_sec": elapsed,
                "message": (
                    "T1000 model failover: running on fallback longer than threshold — "
                    "possible billing/rate problem on preferred provider"
                ),
            }
            self.alert_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        return True

    @property
    def active(self) -> Dict[str, str]:
        return {
            "provider": self._active_provider or "",
            "model": self._active_model or "",
        }


def classify_http_status(status: int) -> FailClass:
    if status == 402:
        return FailClass.BILLING
    if status == 429:
        return FailClass.RATE_LIMIT
    if status in {401, 403}:
        return FailClass.AUTH
    if 500 <= status <= 599:
        return FailClass.SERVER
    return FailClass.OTHER


def default_policy_from_env(
    *,
    preferred_provider: str,
    preferred_model: str = "",
    chain: Optional[Sequence[Dict[str, str]]] = None,
    state_dir: Optional[Path] = None,
) -> ModelFailoverPolicy:
    root = state_dir or Path(
        os.path.expanduser(os.environ.get("HERMES_HOME", "~/.t1000"))
    ) / "failover"
    cfg = FailoverConfig(
        preferred_provider=preferred_provider,
        preferred_model=preferred_model,
        chain=list(chain or []),
        strikes_to_demote=int(os.environ.get("T1000_FAILOVER_STRIKES", "2")),
        cooldown_sec=float(os.environ.get("T1000_FAILOVER_COOLDOWN_SEC", "60")),
        sustained_failover_alert_sec=float(
            os.environ.get("T1000_FAILOVER_SUSTAINED_SEC", str(2 * 3600))
        ),
    )
    return ModelFailoverPolicy(
        cfg,
        log_path=root / "route-decisions.jsonl",
        alert_path=root / "sustained-failover-alert.json",
    )
