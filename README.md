# DiscordRPG

## Run transitions

Apply `migrations/001_run_transitions.sql` to the existing PostgreSQL database
before running this version. It adds saved floor, room completion, reward choices,
and a state ID used to reject buttons from older screens. PostgreSQL 13 or newer
is required for `gen_random_uuid()`.

```sh
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f migrations/001_run_transitions.sql
uv sync --locked
uv run python main.py
```

Set `DATABASE_URL` and `DISCORD_TOKEN` in `.env`. This migration extends the
existing game tables; it does not create a new database from scratch.

Use `!start` to create a character, then `!run` and confirm Yes. Each floor has
six rooms, starting at basecamp and ending with a boss (the final boss on floor
four). Every room has a **Complete Room** placeholder button. Battle placeholders
award 100 XP; other placeholders have no rewards yet. Level-ups offer cards before
the map appears. The current catalog only contains common cards, so empty rarity
pools fall back to available cards.

**Move** enters the next room. After the boss, **Next Floor** generates the next
floor and enters its basecamp. After the final boss, **Finish Run** closes the run
through the existing victory/relic handling. No combat mechanics are implemented.

Use `!run` again after closing a message or restarting the bot. It restores the
room, pending card choices, map, or completion screen from saved state. Older
messages cannot repeat rewards or move the player twice.

To test manually, complete all six rooms on each of the four floors, select every
offered card, and finish the run. Reopen `!run` at a room, a card selection, and a
map to check resume behavior. Try the same action from two open `!run` messages;
only the first should change the run.

Run the transition tests with installed project dependencies:

```sh
uv run python -m unittest discover -s tests -v
```
