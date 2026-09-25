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
                response = await func(user, *args, conn=conn, **kwargs)
                return response, False
        except asyncpg.UndefinedTableError as e:
            dblogger.exception(f"Missing DB table. UserID: {user.id}. Error: {e}")
            return None, True
        except asyncpg.UndefinedColumnError as e:
            dblogger.exception(f"Missing DB column. UserID: {user.id}. Error: {e}")
            return None, True
        except Exception as e:
            dblogger.exception(f"DB error occurred. UserID: {user.id}. Error: {e}")
            return None, True
    return wrapper

@db_exception_handler
async def new_player(
    user: discord.User,
    class_name: str,
    *,
    conn: asyncpg.Connection | None = None
):
    if conn is None:
        raise RuntimeError("Database connection was not provided.")
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
    if conn is None:
        raise RuntimeError("Database connection was not provided.")
    await conn.execute('''
        UPDATE players 
        SET class = $1 
        WHERE user_id = $2
    ''', class_name, user.id)

@db_exception_handler
async def fetch_player(
    user: discord.User | discord.Member,
    *,
    conn: asyncpg.Connection | None = None,
):
    if conn is None:
        raise RuntimeError("Database connection was not provided.")
    return await conn.fetchrow(
        'SELECT * FROM players WHERE user_id = $1', user.id
    )


@db_exception_handler
async def fetch_run(
    user: discord.User | discord.Member,
    *,
    conn: asyncpg.Connection | None = None,
):
    if conn is None:
        raise RuntimeError("Database connection was not provided.")
    return await conn.fetchrow(
        'SELECT * FROM runs WHERE user_id = $1', user.id
    )


@db_exception_handler
async def fetch_equipment(
    user: discord.User | discord.Member,
    *,
    conn: asyncpg.Connection | None = None,
):
    if conn is None:
        raise RuntimeError("Database connection was not provided.")
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
    return {record['slot']: record for record in records}


def requires_player():
    async def predicate(ctx):
        player, db_error = await fetch_player(ctx.author)
        if db_error:
            await ctx.send("An error occurred while accessing the database. Please try again later.")
            return False
        if player is None:
            await ctx.send("You don't have a character yet. Use `!start` first.")
            return False
        ctx.player = player
        return True

    return commands.check(predicate)

@db_exception_handler
async def update(
    user: discord.User | discord.Member,
    **kwargs
):
    conn: asyncpg.Connection | None = kwargs.get('conn')
    if conn is None:
        raise RuntimeError("Database connection was not provided.")

    if 'xp' in kwargs:
        await conn.execute('''
            UPDATE runs
            SET xp = $2
            WHERE user_id = $1;
        ''', user.id, kwargs['xp'])

    if kwargs.get('levelup', 0) > 0:
        await conn.execute('''
            UPDATE runs
            SET run_level = run_level + $2
            WHERE user_id = $1;
        ''', user.id, kwargs['levelup'])

    if 'relic' in kwargs:
        await conn.execute('''
            UPDATE players
            SET relic = relic + $1
            WHERE user_id = $2;
        ''', kwargs['relic'], user.id)

    return None

@db_exception_handler
async def endrun(
    user: discord.User,
    *,
    conn: asyncpg.Connection | None = None
):
    if conn is None:
        raise RuntimeError("Database connection was not provided.")
    await conn.fetchrow('DELETE FROM runs WHERE user_id = $1', user.id)

    return None
