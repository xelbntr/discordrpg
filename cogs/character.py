import discord
from discord.ext import commands
from core.lib import db
from core.data.classes import CLASSES
from core.ui.class_select import ClassSelectView


class Character(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def start(self, ctx):
        player, db_error = await db.fetch_player(ctx.author)
        if db_error:
            await ctx.send("Unable to load your character. Please try again later.")
            return

        if player:
            await ctx.send(f"You already have a save file! Your current class is **{player['class']}**.")
            return

        available_classes = "\n".join([f"**{c_name}**: {c_info['description']}" for c_name, c_info in CLASSES.items()])
        welcome_msg = f"Welcome to Discord RPG! Choose your class. This choice is permanent! \n\nAvailable classes:\n{available_classes}\n\n"
        
        view = ClassSelectView(ctx.author)
        await ctx.send(welcome_msg, view=view)

    @commands.command()
    @db.requires_player()
    async def profile(self, ctx):
        player = ctx.player
        class_name = player['class']
        class_info = CLASSES.get(class_name, {})
        passive_name = class_info.get("base_passive", {}).get("name", "Unknown")
        passive_desc = class_info.get("base_passive", {}).get("description", "Unknown")

        embed = discord.Embed(title=f"{ctx.author.name}'s Profile", color=discord.Color.blue())
        embed.add_field(name="Class", value=class_name, inline=True)
        embed.add_field(name="Rank", value=str(player['rank']), inline=True)
        embed.add_field(name="Base Passive", value=f"**{passive_name}**: {passive_desc}", inline=False)
        
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Character(bot))
