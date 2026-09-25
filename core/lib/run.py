import random

import math

import asyncpg
import discord

from core.data.rooms import ROOMS_BY_FLOOR, ROOMS
from core.lib import db
from core.lib.db import GearTier
from core.lib.log import dblogger, botlogger
from core.data.cards import CARDS_BY_RARITY

CARD_DROPRATE: dict[int, list[int]] = {
    0: [80, 19, 1, 0],
    1: [55, 38, 7, 0],
    2: [35, 50, 14, 1],
    3: [20, 50, 25, 5],
}

CARD_GUARANTEED: dict[int, GearTier] = {
    0: GearTier.rare,
    1: GearTier.rare,
    2: GearTier.legendary,
    3: GearTier.legendary,
}

RARITIES: list[GearTier] = [GearTier.common, GearTier.rare, GearTier.legendary, GearTier.prismatic_i]

ROOMS_PER_FLOOR = 6
MAX_FLOORS = 4

@db.db_exception_handler
async def _create_run(
    user: discord.User | discord.Member,
    hp: int,
    *,
    conn: asyncpg.Connection | None = None,
):
    if conn is None:
        raise RuntimeError("Database connection was not provided.")
    return await conn.fetchrow('''
        INSERT INTO runs (user_id, hp, rank_snapshot)
        SELECT $1, $2, rank
        FROM players
        WHERE user_id = $1
        ON CONFLICT (user_id) DO NOTHING
        RETURNING *;
    ''', user.id, hp)

async def generate_rooms(
        user: discord.User | discord.Member,
        rank: int,
        floor: int,
) -> bool:
    candidates = ROOMS_BY_FLOOR[floor]
    run, dberror = await db.fetch_run(user=user)

    if dberror:
        botlogger.error(f"Unable to generate room due to a database issue.")
        return False

    if floor > 1:
        if not await db.reset_floor(user=user):
            botlogger.error(f"Unable to reset floor due to a database issue.")
            return False

    for i in range(ROOMS_PER_FLOOR):
        if i == 0:
            chosen_room = "basecamp"
        elif i == ROOMS_PER_FLOOR-1:
            if floor == MAX_FLOORS:
                chosen_room = "finalboss"
            else:
                chosen_room = "boss"
        else:
            chosen_room = random.choices(candidates, weights=[ROOMS[room].weight for room in candidates], k=1)[0]
        await db.update(user=user, room=chosen_room)

    return True

async def start_run(
    interaction: discord.Interaction,
    confirmation_view: discord.ui.View,
    hp: int = 100,
) -> None:
    run, db_error = await _create_run(interaction.user, hp)

    if db_error:
        await interaction.response.send_message("Error starting run.", ephemeral=True)
        return

    if run is None:
        # Fallback if creation returned no row (e.g. run already exists)
        run, db_error = await db.fetch_run(interaction.user)
        if db_error or run is None:
            dblogger.error(f"Unable to start run for {interaction.user.id}. run output:\n{run}")
            await interaction.response.edit_message(content="Error starting run.", view=None)
            confirmation_view.stop()
            return

    from core.data.rooms import ROOMS

    room_name = run["room_sequence"][run["current_room"]]
    room = ROOMS[room_name]
    main_run_embed = room.embed(run)
    view = room.view(interaction.user)
    await interaction.response.edit_message(content=None, embed=main_run_embed, view=view)
    confirmation_view.stop()


def generate_card(level: int) -> list[str]:
    pulls: int = 2

    # Level 1–4: 80% Common, 19% Rare, 1% Legendary
    # Level 5–9: 55% Common, 38% Rare, 7% Legendary
    # Level 10–14: 35% Common, 50% Rare, 14% Legendary, 1% Prismatic I
    # Level 15+: 20% Common, 50% Rare, 25% Legendary, 5% Prismatic I
    # Level 0 and 5 guarantees a rare card, level 10 and 15 guarantees a legendary
    cards: list[str] = []
    
    for x in range(pulls):
        bracket: int = min(level // 5, 3)
        if level % 5 == 0:
            rolled_rarity: GearTier = CARD_GUARANTEED[bracket]
        else:
            rolled_rarity: GearTier = random.choices(RARITIES, weights=CARD_DROPRATE[bracket])[0]
            
        available_cards: list[str] = [c for c in CARDS_BY_RARITY[rolled_rarity] if c not in cards]
        if not available_cards:
            available_cards = CARDS_BY_RARITY[rolled_rarity]
            
        cards.append(random.choice(available_cards))

    return cards

def on_gain_xp(run: asyncpg.Record, xp: int) -> tuple[int, int]:
    temp_xp: float = run['xp'] + xp
    level: int = run['run_level']
    xp_threshold: float = 100 * 1.25**(level-1)
    level_increment: int = 0

    while temp_xp >= xp_threshold:
        level_increment += 1
        curr_level: int = level+level_increment

        temp_xp -= xp_threshold
        xp_threshold = 100 * 1.25**(curr_level - 1)

    return level_increment, math.floor(temp_xp)

async def on_death(user: discord.User | discord.Member, victory: bool) -> bool:
    player, db_error = await db.fetch_player(user)
    if db_error or player is None:
        dblogger.error(f"Unable to kill player: Could not load player. Userid {user.id}")
        return False

    # Equipment must be read before deleting the run and its inventory.
    equipment, db_error = await db.fetch_equipment(user)
    if db_error:
        dblogger.error(f"Unable to kill player: Could not load equipment. Userid {user.id}")
        return False

    _, db_error = await db.endrun(user)

    if db_error:
        dblogger.error(f"Unable to kill player: Failed to update user database on death. Userid {user.id}.")
        return False

    relic_gained = 0
    for gear in equipment.values():
        # relic gained = gear tier * 50 base val
        # temporary; may change over time
        relic_gained += int((gear['tier'] * 50) * (1.2 if victory else 0.7))
        
    if relic_gained > 0:
        _, db_error = await db.update(user, relic=relic_gained)
        if db_error:
            return False

    return True
