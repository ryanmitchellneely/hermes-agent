"""Shared kanban task-estimate core.

Asks the auxiliary (auto-routed) model for a rough token/complexity/
local-vs-frontier read on a task, then builds a concrete model/provider
suggestion from Ryan's desk catalog. NOT a dollar cost estimate — providers
don't report cost reliably, so this estimates tokens + a complexity band
with a one-line rationale.

Historically this lived inline in ``plugins/kanban/dashboard/plugin_api.py``
behind two on-click endpoints (``POST /estimate`` for the create dialog,
``POST /tasks/:id/estimate`` for an existing task). It's extracted here,
with zero dependency on FastAPI or ``kanban_db``, so it can also be driven
by the gateway dispatcher's auto-estimate tick (see the ``estimate_status``
column in ``kanban_db.py`` and ``gateway/kanban_watchers.py``) — the same
core now runs both on-click (dashboard) and on-create (dispatcher), and
cannot drift between the two call sites.
"""

from __future__ import annotations

from typing import Optional

_ESTIMATE_SYSTEM_PROMPT = (
    "You estimate how much work an autonomous coding agent will spend on a "
    "kanban task, and whether a strong local LLM is enough vs a frontier model. "
    "Given the task title and description, respond with STRICT "
    "JSON only (no prose, no code fence):\n"
    '{"est_tokens": <integer total tokens across the whole run>, '
    '"complexity": "S"|"M"|"L", '
    '"lane": "local"|"frontier"|"either", '
    '"rationale": "<one short sentence>"}\n'
    "Base the token figure on a realistic multi-turn agent run (reading files, "
    "tool calls, edits, retries) — not a single reply. S≈small/localized, "
    "M≈multi-file, L≈broad or ambiguous.\n"
    "lane guidance (route meaningful work to local when safe):\n"
    '- "local": clear acceptance criteria; localized/mechanical code edits; '
    "boilerplate; well-scoped multi-file work without architecture ambiguity; "
    "no security-sensitive design judgment. Good candidates for local models "
    "(DeepSeek V4 Flash/Pro, Spark Qwen3.8-Flash-Next, MBP coder).\n"
    '- "frontier": ambiguous requirements; architecture/trade-off design; '
    "security-sensitive changes; novel multi-system reasoning; needs peak IQ "
    "or live web judgment. Prefer Grok 4.5 / Claude Max (ACP).\n"
    '- "either": medium multi-file with clear criteria — local can try, '
    "frontier is safer if quality bar is high.\n"
    "Be honest that this is a rough guess."
)


def _normalize_estimate_lane(
    lane: Optional[str],
    complexity: Optional[str],
    est_tokens: int,
    *,
    risky: bool = False,
) -> Optional[str]:
    """Normalize model-returned lane, with a local-first deterministic fallback.

    Preference order when the aux model is silent/vague:
      - risky signals → frontier
      - S (or small token budget) → local
      - M → local when not risky (user wants local preferred with no risk)
      - L / huge token guess → frontier
    """
    value = str(lane or "").strip().lower()
    if value in {"local", "frontier", "either"}:
        # Downgrade a timid "either" to local when nothing looks risky.
        if value == "either" and not risky and complexity in {None, "S", "M"}:
            if not est_tokens or est_tokens < 100_000:
                return "local"
        # Never honor "local" when the task text is clearly high-risk.
        if value == "local" and risky:
            return "frontier"
        return value
    if risky or complexity == "L" or (est_tokens and est_tokens >= 120_000):
        return "frontier"
    if complexity in {"S", "M", None}:
        return "local"
    if est_tokens and est_tokens < 40_000:
        return "local"
    return "local" if not risky else "frontier"


