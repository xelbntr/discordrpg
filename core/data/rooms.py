from dataclasses import dataclass, field
from collections import defaultdict
from typing import Callable
from core.ui import run_embed, run_ui


@dataclass
class Room:
    floors: set[int]
    view: type[run_ui.BaseRoomView]
    embed: type[run_embed.BaseRoomEmbed]
    # Room content generators are not implemented yet. Keep the registry
    # independent of the selector so importing extensions remains safe.
    generate: Callable[..., None] | None = None
    weight: float = 1.0
    tags: set[str] = field(default_factory=set)

ROOMS: dict[str, Room] = {
    "battle": Room(
        floors={1, 2, 3, 4},
        view=run_ui.BattleView,
        embed=run_embed.BattleEmbed,
        weight=1.0,
        tags={"combat", "common", "danger"},
    ),
    "event": Room(
        floors={1, 2, 3, 4},
        view=run_ui.EventView,
        embed=run_embed.EventEmbed,
        weight=0.8,
        tags={"event", "common", "neutral"},
    ),
    "fountain": Room(
        floors={1, 2, 3, 4},
        view=run_ui.FountainView,
        embed=run_embed.FountainEmbed,
        weight=0.5,
        tags={"event", "rare", "safe"},
    ),
    "market": Room(
        floors={2, 3, 4},
        view=run_ui.MarketView,
        embed=run_embed.MarketEmbed,
        weight=0.4,
        tags={"shop", "rare", "safe"},
    ),
    "blacksmith": Room(
        floors={3, 4},
        view=run_ui.BlacksmithView,
        embed=run_embed.BlacksmithEmbed,
        weight=0.4,
        tags={"shop", "rare", "safe"},
    ),
    "cursed": Room(
        floors={3, 4},
        view=run_ui.CursedView,
        embed=run_embed.CursedEmbed,
        weight=0.2,
        tags={"combat", "legendary", "danger"},
    ),
    "boss": Room(
        floors={1, 2, 3, 4},
        view=run_ui.BossView,
        embed=run_embed.BossEmbed,
        weight=0,
        tags={"boss", "legendary", "danger"},
    ),
    "finalboss": Room(
        floors={4},
        view=run_ui.FinalbossView,
        embed=run_embed.FinalbossEmbed,
        weight=0,
        tags={"boss", "prismatic", "danger"},
    ),
    "basecamp": Room(
        floors={1, 2, 3, 4},
        view=run_ui.BasecampView,
        embed=run_embed.BasecampEmbed,
        weight=0,
        tags={"event", "common", "safe"},
    ),
}

ROOMS_BY_FLOOR: dict[int, list[str]] = defaultdict(list)
for room, data in ROOMS.items():
    for floor in data.floors:
        ROOMS_BY_FLOOR[floor].append(room)
