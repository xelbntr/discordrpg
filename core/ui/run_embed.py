from collections.abc import Iterable, Mapping
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
        # Copying also supports asyncpg.Record without modifying live run data.
        data = dict(run)
        super().__init__(
            title=self.room_title,
            description=(details or self.room_description)[:4096],
            color=self.room_color,
        )
        for key, label in (("hp", "HP"), ("run_level", "Level"), ("xp", "XP")):
            if data.get(key) is not None:
                self.add_field(name=label, value=str(data[key])[:1024])
        if data.get("current_room") is not None:
            self.set_footer(text=f"Room {data['current_room'] + 1}")
        if monster is not None:
            enemy = dict(monster)
            text = str(enemy.get("name", "Unknown monster"))
            if enemy.get("hp") is not None:
                text += f"\nHP: {enemy['hp']}"
            self.add_field(name="Monster", value=text[:1024], inline=False)
        if inventory is not None:
            items = "\n".join(str(item) for item in inventory)
            self.add_field(name="Inventory", value=items[:1024] or "Empty", inline=False)


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


class BasecampEmbed(BaseRoomEmbed):
    room_title = "Basecamp"
    room_description = "You rest at the basecamp."
    room_color = discord.Color.green()
