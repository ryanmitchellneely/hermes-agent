# SPEC: Human Gates as Reactions (chip-ify the ack queue)

## Problem + evidence
The mesh generates human decisions faster than they clear: 42 blocked cards, with waits of
83h/67h/34h+ measured (pm-factory 2026-08-09). Kevin-side it's worse — his queue (W4
dual-ack t_a97cf1e6, width-ladder ack t_89c72b32, GNOME trim t_a6232cb1, Entrpi fork
t_43e997d2, plus two Chamberlain decisions blocked 34h+) rots because Kevin isn't in these
chats. Meanwhile the exact machinery for react-to-decide already exists and is production-
proven: Chamberlain chips on Buzz (`k2_hub/buzz.py send_chip_message` → #chamberlain
channel, reactions read back via `messages get --kinds 7`, outcomes reply in-thread).
Today's sign-off session proved the pattern's value interactively; this makes it async.

## V1 scope
1. A mapper (VPS-side, next to Chamberlain's chip poller) that renders selected mesh/k2
   HUMAN-blocked cards as decision chips into the OWNER's channel (Kevin → #chamberlain,
   Ryan → his Telegram via existing notify), with the card's one-sentence decision and
   2-3 emoji-mapped options.
2. Reaction reader maps 👍/👎/🤷 back to: a comment on the card recording who/when/what
   + for single-ack gates, an unblock. NEVER auto-completes a card; ack-recording only.
3. Scope v1 to a hand-curated allowlist file of card ids (5-10 max at a time), not the
   whole blocked column. Dual-ack cards (W4) record the ack and wait for the other person.
4. The twice-daily digest links each listed human gate to its chip ("react in #chamberlain").

## Non-goals
No mesh-DB access from the VPS (the mapper reads an exported JSON the Mac digest cron
already produces — extend kevin_digest.py to also write human-gates.json and scp it with
the same fail-soft pattern as the Buzz post). No new bot; no Slack; no auto-unblock of
restart-path cards ever (allowlist excludes them by rule).

## Gates & risks
- Cross-estate: touches K2 repo (chip mapper handler) → normal PR + review lanes apply.
- An ack recorded from a reaction is weaker evidence than a typed comment — mitigate by
  writing the chip text verbatim into the card comment so the record shows exactly what
  was asked.
- Spoofing: reactions are pubkey-signed on the relay; only Kevin's/Ryan's keys count.
- Requires Kevin's buy-in on the pattern → the proposal itself goes through his inbox.

## Card decomposition
- CG-1 (blocked, HUMAN Kevin): inbox note to kevin-claude proposing the pattern + the v1
  allowlist; Kevin acks the UX before anything is built.
- CG-2 (todo, parent CG-1): extend kevin_digest.py to emit human-gates.json + ship to VPS.
- CG-3 (todo, parent CG-2): chip mapper + reaction reader handler in k2-hub (PR, review).
- CG-4 (blocked, HUMAN Ryan+Kevin, parent CG-3): arm on the real allowlist after one
  dry-run batch with fake cards.

## Open questions
1. Should Ryan's side stay Telegram-text ("reply 1/2/3") instead of Buzz reactions, since
   his surface is Telegram-first?
