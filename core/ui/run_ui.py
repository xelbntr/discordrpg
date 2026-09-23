import discord

from core.lib import db
from core.lib.run import *
from core.lib.log import dblogger

class RunConfirmationView(discord.ui.View):
    def __init__(self, original_user):
        super().__init__(timeout=60)
        self.original_user = original_user
        self.message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.original_user:
            return False
        return True

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            await self.message.edit(view=self)

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.green)
    async def confirm_run(self, interaction: discord.Interaction, button: discord.ui.Button):
        run, db_error = await db.startrun(interaction.user, 0)

        if db_error:
            await interaction.response.send_message("Error starting run.", ephemeral=True)
            return

        if run is None:
            # Fallback if startrun failed (e.g. run already exists)
            context, db_error = await db.fetch_player_context(interaction.user, run=True)
            run = context['run'] if not db_error else None
            if db_error or run is None:
                dblogger.error(f"Unable to start run for {interaction.user.id}. run output:\n{run}")
                await interaction.response.edit_message(content="Error starting run. Do you have a character?", view=None)
                self.stop()
                return

        main_run_embed = discord.Embed(
            title="Run",
            description="[Placeholder main run embed]"
        )

        view = BasecampView(self.original_user)
        await interaction.response.edit_message(content=None, embed=main_run_embed, view=view)
        self.stop()

    @discord.ui.button(label="No", style=discord.ButtonStyle.red)
    async def cancel_run(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="Run cancelled.", view=None, ephemeral=True)
        self.stop()


class BaseRoomView(discord.ui.View):
    def __init__(self, original_user):
        super().__init__(timeout=None)
        self.original_user = original_user
        self.message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.original_user:
            return False
        return True


class CardSelectionView(BaseRoomView):
    def __init__(self, original_user, cards: list[str], remaining_levels: list[int]):
        super().__init__(original_user)
        self.cards = cards
        self.remaining_levels = remaining_levels

        for idx, card in enumerate(cards):
            btn = discord.ui.Button(label=f"{card}", style=discord.ButtonStyle.primary, custom_id=f"take_card_{idx}")
            btn.callback = self.make_callback(card)
            self.add_item(btn)

    def make_callback(self, card_name: str):
        async def card_callback(interaction: discord.Interaction):
            # await db.update_cards(user=self.original_user, card=card_name)
            # (function not implemented in db.py yet)

            if self.remaining_levels:
                next_level = self.remaining_levels.pop(0)
                next_cards = await generate_card(user=self.original_user, level=next_level)
                
                view = CardSelectionView(self.original_user, next_cards, self.remaining_levels)
                embed = discord.Embed(title=f"Level Up! (Level {next_level})", description="Choose a card:")
                await interaction.response.edit_message(embed=embed, view=view)
            else:
                # 3. No more level ups, proceed to the next room (Basecamp)
                view = BasecampView(self.original_user)
                embed = discord.Embed(title="Basecamp", description="You rest at the basecamp.")
                await interaction.response.edit_message(embed=embed, view=view)
                
        return card_callback


class BasecampView(BaseRoomView):
    pass


class BattleView(BaseRoomView):
    @discord.ui.button(label="Next", style=discord.ButtonStyle.green)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        context, db_error = await db.fetch_player_context(self.original_user, run=True)
        run = context['run'] if not db_error else None
        if db_error or not run:
            await interaction.response.send_message("Error fetching run data.", ephemeral=True)
            return

        current_level = run['run_level']
        
        level_increment, xp = await on_gain_xp(user=self.original_user, xp=100) # temp placeholder xp
        await db.update(user=self.original_user, xp=xp, levelup=level_increment)
        if level_increment > 0:
            levels_to_process = [current_level + i + 1 for i in range(level_increment)]
            
            first_level = levels_to_process.pop(0)
            cards = await generate_card(user=self.original_user, level=first_level)
            
            view = CardSelectionView(self.original_user, cards, levels_to_process)
            embed = discord.Embed(title=f"Level Up! (Level {first_level})", description="Choose a card:")
            await interaction.response.edit_message(embed=embed, view=view)
        else:
            # move to next room; this is placeholder
            view = BasecampView(self.original_user)
            embed = discord.Embed(title="Basecamp", description="You rest at the basecamp.")
            await interaction.response.edit_message(embed=embed, view=view)



class EventView(BaseRoomView):
    pass


class FountainView(BaseRoomView):
    pass


class MarketView(BaseRoomView):
    pass


class BlacksmithView(BaseRoomView):
    pass


class CursedView(BaseRoomView):
    pass


class BossView(BaseRoomView):
    pass


class FinalbossView(BaseRoomView):
    pass
