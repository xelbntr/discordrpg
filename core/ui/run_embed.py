from collections.abc import Iterable, Mapping
from pydoc import describe
from typing import Any

import discord


class BaseRoomEmbed(discord.Embed):
    room_title = "Room"
    room_description = ""
    room_color = discord.Color.blue()

    def __init__(
        self,
        run: Mapping[str, Any],
        *,
        details: str | None = None,
        monster: Mapping[str, Any] | None = None,
        inventory: Iterable[str] | None = None,
    ):
        super().__init__(
            title=self.room_title,
            description=(details or self.room_description)[:4096],
            color=self.room_color,
        )


class MapViewEmbed(discord.Embed):
    def __init__(self, rooms: list[str], current_room: int):
        super().__init__(
            title="Map",
            description="Choose a room to move to.",
        )

        for pos, room in enumerate(rooms, start=1):
            if pos == current_room:
                self.add_field(value=f"**[{pos}] {room} <<<**")
            else:
                self.add_field(value=f"[{pos}] {room}")


class BasecampEmbed(BaseRoomEmbed):
    room_title = "Basecamp"
    room_description = "You rest at the basecamp."
    room_color = discord.Color.green()


class BattleEmbed(BaseRoomEmbed):
    room_title = "Battle"
    room_description = "Prepare to fight."
    room_color = discord.Color.red()


class EventEmbed(BaseRoomEmbed):
    room_title = "Event"
    room_description = "An encounter awaits."


class FountainEmbed(BaseRoomEmbed):
    room_title = "Fountain"
    room_description = "You discover a fountain."
    room_color = discord.Color.green()


class MarketEmbed(BaseRoomEmbed):
    room_title = "Market"
    room_description = "Browse the market's wares."
    room_color = discord.Color.gold()


class BlacksmithEmbed(BaseRoomEmbed):
    room_title = "Blacksmith"
    room_description = "Visit the blacksmith to improve your equipment."
    room_color = discord.Color.gold()


class CursedEmbed(BaseRoomEmbed):
    room_title = "Cursed Room"
    room_description = "A dangerous presence fills the room."
    room_color = discord.Color.purple()


class BossEmbed(BattleEmbed):
    room_title = "Boss"
    room_description = "The floor's boss awaits."


class FinalbossEmbed(BossEmbed):
    room_title = "Final Boss"
    room_description = "Your final challenge awaits."

