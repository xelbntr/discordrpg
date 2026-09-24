import asyncpg
import json
import inspect
from functools import wraps
from core.lib.log import dblogger
import discord
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
    async def wrapper(user: discord.User, *args, **kwargs):
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
async def fetch_player_context(
    user: discord.User,
    *,
    player: bool = False,
    equipment: bool = False,
    run: bool = False,
    conn: asyncpg.Connection | None = None
):
    """Return (context, db_error), fetching only requested keys in one connection.

    Missing player/run rows are None; missing equipment is an empty dict.
    """
    if conn is None:
        raise RuntimeError("Database connection was not provided.")

    context = {}
    if player:
        context['player'] = await conn.fetchrow(
            'SELECT * FROM players WHERE user_id = $1', user.id
        )
    if equipment:
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
        context['equipment'] = {record['slot']: record for record in records}
    if run:
        context['run'] = await conn.fetchrow(
            'SELECT * FROM runs WHERE user_id = $1', user.id
        )
    return context

def with_player_context(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # check if the user object exists
        user: discord.User | discord.Member | None = kwargs.get('user')
        ctx_or_interaction = None
        if not user:
            for arg in args:
                if isinstance(arg, (discord.User, discord.Member)):
                    user = arg
                    break
                elif hasattr(arg, 'author') and isinstance(getattr(arg, 'author'), (discord.User, discord.Member)):
                    user = arg.author
                    ctx_or_interaction = arg
                    break
                elif hasattr(arg, 'user') and isinstance(getattr(arg, 'user'), (discord.User, discord.Member)):
                    user = arg.user
                    ctx_or_interaction = arg
                    break
                    
        if not user:
            # fallback if user object doesnt exist
            return await func(*args, **kwargs) if inspect.iscoroutinefunction(func) else func(*args, **kwargs)

        sig = inspect.signature(func)
        needs_user = 'user' in sig.parameters
        needs_player = 'player' in sig.parameters
        needs_gear = 'equipment' in sig.parameters
        needs_class = 'class_name' in sig.parameters
        needs_run = 'run' in sig.parameters
        
        async def send_error(msg):
            if ctx_or_interaction:
                if hasattr(ctx_or_interaction, 'send'):
                    await ctx_or_interaction.send(msg)
                elif hasattr(ctx_or_interaction, 'response') and hasattr(ctx_or_interaction.response, 'send_message'):
                    if not ctx_or_interaction.response.is_done():
                        await ctx_or_interaction.response.send_message(msg, ephemeral=True) 

        context = {}
        if needs_player or needs_class or needs_gear or needs_run:
            context, db_error = await fetch_player_context(
                user,
                player=needs_player or needs_class,
                equipment=needs_gear,
                run=needs_run,
            )
            if db_error:
                dblogger.exception(f"Error fetching player context for user {user.id}")
                await send_error("An error occurred while accessing the database. Please try again later.")
                return None

        player = context.get('player')
        equipment = context.get('equipment')
        run = context.get('run')

        inject = {}
        if needs_user:
            inject['user'] = user
        if needs_player: 
            inject['player'] = player
        if needs_gear: 
            inject['equipment'] = equipment
        if needs_class:
            inject['class_name'] = player['class'] if player else None
        if needs_run:
            inject['run'] = run
            
        final_kwargs = {**inject, **kwargs}
        
        if inspect.iscoroutinefunction(func):
            return await func(*args, **final_kwargs)
        return func(*args, **final_kwargs)
        
    return wrapper

@db_exception_handler
async def update(
    user: discord.User,
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
async def startrun(
    user: discord.User,
    hp: int,
    *,
    conn: asyncpg.Connection | None = None
):
    if conn is None:
        raise RuntimeError("Database connection was not provided.")
    response = await conn.fetchrow('''
        INSERT INTO runs (user_id, hp, rank_snapshot)
        SELECT $1, $2, rank
        FROM players
        WHERE user_id = $1
        ON CONFLICT (user_id) DO NOTHING
        RETURNING *;
    ''', user.id, hp)
    return response

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
