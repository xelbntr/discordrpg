# use uv instead of pip/python
import os
from pathlib import Path
import discord
import asyncpg
from discord.ext import commands
from dotenv import load_dotenv
from core.lib import db

from core.lib.log import botlogger, dblogger
COGS_DIR = Path(__file__).resolve().parent / "cogs"


class Main(commands.Bot):
    def __init__(self, database_url: str | None = None):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
        self.database_url = database_url

    async def setup_hook(self):
        if not self.database_url:
            raise RuntimeError("Database URL is not set.")

        try:
            # noinspection PyTypeChecker
            db.dbpool = await asyncpg.create_pool(self.database_url, init=db.init_db)
            dblogger.info("Database pool created successfully.")
        except Exception as e:
            dblogger.exception(f"Failed to create database pool: {e}")
            raise

        try:
            for filename in sorted(os.listdir(COGS_DIR)):
                if filename.endswith(".py"):
                    await self.load_extension(f"cogs.{filename[:-3]}")
                    botlogger.info(f"Loaded cog: {filename[:-3]}")
        except Exception as e:
            botlogger.error(f"Error occurred while loading cogs: {e}")
            raise

    async def close(self):
        if db.dbpool:
            await db.dbpool.close()
        await super().close()

bot = Main()

@bot.event
async def on_ready():
    botlogger.info("────────────────────────────────")
    botlogger.info(f"> Logged in as {bot.user} (ID: {bot.user.id})")
    botlogger.info("────────────────────────────────")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    
    raise error

@bot.command(aliases=['r'])
@commands.is_owner()
async def reload(ctx):
    extension = "<unknown>"
    try:
        for filename in sorted(os.listdir(COGS_DIR)):
            if filename.endswith(".py"):
                extension = filename[:-3]
                await bot.reload_extension(f"cogs.{extension}")
                await ctx.send(f"Successfully reloaded `cogs.{extension}`.")
                botlogger.info(f"Successfully reloaded `cogs.{extension}`.")
    except Exception as e:
        await ctx.send(f"Error reloading extension `cogs.{extension}`. Check terminal for details.")
        botlogger.error(f"Error occurred while reloading extension: {e}")

def main():
    load_dotenv()
    token = os.getenv("DISCORD_TOKEN")
    database_url = os.getenv("DATABASE_URL")
    if not token:
        raise RuntimeError("Token is not set.")
    if not database_url:
        raise RuntimeError("Database URL is not set.")
    bot.database_url = database_url
    bot.run(token)


if __name__ == "__main__":
    main()
