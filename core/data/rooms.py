from dataclasses import dataclass, field
from collections import defaultdict
from typing import Callable
from core.lib import roomgen
import discord
from core.ui import run_ui


@dataclass
class Room:
    floors: set[int]
    generate: Callable[..., None]
    view: type[discord.ui.View]
    weight: float = 1.0
    tags: set[str] = field(default_factory=set)

ROOMS: dict[str, Room] = {
    "battle": Room(
        floors={1, 2, 3, 4},
        generate=roomgen.gen_battle,
        view=run_ui.BattleView,
        weight=1.0,
        tags={"combat", "common", "danger"},
    ),
    "event": Room(
        floors={1, 2, 3, 4},
        generate=roomgen.gen_event,
        view=run_ui.EventView,
        weight=0.8,
        tags={"event", "common", "neutral"},
    ),
    "fountain": Room(
        floors={1, 2, 3, 4},
        generate=roomgen.gen_fountain,
        view=run_ui.FountainView,
        weight=0.5,
        tags={"event", "rare", "safe"},
    ),
    "market": Room(
        floors={2, 3, 4},
        generate=roomgen.gen_market,
        view=run_ui.MarketView,
        weight=0.4,
        tags={"shop", "rare", "safe"},
    ),
    "blacksmith": Room(
        floors={3, 4},
        generate=roomgen.gen_blacksmith,
        view=run_ui.BlacksmithView,
        weight=0.4,
        tags={"shop", "rare", "safe"},
    ),
    "cursed": Room(
        floors={3, 4},
        generate=roomgen.gen_cursed,
        view=run_ui.CursedView,
        weight=0.2,
        tags={"combat", "legendary", "danger"},
    ),
    "boss": Room(
        floors={1, 2, 3, 4},
        generate=roomgen.gen_boss,
        view=run_ui.BossView,
        weight=0,
        tags={"boss", "legendary", "danger"},
    ),
    "finalboss": Room(
        floors={4},
        generate=roomgen.gen_finalboss,
        view=run_ui.FinalbossView,
        weight=0,
        tags={"boss", "prismatic", "danger"},
    ),
    "basecamp": Room(
        floors={1, 2, 3, 4},
        generate=roomgen.gen_basecamp,
        view=run_ui.BasecampView,
        weight=0,
        tags={"event", "common", "safe"},
    ),
}

ROOMS_BY_FLOOR: dict[int, list[str]] = defaultdict(list)
for room, data in ROOMS.items():
    for floor in data.floors:
        ROOMS_BY_FLOOR[floor].append(room)
