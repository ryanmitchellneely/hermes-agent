# Claude ACP lane (T1000)

**You stay the brain (Hermes / Grok default). Claude is an engine via ACP.**

## Architecture

```
Hermes (tools, memory, ops)  --ACP stdio-->  claude-agent-acp  -->  Claude Max OAuth
```

Same Buzz pattern. Avoids native Anthropic HTTP "third-party extra usage" wall.

The ACP **process + session are reused** across turns on the same Hermes client
(agent loop). History deltas are sent after the first turn so Claude keeps its
own continuity (files read, internal scratch) without duplicating the full
transcript. Session recycles on: client close, idle timeout (default 15m),
context compression / non-prefix history rewrite, or transport error.

## Binary

Default discovery order:

1. `HERMES_CLAUDE_ACP_COMMAND`
2. `claude-agent-acp` on PATH (`~/.local/bin/claude-agent-acp` symlink)
3. Buzz bundle: `~/Library/Application Support/Buzz/node-tools/bin/claude-agent-acp`

## Auth (Ryan interactive)

```bash
export PATH="$HOME/.local/bin:$PATH"
export HERMES_HOME=~/.t1000
claude auth login
hermes auth status claude-acp
hermes chat -q "ping" --provider claude-acp --model haiku
```

## Swap (session / Desktop dropdown)

Picker shows **only**:

- **xAI Grok OAuth** (desk default)
- **Claude Agent ACP** (Max sub)
- **Spark Ollama**
- **MBP Ollama**

Noise (Copilot, Nous, Anthropic HTTP, MoA, …) is in `model_catalog.excluded_providers`.

```
/model claude-acp
/model adv          # alias → claude-acp / opus[1m]
/model sonnet
/model grok         # back to desk brain engine
```

**Effort dial** (Desktop row submenu or `/reasoning low|medium|high|xhigh|max`) is applied via ACP `session/set_config_option` → `effort`.

Default config stays `xai-oauth` / `grok-4.5`.

## Permission mode (native Claude tools)

Claude Code may request permission for Bash / Edit / etc. Hermes answers via ACP
`session/request_permission`:

```yaml
# ~/.t1000/config.yaml
model:
  claude_acp:
    permission_mode: auto   # deny | auto  (default: deny)
    idle_seconds: 900       # recycle idle ACP process
```

| Mode | Behavior |
|------|----------|
| `deny` | Read-only Opus — native Bash/Edit cancelled (safe default) |
| `auto` | Allow native Claude tools (still path-guarded for `fs/*`) |

Env override (tests / one-shot): `HERMES_CLAUDE_ACP_PERMISSION_MODE=auto`.

**Note:** `auto` lets the Claude Agent SDK run shell on your machine inside the
ACP cwd. Prefer Grok/Hermes tools for desk ops; use Opus+auto for code craft.

## Context window

ACP short ids resolve to **1M** in Hermes metadata (`opus[1m]`,
`claude-fable-5[1m]`, …) so the compressor/counter matches Claude's real ceiling
instead of falling through to the 256k default.

## Caches (what actually applies)

| Layer | What it does | Status |
|-------|----------------|--------|
| **ACP process/session pool** | Keeps `claude-agent-acp` alive across Hermes `reuse_evict` | ✅ scoped by `HERMES_SESSION_ID` + cwd |
| **Delta prompts** | After turn 1, only new messages are sent into the live ACP session | ✅ |
| **Claude Code internal cache** | Prefix/tool cache *inside* the ACP session | ✅ only if process stays warm |
| **Hermes request-client cache** | Reuses the OpenAI-shaped facade when not closed | ✅ soft `close()` is a no-op |
| **`prompt_caching:` in config.yaml** | Anthropic HTTP `cache_control` markers | ❌ N/A on ACP (no HTTP) |
| **OpenRouter response cache** | N/A on this lane | ❌ |
| **Context compressor** | Compacts Hermes transcript at `threshold × context_length` | ✅ uses 1M for opus[1m] |

**Idle:** backends recycle after `model.claude_acp.idle_seconds` (default 900).

**Do not** share one ACP backend across Desktop chats — pool key includes the
Hermes session id so continuity stays per-conversation.

## Files

- `agent/claude_acp_client.py`
- `plugins/model-providers/claude-acp/`
- external-process auth generalized in `hermes_cli/auth.py`
- picker explicit_only recognizes ACP + aliases
