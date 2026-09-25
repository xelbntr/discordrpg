import discord
from core.lib import db
from core.data.classes import CLASSES

class ClassSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=c_name, description=c_info['description']) 
            for c_name, c_info in CLASSES.items()
        ]
        super().__init__(placeholder="Choose your class...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        data, db_error = await db.fetch(interaction.user, player=True)
        if db_error:
            await interaction.response.send_message("Unable to load your character. Please try again later.", ephemeral=True)
            return

        player = data['player']
        class_name = self.values[0]
        
        if player:
            await interaction.response.send_message(f"You already have a save file! Your current class is **{player['class']}**.", ephemeral=True)
            self.disabled = True
            await interaction.message.edit(view=self.view)
            self.view.stop()
            return
            
        inserted, create_error = await db.new_player(interaction.user, class_name)
        
        if create_error:
            await interaction.response.send_message("An error occurred while creating your save file.", ephemeral=True)
            return
            
        if not inserted:
             await interaction.response.send_message("You already have a save file!", ephemeral=True)
             self.disabled = True
             await interaction.message.edit(view=self.view)
             self.view.stop()
             return

        await interaction.response.send_message(f"Welcome to the game, {interaction.user.name}! Your character has been created with the **{class_name}** class. You can view your profile with `!profile`.")
        
        self.disabled = True
        await interaction.message.edit(view=self.view)
        self.view.stop()


class ClassSelectView(discord.ui.View):
    def __init__(self, original_user):
        super().__init__(timeout=180)
        self.original_user = original_user
        self.add_item(ClassSelect())

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.original_user:
            return False
        return True