# Phrases that mean "don't put this on a local model" even if size looks small.
_RISK_PATTERNS = (
    "architect",
    "security",
    "auth",
    "oauth",
    "permission",
    "encrypt",
    "migrat",
    "redesign",
    "rewrite the system",
    "multi-tenant",
    "compliance",
    "hipaa",
    "pci",
    "production incident",
    "data loss",
    "irreversible",
    "novel algorithm",
    "research spike",
    "ambiguous",
    "unclear requirements",
    "figure out how",
    "explore options",
    "trade-?off",
    "threat model",
    # Credential-disclosure risk screen. Added after K2
    # harness-and-model-lane-findings.md (Sec-15, 2026-08-28): a production
    # dispatch card that asked a worker to read and report a credential
    # value tripped none of the patterns above (no security/auth/encrypt
    # keyword appears in "report the value of SENDGRID_API_KEY"), so the
    # estimator never routed it away from local. Bare "token" is
    # deliberately excluded -- this codebase discusses LLM tokens in nearly
    # every card body, and that word would misfire the risk screen on
    # routine estimation work rather than credential handling.
    "secret",
    "credential",
    "api[_ -]?key",
    r"\.env\b",
    "password",
    "private[_ -]?key",
    "exfiltrat",
)


def _estimate_is_risky(title: str, body: Optional[str], complexity: Optional[str]) -> bool:
    """Cheap lexical risk screen — prefer frontier when these fire."""
    if complexity == "L":
        return True
    text = f"{title or ''}\n{body or ''}".lower()
    import re as _re

    for pat in _RISK_PATTERNS:
        if _re.search(pat, text):
            return True
    return False


# Local OpenAI-compatible endpoints we consider "local lane ready" for estimate
# UI. Keep the probe cheap: GET /models with a short timeout. Order is
# preference for the primary suggestion (DS4 first — Ryan's primary local coder).
_LOCAL_PROVIDER_PREFERENCE = (
    "kevin-spark",
    "spark",
    "mbp-ollama",
    "ollama",
    "local",
    "llama-cpp",
    "vllm",
)

# Preferred model id per local provider when the provider lists several.
_LOCAL_MODEL_PREFERENCE = {
    "kevin-spark": ("deepseek-v4-flash", "deepseek-v4-pro"),
    # 2026-09-06 (t_37efebbb): provider `spark` is Qwen3.8-Flash-Next (llama.cpp, :11439).
    # gpt-oss:120b stays as an alias name the same server answers to.
    "spark": ("qwen3.8-flash-next", "gpt-oss:120b", "hermes3:8b-16k"),
    "mbp-ollama": ("qwen3-coder:30b", "hf.co/NousResearch/Hermes-4.3-36B-GGUF:Q4_K_M", "hermes3:8b"),
}

# Models that must not take the FIRST attempt on M/L cards. Measured
# 2026-08-13: the estimator sent 50+ M-tier cards here with rubber-stamp
# rationales while the model completed 2 of 36 runs (55.6% crashed, protocol
# non-compliance — clean exit, no terminal verb). Flash keeps S-tier and its
# proven DevBot/eval-apply lane; this only changes who goes first on M/L.
_FLASH_CLASS_MODELS = frozenset({"deepseek-v4-flash"})


def _demote_flash_for_m_plus(suggestion: dict, alternatives: list, complexity: str):
    """Never suggest a flash-class model as the first attempt on an M/L card.

    Promotes the first capable LOCAL alternative if one is ready (stays on the
    boxes), else sonnet from the frontier fallbacks. The flash pick is kept as
    the first alternative so a human override stays one click. S cards are
    untouched — flash earns its keep there.
    """
    if complexity not in ("M", "L") or suggestion.get("model") not in _FLASH_CLASS_MODELS:
        return suggestion, alternatives
    promoted = None
    for i, alt in enumerate(alternatives):
        if alt.get("lane") == "local" and alt.get("model") not in _FLASH_CLASS_MODELS:
            promoted = dict(alternatives.pop(i))
            break
    if promoted is None:
        for prov, mid, lab in _FRONTIER_FALLBACKS:
            if mid == "sonnet":
                promoted = {"lane": "frontier", "provider": prov, "model": mid, "label": lab}
                alternatives = [
                    a for a in alternatives
                    if not (a.get("model") == mid and a.get("provider") == prov)
                ]
                break
    if promoted is None:
        return suggestion, alternatives
    demoted = {k: suggestion.get(k) for k in ("lane", "provider", "model", "label")}
    promoted["effort"] = suggestion.get("effort") or ("high" if complexity == "L" else "medium")
    promoted["local_ok"] = suggestion.get("local_ok")
    promoted["why"] = (
        f"{complexity}-tier: flash-class first attempts measured at 55.6% crash "
        "(protocol non-compliance, 2026-08-13) — routing to a capable model; "
        "flash stays available as the first alternative"
    )
    return promoted, [demoted] + list(alternatives)


