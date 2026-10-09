from discord.ext import commands
from core.ui.run_ui import RunConfirmationView, run_screen
from core.lib.run_lib import load_run
from core.lib import db


class Run(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @db.requires_player()
    async def run(self, ctx):
        run = await load_run(ctx.author)
        if run:
            embed, view = run_screen(ctx.author, run)
            await ctx.send(embed=embed, view=view)
        else:
            view = RunConfirmationView(ctx.author)
            view.message = await ctx.send("Start a run?", view=view)

async def setup(bot):
    await bot.add_cog(Run(bot))
