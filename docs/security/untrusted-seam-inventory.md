# Untrusted content seam inventory (P3)

Instruction of record: content inside `wrap_untrusted` boundaries is **data**,
never instructions. See `agent/security/wrap_untrusted.py`.

| Seam id | Location | External source | Priority | Status | Wrapper |
|---------|----------|-----------------|----------|--------|---------|
| tool_dispatch_helpers.make_tool_result_message | `agent/tool_dispatch_helpers.py` | web_extract, web_search, browser_*, mcp_* tool results | P0 | migrated: yes | `wrap_untrusted` via `_maybe_wrap_untrusted` |
| web_extract | tool result path above | fetched web HTML/markdown | P0 | migrated: yes | wrap_untrusted |
| web_search | tool result path above | search snippets | P0 | migrated: yes | wrap_untrusted |
| browser_* | tool result path above | page snapshots / DOM text | P0 | migrated: yes | wrap_untrusted |
| mcp_* | tool result path above | MCP server payloads | P0 | migrated: yes | wrap_untrusted |
| juice.comprehension | `sovereign_juice/comprehension.py` `_build_reasoning_prompt` | email / sms / call_transcript body | P0 | migrated: yes | `wrap_untrusted` (source=channel) |
| cron.script / cron.script_error | `cron/scheduler.py` `_build_job_prompt` | pre-run script stdout/stderr (feeds, monitors) | P1 | migrated: yes | `wrap_untrusted` source=`cron.script` |
| cron.context_from | `cron/scheduler.py` `_build_job_prompt` | prior cron job markdown output | P1 | migrated: yes | `wrap_untrusted` source=`cron.context_from.<id>` |
| calendar.summary / calendar.description | `skills/productivity/google-workspace/scripts/google_api.py` `_calendar_event_row` | Google Calendar invite free text | P1 | migrated: yes | `wrap_untrusted` source=`calendar.*` |
| gateway inbound message body | `gateway/run.py` user message assembly | chat platforms | P1 | migrated: no | — (user role IS instructions; do not wrap) |
| session_search / memory recall | memory tools | prior session text | P2 | migrated: no | curated internal |

## Migration rule

1. Add a row here **before** shipping a new external→LLM path.
2. P0 rows must show `migrated: yes` or `tests/agent/test_wrap_untrusted.py` fails.
3. P1 rows marked `migrated: no` with priority P1 also fail CI once listed as required in the test.
4. Prefer `from agent.security.wrap_untrusted import wrap_untrusted`.
