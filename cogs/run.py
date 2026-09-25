from discord.ext import commands
from core.ui.run_ui import RunConfirmationView, BaseRoomView
from core.data.rooms import ROOMS
from core.lib import db


class Run(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @db.requires_player()
    async def run(self, ctx):
        run, db_error = await db.fetch_run(ctx.author)
        if db_error:
            await ctx.send("Error fetching run data. Please try again later.")
            return

        if run:
            room_name = run["room_sequence"][run["current_room"]]
            main_run_embed = ROOMS[room_name].embed(run)
            main_run_view: type[BaseRoomView] = ROOMS[room_name].view

            view: BaseRoomView = main_run_view(ctx.author)
            view.message = await ctx.send(embed=main_run_embed, view=view, ephemeral=True)
        else:
            view = RunConfirmationView(ctx.author)
            view.message = await ctx.send("Start a run?", view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Run(bot))
