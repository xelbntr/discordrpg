from email import message

import discord

from core.lib import db
from core.lib.log import botlogger
from core.lib.run_lib import generate_card, on_gain_xp, start_run

class RunConfirmationView(discord.ui.View):
    def __init__(self, original_user: discord.User | discord.Member):
        super().__init__(timeout=60)
        self.original_user = original_user
        self.message: discord.Message | None = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.original_user:
            return False
        return True

    async def on_timeout(self):
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True
        if self.message:
            await self.message.edit(view=self)

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.green)
    async def confirm_run(self: "RunConfirmationView", interaction: discord.Interaction, _button: discord.ui.Button):
        await start_run(interaction, self)

    @discord.ui.button(label="No", style=discord.ButtonStyle.red)
    async def cancel_run(self: "RunConfirmationView", interaction: discord.Interaction, _button: discord.ui.Button):
        await interaction.response.edit_message(content="Run cancelled.", view=None)
        self.stop()


class BaseRoomView(discord.ui.View):
    def __init__(self, original_user: discord.User | discord.Member):
        super().__init__(timeout=None)
        self.original_user = original_user
        self.message: discord.Message | None = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.original_user:
            return False
        return True


class CardSelectionView(BaseRoomView):
    def __init__(self, original_user: discord.User | discord.Member, cards: list[str], remaining_levels: list[int]):
        super().__init__(original_user)
        self.cards = cards
        self.remaining_levels = remaining_levels

        for idx, card in enumerate(cards):
            btn = discord.ui.Button(label=f"{card}", style=discord.ButtonStyle.primary, custom_id=f"take_card_{idx}")
            btn.callback = self.make_callback(card)
            self.add_item(btn)

    def make_callback(self, card: str):
        async def card_callback(interaction: discord.Interaction):
            _, dberror = await db.update(user=self.original_user, deck=card)

            if dberror:
                botlogger.error("Failed to claim new card due to database error.")
                embed = discord.Embed(description="Failed to claim new card due to database error.")
                await interaction.response.edit_message(embed=embed)
                return

            if self.remaining_levels:
                next_level = self.remaining_levels[0]
                next_cards = generate_card(level=next_level)
                self.remaining_levels.pop(0)
                
                view: BaseRoomView = CardSelectionView(self.original_user, next_cards, self.remaining_levels)
                embed = discord.Embed(title=f"Level Up! (Level {next_level})", description="Choose a card:")
                await interaction.response.edit_message(embed=embed, view=view)
            else:
                # 3. No more level ups, proceed to the next room (Basecamp)
                data, db_error = await db.fetch(self.original_user, run=True)
                if db_error or not data['run']:
                    await interaction.response.send_message("Error fetching run data.", ephemeral=True)
                    return
                from core.data.rooms import ROOMS

                run = data['run']
                room = ROOMS["basecamp"]
                view = room.view(self.original_user)
                embed = room.embed(run)
                await interaction.response.edit_message(embed=embed, view=view)
                
        return card_callback


class BasecampView(BaseRoomView):
    pass


class BattleView(BaseRoomView):
    @discord.ui.button(label="Next", style=discord.ButtonStyle.green)
    async def next(self: "BattleView", interaction: discord.Interaction, _button: discord.ui.Button):
        data, db_error = await db.fetch(self.original_user, run=True)
        if db_error or not data['run']:
            await interaction.response.send_message("Error fetching run data.", ephemeral=True)
            return

        run = data['run']
        current_level = run['run_level']
        
        level_increment, xp = on_gain_xp(run, xp=100) # temp placeholder xp
        _, db_error = await db.update(user=self.original_user, xp=xp, levelup=level_increment)
        if db_error:
            await interaction.response.send_message("Error updating run data.", ephemeral=True)
            return
        if level_increment > 0:
            levels_to_process = [current_level + i + 1 for i in range(level_increment)]
            
            first_level = levels_to_process.pop(0)
            cards = generate_card(level=first_level)
            
            view: BaseRoomView = CardSelectionView(self.original_user, cards, levels_to_process)
            embed = discord.Embed(title=f"Level Up! (Level {first_level})", description="Choose a card:")
            await interaction.response.edit_message(embed=embed, view=view)
        else:
            # move to next room; this is placeholder
            next_room_name = run["room_sequence"][run["current_room"]]
            from core.data.rooms import ROOMS

            room = ROOMS[next_room_name]
            view = room.view(self.original_user)
            updated_run = dict(run)
            updated_run.update(xp=xp, run_level=current_level + level_increment)
            embed = room.embed(updated_run)
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