# Frontier fallbacks when local is unsafe or offline (desk catalog order).
_FRONTIER_FALLBACKS = (
    ("xai-oauth", "grok-4.5", "Grok 4.5"),
    ("claude-acp", "opus[1m]", "Claude Opus (ACP)"),
    ("claude-acp", "sonnet", "Claude Sonnet (ACP)"),
    ("claude-acp", "default", "Claude (ACP default)"),
)


def _short_provider_label(name: str, pid: str) -> str:
    return {
        "Kevin Spark DS4": "DS4",
        "MBP Ollama (local)": "MBP",
        "Spark Ollama (tunnel :11435)": "Spark",
        "kevin-spark": "DS4",
        "mbp-ollama": "MBP",
        "spark": "Spark",
        "xai-oauth": "Grok",
        "claude-acp": "Claude ACP",
    }.get(str(name), {
        "kevin-spark": "DS4",
        "mbp-ollama": "MBP",
        "spark": "Spark",
    }.get(pid, str(name or pid)))


def _pick_model_from_endpoint(endpoint: dict) -> Optional[str]:
    """Choose the best model id listed on a readiness endpoint."""
    pid = str(endpoint.get("id") or "")
    models = [str(m) for m in (endpoint.get("models") or []) if m]
    prefs = _LOCAL_MODEL_PREFERENCE.get(pid) or ()
    for pref in prefs:
        if pref in models:
            return pref
    return models[0] if models else None


