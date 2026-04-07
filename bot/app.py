import os

import discord
from discord.ext import tasks

from bot.commands import changelogs, faq, features, keys, scripts
from bot.views.script_card_view import ScriptCardView
from db import cleanup_expired_keys, get_db_health, init_db


class HubBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.tree = discord.app_commands.CommandTree(self)
        self.pending_previews = {}

    async def setup_hook(self):
        self.add_view(ScriptCardView())

        keys.register(self.tree)
        scripts.register(self.tree, self)
        changelogs.register(self.tree, self)
        faq.register(self.tree, self)
        features.register(self.tree, self)

        synced = await self.tree.sync()
        print(f"Synced {len(synced)} slash commands")

    async def on_ready(self):
        print(f"Bot logged in as {self.user}")

        try:
            health = get_db_health()
            print(f"Database connection OK: {health}")
        except Exception as exc:
            print(f"Database health check failed: {repr(exc)}")

        try:
            init_db()
            print("Database initialized")
        except Exception as exc:
            print(f"Database init failed: {repr(exc)}")

        if not cleanup_loop.is_running():
            cleanup_loop.start()


bot = HubBot()


@tasks.loop(hours=1)
async def cleanup_loop():
    try:
        deleted = cleanup_expired_keys()
        if deleted:
            print(f"Cleaned {deleted} expired keys")
    except Exception as exc:
        print(f"Cleanup error: {repr(exc)}")


@cleanup_loop.before_loop
async def before_cleanup_loop():
    await bot.wait_until_ready()


def main():
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_TOKEN is missing")

    try:
        health = get_db_health()
        print(f"Startup DB connection OK: {health}")
    except Exception as exc:
        print(f"Startup database check failed: {repr(exc)}")

    try:
        init_db()
        print("Database initialized at startup")
    except Exception as exc:
        print(f"Startup database init failed: {repr(exc)}")

    bot.run(token)
