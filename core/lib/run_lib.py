import random

import math

import asyncpg
import discord

from core.lib import db
from core.lib.db import GearTier
from core.lib.log import dblogger
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

async def generate_rooms(
        user: discord.User | discord.Member,
        rank: int,
        floor: int,
        *,
        state_id,
):
    from core.data.rooms import ROOMS_BY_FLOOR, ROOMS

    if not 1 <= floor <= MAX_FLOORS:
        raise ValueError(f"Invalid floor: {floor}")

    candidates = [room for room in ROOMS_BY_FLOOR[floor] if ROOMS[room].weight > 0]
    rooms = []
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
        rooms.append(chosen_room)

    return await db.update_run_state(
        user, state_id,
        current_floor=floor, current_room=0, room_sequence=rooms,
        room_completed=False, pending_levels=[], card_choices=[],
    )

async def load_run(user: discord.User | discord.Member):
    data = await db.fetch(user, run=True)
    run = data['run']
    if run and not run['room_sequence']:
        generated_run = await generate_rooms(
            user, run['rank_snapshot'], run['current_floor'], state_id=run['state_id'],
        )
        if generated_run is None:
            data = await db.fetch(user, run=True)
            return data['run']
        run = generated_run
    return run

async def start_run(
    interaction: discord.Interaction,
    confirmation_view: discord.ui.View,
    hp: int = 100,
) -> None:
    await interaction.response.defer()
    run = await db.create_run(interaction.user, hp)

    if run is None:
        run = await load_run(interaction.user)
        if run is None:
            dblogger.error(f"Unable to start run for {interaction.user.id}. run output:\n{run}")
            await interaction.edit_original_response(content="Error starting run.", view=None)
            confirmation_view.stop()
            return

    if not run['room_sequence']:
        run = await generate_rooms(
            interaction.user, run['rank_snapshot'], 1, state_id=run['state_id'],
        )
        if run is None:
            run = await load_run(interaction.user)

    from core.ui.run_ui import show_run

    await show_run(interaction, run)
    confirmation_view.stop()

async def complete_room(user, run, xp: int = 0):
    if run['room_completed']:
        return None

    level_increment, remaining_xp = on_gain_xp(run, xp)
    levels = list(range(run['run_level'] + 1, run['run_level'] + level_increment + 1))
    cards = generate_card(levels[0]) if levels else []
    return await db.update_run_state(
        user, run['state_id'], xp=remaining_xp,
        run_level=run['run_level'] + level_increment,
        room_completed=True, pending_levels=levels, card_choices=cards,
    )

async def choose_card(user, run, card: str):
    if not run['pending_levels'] or card not in run['card_choices']:
        return None

    remaining_levels = list(run['pending_levels'][1:])
    next_cards = generate_card(remaining_levels[0]) if remaining_levels else []
    return await db.update_run_state(
        user, run['state_id'], deck=list(run['deck'] or []) + [card],
        pending_levels=remaining_levels, card_choices=next_cards,
    )

async def move_room(user, run):
    if not run['room_completed'] or run['pending_levels']:
        return None

    next_index = run['current_room'] + 1
    if next_index < len(run['room_sequence']):
        return await db.update_run_state(
            user, run['state_id'], current_room=next_index, room_completed=False,
        )
    if run['current_floor'] < MAX_FLOORS:
        return await generate_rooms(
            user, run['rank_snapshot'], run['current_floor'] + 1,
            state_id=run['state_id'],
        )
    return None

def run_finished(run) -> bool:
    return (
        run['room_completed'] and not run['pending_levels']
        and run['current_floor'] == MAX_FLOORS
        and run['current_room'] == len(run['room_sequence']) - 1
    )


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
            available_cards = list(CARDS_BY_RARITY[rolled_rarity])
        if not available_cards:
            catalog = [card for pool in CARDS_BY_RARITY.values() for card in pool]
            available_cards = [card for card in catalog if card not in cards] or catalog
        if not available_cards:
            raise ValueError("No cards are available for rewards.")
            
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

async def on_death(user: discord.User | discord.Member, victory: bool, state_id=None) -> bool:
    # Equipment must be read before deleting the run and its inventory.
    data = await db.fetch(user, player=True, equipment=True)
    if data['player'] is None:
        dblogger.error(f"Unable to kill player: Could not load player. Userid {user.id}")
        return False

    equipment = data['equipment']

    ended_run = await db.endrun(user, state_id=state_id)
    if ended_run is None:
        return False

    relic_gained = 0
    for gear in equipment.values():
        # relic gained = gear tier * 50 base val
        # temporary; may change over time
        relic_gained += int((gear['tier'] * 50) * (1.2 if victory else 0.7))
        
    if relic_gained > 0:
        await db.update(user, relic=relic_gained)
    return True