def _build_estimate_suggestion(
    *,
    lane: Optional[str],
    complexity: Optional[str],
    est_tokens: int,
    rationale: Optional[str],
    title: str,
    body: Optional[str],
    local_readiness: dict,
    risky: bool,
) -> dict:
    """Concrete model pick from Ryan's desk catalog — local preferred when safe.

    Returned shape is stable for the UI::

        {
          "lane": "local"|"frontier"|"either",
          "provider": "kevin-spark",
          "model": "deepseek-v4-flash",
          "label": "DS4 · deepseek-v4-flash",
          "effort": "medium"|null,
          "why": "…",
          "local_ok": true,
          "alternatives": [{provider, model, label, lane}, ...]
        }
    """
    ready = [e for e in (local_readiness.get("endpoints") or []) if e.get("ready")]
    local_ok = bool(ready)

    # Prefer local whenever lane says so AND something is actually up.
    want_local = (lane in {"local", "either", None}) and not risky and local_ok
    if lane == "local" and not local_ok:
        # User-intent local but endpoints down → still surface the intended
        # local pin (DS4) so Apply wires the right override; worker will fail
        # closed rather than silently burning frontier.
        want_local = True

    alternatives: list[dict] = []
    suggestion: dict

    if want_local:
        primary_ep = ready[0] if ready else None
        # If nothing ready, still propose the preferred configured local.
        if primary_ep is None:
            entries = _local_provider_entries()
            if entries:
                pid, p = entries[0]
                models = p.get("models") or []
                model = None
                prefs = _LOCAL_MODEL_PREFERENCE.get(pid) or ()
                for pref in prefs:
                    if pref in [str(m) for m in models]:
                        model = pref
                        break
                if model is None and models:
                    model = str(models[0])
                primary_ep = {
                    "id": pid,
                    "name": p.get("name") or pid,
                    "models": [str(m) for m in models],
                    "ready": False,
                }
                if model:
                    # ensure pick works
                    primary_ep.setdefault("models", [model])

        model = _pick_model_from_endpoint(primary_ep) if primary_ep else None
        pid = str((primary_ep or {}).get("id") or "kevin-spark")
        short = _short_provider_label((primary_ep or {}).get("name") or pid, pid)
        if not model:
            model = (_LOCAL_MODEL_PREFERENCE.get(pid) or ("deepseek-v4-flash",))[0]
        why_bits = []
        if risky:
            why_bits.append("risk signals present — reconsider frontier")
        elif complexity == "S":
            why_bits.append("small/scoped — local is enough")
        elif complexity == "M":
            why_bits.append("medium but no high-risk signals — prefer local")
        else:
            why_bits.append("local preferred when risk is low")
        if primary_ep and not primary_ep.get("ready"):
            why_bits.append(f"{short} looks offline right now")
        elif local_readiness.get("summary"):
            why_bits.append(str(local_readiness["summary"]))
        suggestion = {
            "lane": "local",
            "provider": pid,
            "model": model,
            "label": f"{short} · {model}",
            "effort": "medium" if complexity == "M" else ("low" if complexity == "S" else "high"),
            "why": "; ".join(why_bits),
            "local_ok": bool(primary_ep and primary_ep.get("ready")),
        }
        # Other ready locals as alternatives
        for ep in ready[1:3]:
            m = _pick_model_from_endpoint(ep)
            if not m:
                continue
            sp = _short_provider_label(ep.get("name") or ep.get("id"), str(ep.get("id")))
            alternatives.append({
                "lane": "local",
                "provider": ep.get("id"),
                "model": m,
                "label": f"{sp} · {m}",
            })
        # Frontier escape hatch always listed
        for prov, mid, lab in _FRONTIER_FALLBACKS[:2]:
            alternatives.append({
                "lane": "frontier",
                "provider": prov,
                "model": mid,
                "label": lab,
            })
        suggestion, alternatives = _demote_flash_for_m_plus(
            suggestion, alternatives, complexity
        )
    else:
        # Frontier primary
        prov, mid, lab = _FRONTIER_FALLBACKS[0]
        why = rationale or (
            "high-risk or large/ambiguous — use frontier"
            if risky or complexity == "L"
            else ("no local endpoint ready — use frontier" if not local_ok else "frontier recommended")
        )
        suggestion = {
            "lane": "frontier",
            "provider": prov,
            "model": mid,
            "label": lab,
            "effort": "high" if complexity == "L" or risky else "medium",
            "why": why,
            "local_ok": local_ok,
        }
        for prov2, mid2, lab2 in _FRONTIER_FALLBACKS[1:3]:
            alternatives.append({
                "lane": "frontier",
                "provider": prov2,
                "model": mid2,
                "label": lab2,
            })
        # Offer local as alternative if up, even on frontier rec
        for ep in ready[:2]:
            m = _pick_model_from_endpoint(ep)
            if not m:
                continue
            sp = _short_provider_label(ep.get("name") or ep.get("id"), str(ep.get("id")))
            alternatives.append({
                "lane": "local",
                "provider": ep.get("id"),
                "model": m,
                "label": f"{sp} · {m}",
            })

    suggestion["alternatives"] = alternatives
    # Mirror top-level lane onto the suggestion for UI simplicity
    if lane and suggestion.get("lane") == "local" and lane == "either" and not risky:
        suggestion["lane"] = "local"  # still prefer local
    return suggestion


