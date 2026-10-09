import discord

from core.lib.run_lib import (
    MAX_FLOORS, choose_card, complete_room, move_room, on_death,
    run_finished, start_run,
)
from core.ui.run_embed import MapSelectionEmbed


class RunConfirmationView(discord.ui.View):
    def __init__(self, original_user: discord.User | discord.Member):
        super().__init__(timeout=60)
        self.original_user = original_user
        self.message: discord.Message | None = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.original_user:
            await interaction.response.send_message("This run belongs to another player.", ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True
        if self.message:
            await self.message.edit(view=self)

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.green)
    async def confirm_run(self, interaction: discord.Interaction, _button: discord.ui.Button):
        await start_run(interaction, self)

    @discord.ui.button(label="No", style=discord.ButtonStyle.red)
    async def cancel_run(self, interaction: discord.Interaction, _button: discord.ui.Button):
        await interaction.response.edit_message(content="Run cancelled.", view=None)
        self.stop()


class BaseRoomView(discord.ui.View):
    def __init__(self, original_user: discord.User | discord.Member, run):
        super().__init__(timeout=None)
        self.original_user = original_user
        self.run = run

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.original_user:
            await interaction.response.send_message("This run belongs to another player.", ephemeral=True)
            return False
        if self.is_finished():
            await interaction.response.send_message("This screen has expired. Use `!run` to resume.", ephemeral=True)
            return False
        return True

    async def show_result(self, interaction: discord.Interaction, run):
        if run is not None:
            self.stop()
        await show_run(interaction, run)


class MapSelectionView(BaseRoomView):
    def __init__(self, original_user: discord.User | discord.Member, run, next_room: str):
        super().__init__(original_user, run)
        self.next_room = next_room
        if run['current_room'] == len(run['room_sequence']) - 1:
            self.next.label = "Next Floor"

    # --- DO NOT DELETE ---
    # in the future, there will be up to three room selections per block, and
    # it will have similar button generation mechanics to card selection view.
    # either that or I change both so that unused buttons just get disabled
    # instead of generating buttons per available room.

    @discord.ui.button(label="Move", style=discord.ButtonStyle.green)
    async def next(self, interaction: discord.Interaction, _button: discord.ui.Button):
        await interaction.response.defer()
        run = await move_room(self.original_user, self.run)
        await self.show_result(interaction, run)


class CardSelectionView(BaseRoomView):
    def __init__(self, original_user: discord.User | discord.Member, run):
        super().__init__(original_user, run)
        for idx, card in enumerate(dict.fromkeys(run['card_choices'])):
            button = discord.ui.Button(
                label=card, style=discord.ButtonStyle.primary, custom_id=f"take_card_{idx}",
            )
            button.callback = self.make_callback(card)
            self.add_item(button)

    def make_callback(self, card: str):
        async def card_callback(interaction: discord.Interaction):
            await interaction.response.defer()
            run = await choose_card(self.original_user, self.run, card)
            await self.show_result(interaction, run)
        return card_callback


class PlaceholderRoomView(BaseRoomView):
    xp_reward = 0

    @discord.ui.button(label="Complete Room", style=discord.ButtonStyle.green)
    async def complete(self, interaction: discord.Interaction, _button: discord.ui.Button):
        await interaction.response.defer()
        run = await complete_room(self.original_user, self.run, xp=self.xp_reward)
        await self.show_result(interaction, run)


class BasecampView(PlaceholderRoomView):
    pass


class BattleView(PlaceholderRoomView):
    xp_reward = 100


class EventView(PlaceholderRoomView):
    pass


class FountainView(PlaceholderRoomView):
    pass


class MarketView(PlaceholderRoomView):
    pass


class BlacksmithView(PlaceholderRoomView):
    pass


class CursedView(PlaceholderRoomView):
    pass


class BossView(PlaceholderRoomView):
    pass


class FinalbossView(PlaceholderRoomView):
    pass


class VictoryView(BaseRoomView):
    @discord.ui.button(label="Finish Run", style=discord.ButtonStyle.green)
    async def finish(self, interaction: discord.Interaction, _button: discord.ui.Button):
        await interaction.response.defer()
        if not await on_death(self.original_user, victory=True, state_id=self.run['state_id']):
            await interaction.followup.send("Unable to finish this run. Use `!run` to resume.", ephemeral=True)
            return
        await interaction.edit_original_response(content="Run complete! Use `!run` to start again.", embed=None, view=None)
        self.stop()


def run_screen(user: discord.User | discord.Member, run):
    from core.data.rooms import ROOMS

    if run['pending_levels']:
        level = run['pending_levels'][0]
        embed = discord.Embed(title=f"Level Up! (Level {level})", description="Choose a card:")
        return embed, CardSelectionView(user, run)

    if run_finished(run):
        embed = discord.Embed(
            title="Run Complete", description=f"You completed all {MAX_FLOORS} placeholder floors!",
            color=discord.Color.green(),
        )
        return embed, VictoryView(user, run)

    if run['room_completed']:
        next_index = run['current_room'] + 1
        next_room = run['room_sequence'][next_index] if next_index < len(run['room_sequence']) else "basecamp"
        embed = MapSelectionEmbed(run['current_floor'], run['room_sequence'], run['current_room'])
        if next_index == len(run['room_sequence']):
            embed.add_field(name="Next Floor", value=f"Floor {run['current_floor'] + 1}: Basecamp", inline=False)
        else:
            embed.add_field(name="Next Room", value=ROOMS[next_room].embed.room_title, inline=False)
        return embed, MapSelectionView(user, run, next_room)

    room = ROOMS[run['room_sequence'][run['current_room']]]
    return room.embed(run), room.view(user, run)


async def show_run(interaction: discord.Interaction, run) -> bool:
    if run is None:
        await interaction.followup.send("This screen has expired. Use `!run` to resume.", ephemeral=True)
        return False
    embed, view = run_screen(interaction.user, run)
    await interaction.edit_original_response(content=None, embed=embed, view=view)
    return True
