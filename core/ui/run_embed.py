from collections.abc import Mapping
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
    ):
        super().__init__(
            title=self.room_title,
            description=(details or self.room_description)[:4096],
            color=self.room_color,
        )
        self.add_field(name="HP", value=str(run["hp"]))
        self.add_field(name="XP", value=str(run["xp"]))


class MapSelectionEmbed(discord.Embed):
    def __init__(
            self,
            floor: int,
            rooms: list[str],
            current_room: int
    ):
        super().__init__(
            title="Map",
            description=f"Floor {floor}",
            color=discord.Color.gold()
        )

        for pos, room in enumerate(rooms):
            if pos == current_room:
                self.add_field(name=f"Room {pos + 1}", value=f"**[{pos + 1}] {room} <<<**")
            else:
                self.add_field(name=f"Room {pos + 1}", value=f"[{pos + 1}] {room}")


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