def _local_provider_entries(cfg: Optional[dict] = None) -> list[tuple[str, dict]]:
    """Return (provider_id, provider_dict) for configured local-ish providers."""
    if cfg is None:
        try:
            from hermes_cli.config import load_config

            cfg = load_config() or {}
        except Exception:
            cfg = {}
    providers = cfg.get("providers") or {}
    if not isinstance(providers, dict):
        return []
    out: list[tuple[str, dict]] = []
    seen: set[str] = set()
    # Preferred ids first, then any remaining with loopback / ollama-ish URL.
    for pid in _LOCAL_PROVIDER_PREFERENCE:
        p = providers.get(pid)
        if isinstance(p, dict) and pid not in seen:
            out.append((pid, p))
            seen.add(pid)
    for pid, p in providers.items():
        if pid in seen or not isinstance(p, dict):
            continue
        api = str(p.get("api") or p.get("base_url") or "").lower()
        # Only auto-include loopback / known local ports — never cloud OpenAI URLs.
        if any(
            h in api
            for h in (
                "127.0.0.1",
                "localhost",
                "0.0.0.0",
                ":11434",
                ":11435",
                ":8889",
            )
        ):
            out.append((str(pid), p))
            seen.add(str(pid))
    return out


def _probe_openai_compatible(base_url: str, timeout: float = 0.6) -> tuple[bool, Optional[float], Optional[str]]:
    """Cheap liveness probe for an OpenAI-compatible base URL.

    Returns (ready, latency_ms, error_or_none). Tries GET {base}/models.
    """
    import time
    import urllib.error
    import urllib.request

    url = (base_url or "").rstrip("/")
    if not url:
        return False, None, "no base_url"
    if not url.endswith("/models"):
        # accept either .../v1 or .../v1/models
        if url.endswith("/v1"):
            url = url + "/models"
        elif "/v1/" in url:
            pass
        else:
            url = url + "/models"
    t0 = time.monotonic()
    try:
        req = urllib.request.Request(url, method="GET", headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec B310 — local loopback only
            code = getattr(resp, "status", None) or resp.getcode()
            _ = resp.read(256)
        ms = (time.monotonic() - t0) * 1000.0
        if 200 <= int(code or 0) < 300:
            return True, round(ms, 1), None
        return False, round(ms, 1), f"http {code}"
    except Exception as exc:
        ms = (time.monotonic() - t0) * 1000.0
        return False, round(ms, 1), f"{type(exc).__name__}"


def probe_local_model_readiness(cfg: Optional[dict] = None) -> dict:
    """Probe configured local providers; used by estimate UI.

    Shape::

        {
          "any_ready": bool,
          "ready_count": int,
          "total": int,
          "summary": "DS4 ready · MBP down",
          "endpoints": [
            {"id", "name", "ready", "base_url", "models", "latency_ms", "error"}
          ]
        }
    """
    entries = _local_provider_entries(cfg)
    endpoints: list[dict] = []
    for pid, p in entries:
        api = str(p.get("api") or p.get("base_url") or "").strip()
        name = str(p.get("name") or pid)
        models = p.get("models") or []
        if not isinstance(models, list):
            models = []
        ready, latency_ms, err = _probe_openai_compatible(api)
        endpoints.append(
            {
                "id": pid,
                "name": name,
                "ready": ready,
                "base_url": api,
                "models": [str(m) for m in models[:6]],
                "latency_ms": latency_ms,
                "error": None if ready else err,
            }
        )
    ready_eps = [e for e in endpoints if e.get("ready")]
    # Prefer first ready in preference order for summary label
    if ready_eps:
        top = ready_eps[0]
        label = top.get("name") or top.get("id")
        # Shorten common names for the pill
        short = {
            "Kevin Spark DS4": "DS4",
            "MBP Ollama (local)": "MBP",
            "Spark Ollama (tunnel :11435)": "Spark",
        }.get(str(label), str(label))
        if len(ready_eps) == 1:
            summary = f"{short} ready"
        else:
            summary = f"{short} +{len(ready_eps) - 1} local ready"
    elif endpoints:
        summary = "local endpoints down"
    else:
        summary = "no local providers configured"
    return {
        "any_ready": bool(ready_eps),
        "ready_count": len(ready_eps),
        "total": len(endpoints),
        "summary": summary,
        "endpoints": endpoints,
    }


def run_estimate(title: str, body: Optional[str]) -> dict:
    """Shared estimate core: ask the auto-routed auxiliary model for a rough
    token + complexity + local/frontier lane read on a task described by
    ``title``/``body``.

    Never raises — a bad config / parse / API error becomes
    ``{"ok": False, "reason": ...}`` so callers (the dashboard endpoints, the
    dispatcher's auto-estimate tick) can handle it inline instead of catching
    exceptions.
    """
    if not (title or "").strip():
        return {"ok": False, "reason": "a title is required to estimate"}

    try:
        from agent.auxiliary_client import call_llm
    except Exception:
        return {"ok": False, "reason": "auxiliary client unavailable"}

    def _cap(s: Optional[str], n: int) -> str:
        s = (s or "").strip()
        return s if len(s) <= n else s[:n] + "…"

    user_msg = (
        f"Title: {_cap(title, 400)}\n\n"
        f"Description:\n{_cap(body, 4000) or '(none)'}"
    )
    try:
        resp = call_llm(
            task="kanban_estimator",
            messages=[
                {"role": "system", "content": _ESTIMATE_SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.0,
            max_tokens=300,
            timeout=60,
        )
    except Exception as exc:
        return {"ok": False, "reason": f"LLM error: {type(exc).__name__}"}

    try:
        raw = (resp.choices[0].message.content or "").strip()
        model = getattr(resp, "model", None)
    except Exception:
        raw, model = "", None

    # Reuse the same tolerant JSON-blob extraction the specifier uses.
    parsed: Optional[dict] = None
    try:
        import json as _json
        import re as _re
        blob = raw
        if not blob.lstrip().startswith("{"):
            m = _re.search(r"\{.*\}", blob, _re.DOTALL)
            blob = m.group(0) if m else blob
        obj = _json.loads(blob)
        if isinstance(obj, dict):
            parsed = obj
    except Exception:
        parsed = None

    if not parsed:
        return {"ok": False, "reason": "could not parse an estimate from the model"}

    try:
        est_tokens = int(parsed.get("est_tokens") or 0)
    except (TypeError, ValueError):
        est_tokens = 0
    complexity = str(parsed.get("complexity") or "").strip().upper()
    if complexity not in {"S", "M", "L"}:
        complexity = None
    rationale = str(parsed.get("rationale") or "").strip() or None
    risky = _estimate_is_risky(title, body, complexity)
    lane = _normalize_estimate_lane(
        parsed.get("lane"), complexity, est_tokens, risky=risky
    )

    # Always attach live local-endpoint readiness so the caller can show
    # whether a "local" lane recommendation is actually runnable right now
    # (DS4 / Spark / MBP Ollama). Cheap probes; never fails the estimate.
    try:
        local_readiness = probe_local_model_readiness()
    except Exception as exc:
        local_readiness = {
            "any_ready": False,
            "ready_count": 0,
            "total": 0,
            "summary": f"readiness probe failed: {type(exc).__name__}",
            "endpoints": [],
        }

    try:
        suggestion = _build_estimate_suggestion(
            lane=lane,
            complexity=complexity,
            est_tokens=est_tokens,
            rationale=rationale,
            title=title,
            body=body,
            local_readiness=local_readiness,
            risky=risky,
        )
        # Keep top-level lane aligned with the concrete pick.
        if suggestion.get("lane") in {"local", "frontier", "either"}:
            lane = suggestion["lane"]
    except Exception as exc:
        suggestion = {
            "lane": lane or "frontier",
            "provider": "xai-oauth",
            "model": "grok-4.5",
            "label": "Grok 4.5",
            "effort": "medium",
            "why": f"suggestion builder failed ({type(exc).__name__}); defaulting to frontier",
            "local_ok": bool(local_readiness.get("any_ready")),
            "alternatives": [],
        }

    return {
        "ok": True,
        "est_tokens": est_tokens,
        "complexity": complexity,
        "lane": lane,
        "rationale": rationale,
        "model": model,
        "risky": risky,
        "local_readiness": local_readiness,
        "suggestion": suggestion,
    }
