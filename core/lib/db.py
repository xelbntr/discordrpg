import asyncpg
from functools import wraps
from core.lib.log import dblogger
import discord
from discord.ext import commands
import enum

class GearTier(enum.IntEnum):
    common = 1
    rare = 2
    legendary = 3
    prismatic_i = 4
    prismatic_ii = 5
    prismatic_iii = 6

async def init_db(conn: asyncpg.Connection):
    await conn.set_type_codec(
        'gear_tier',
        encoder=lambda t: t.name,
        decoder=lambda t: GearTier[t],
        schema='public'
    )

dbpool: asyncpg.Pool | None = None
def db_exception_handler(func):
    @wraps(func)
    async def wrapper(user: discord.User | discord.Member, *args, **kwargs):
        try:
            if dbpool is None:
                raise RuntimeError("Database pool has not been initialized.")
            async with dbpool.acquire() as conn:
                if conn is None:
                    raise RuntimeError("Database connection was not provided.")
                response = await func(user, *args, conn=conn, **kwargs)
                return response
        except asyncpg.UndefinedTableError as e:
            dblogger.exception(f"Missing DB table. UserID: {user.id}. Error: {e}")
            raise
        except asyncpg.UndefinedColumnError as e:
            dblogger.exception(f"Missing DB column. UserID: {user.id}. Error: {e}")
            raise
        except Exception as e:
            dblogger.exception(f"DB error occurred. UserID: {user.id}. Error: {e}")
            raise
    return wrapper

@db_exception_handler
async def new_player(
    user: discord.User,
    class_name: str,
    *,
    conn: asyncpg.Connection | None = None
):
    response = await conn.fetchrow('''
        INSERT INTO players (user_id, class) 
        VALUES ($1, $2) 
        ON CONFLICT (user_id) DO NOTHING
        RETURNING user_id;
    ''', user.id, class_name)
    return response

@db_exception_handler
async def set_class(
    user: discord.User,
    class_name: str,
    *,
    conn: asyncpg.Connection | None = None
):
    await conn.execute('''
        UPDATE players 
        SET class = $1 
        WHERE user_id = $2
    ''', class_name, user.id)

@db_exception_handler
async def fetch(
    user: discord.User | discord.Member,
    **kwargs
):
    conn: asyncpg.Connection | None = kwargs.get('conn')

    data = {}
    if 'player' in kwargs:
        data['player'] = await conn.fetchrow(
            'SELECT * FROM players WHERE user_id = $1', user.id
        )
    if 'run' in kwargs:
        data['run'] = await conn.fetchrow(
            'SELECT * FROM runs WHERE user_id = $1', user.id
        )
    if 'equipment' in kwargs:
        records = await conn.fetch('''
            SELECT i.*
            FROM run_equipment e
            JOIN run_inventory i ON i.instance_id IN (
                e.armor_instance_id,
                e.weapon_instance_id,
                e.secondary_instance_id
            )
            WHERE e.user_id = $1
        ''', user.id)
        data['equipment'] = {record['slot']: record for record in records}
    return data

# ONLY USE THESE ON COGS!!!
def requires_player():
    async def predicate(ctx):
        data = await fetch(ctx.author, player=True)
        player = data['player']
        if player is None:
            await ctx.send("You don't have a character yet. Use `!start` first.")
            return False
        ctx.player = player
        return True

    return commands.check(predicate)

UPDATE_FIELDS = {
    "xp": ("runs", "xp = {value}"),
    "levelup": ("runs", "run_level = run_level + {value}"),
    "relic": ("players", "relic = relic + {value}"),
    "room": ("runs", "room_sequence = array_append(room_sequence, {value})"),
    "deck": ("runs", "deck = array_append(deck, {value})"),
    "advance_room": ("runs", "current_room = current_room + {value}"),
}


@db_exception_handler
async def update(
    user: discord.User | discord.Member,
    *,
    conn: asyncpg.Connection | None = None,
    **kwargs,
):
    unknown = kwargs.keys() - UPDATE_FIELDS.keys()
    if unknown:
        raise ValueError(f"Unknown update fields: {', '.join(sorted(unknown))}")

    updates = {}
    for field, value in kwargs.items():
        if field == "levelup" and value <= 0:
            continue

        table, expression = UPDATE_FIELDS[field]
        assignments, values = updates.setdefault(table, ([], [user.id]))
        values.append(value)
        assignments.append(expression.format(value=f"${len(values)}"))

    if not updates:
        return None

    async with conn.transaction():
        for table, (assignments, values) in updates.items():
            query = (
                f"UPDATE {table} SET {', '.join(assignments)} "
                "WHERE user_id = $1"
            )
            await conn.execute(query, *values)

@db_exception_handler
async def reset_floor(
        user: discord.User | discord.Member,
        *,
        conn: asyncpg.Connection | None = None,
):

    await conn.execute('''
                           UPDATE runs
                           SET room_sequence = ARRAY[]::text[], current_room = 0
                           WHERE user_id = $1;
                           ''', user.id)
    return True

@db_exception_handler
async def create_run(
    user: discord.User | discord.Member,
    hp: int,
    *,
    conn: asyncpg.Connection | None = None,
):
    return await conn.fetchrow('''
        INSERT INTO runs (user_id, hp, rank_snapshot, current_room)
        SELECT $1, $2, rank, 0
        FROM players
        WHERE user_id = $1
        ON CONFLICT (user_id) DO NOTHING
        RETURNING *;
    ''', user.id, hp)

RUN_STATE_FIELDS = {
    "xp", "run_level", "deck", "current_floor", "current_room",
    "room_sequence", "room_completed", "pending_levels", "card_choices",
}

@db_exception_handler
async def update_run_state(
    user: discord.User | discord.Member,
    state_id,
    *,
    conn: asyncpg.Connection | None = None,
    **kwargs,
):
    unknown = kwargs.keys() - RUN_STATE_FIELDS
    if unknown:
        raise ValueError(f"Unknown run fields: {', '.join(sorted(unknown))}")

    assignments = ["state_id = gen_random_uuid()"]
    values = [user.id, state_id]
    for field, value in kwargs.items():
        values.append(value)
        assignments.append(f"{field} = ${len(values)}")

    return await conn.fetchrow(
        f"UPDATE runs SET {', '.join(assignments)} "
        "WHERE user_id = $1 AND state_id = $2 RETURNING *",
        *values,
    )

@db_exception_handler
async def endrun(
    user: discord.User,
    state_id=None,
    *,
    conn: asyncpg.Connection | None = None
):
    return await conn.fetchrow(
        'DELETE FROM runs WHERE user_id = $1 AND ($2::uuid IS NULL OR state_id = $2) RETURNING *',
        user.id, state_id,
    )
