from __future__ import annotations
import asyncio
import logging
import discord
from discord import (
    Member,
    app_commands,
    Client,
    Intents,
)
from commands.mod_commands import ModCommands
from commands.role_sync import RoleSyncCommands
from config import Config
from controllers.role_sync_controller import RoleSyncController
from db import DB


discord.utils.setup_logging(level=logging.INFO, root=True)


class RaffleBot(Client):
    def __init__(self):
        intents = Intents.default()
        intents.members = True
        intents.message_content = True
        intents.guilds = True

        # initialize DB for the first time
        DB()

        super().__init__(intents=intents)

    async def on_ready(self):
        logging.info(f"Logged in as {self.user} (ID: {self.user.id})")
        if Config.CONFIG["Discord"]["AutoSyncEnabled"].lower() == "true":
            logging.info("Starting role auto sync...")
            RoleSyncController(self).sync_all_creators.start()


client = RaffleBot()
tree = app_commands.CommandTree(client)


@client.event
async def on_guild_join(guild):
    tree.clear_commands(guild=guild)
    tree.copy_global_to(guild=guild)
    await tree.sync(guild=guild)


async def main():
    async with client:
        tree.add_command(ModCommands(tree, client))
        tree.add_command(RoleSyncCommands(tree, client))
        await client.start(Config.CONFIG["Discord"]["Token"])


if __name__ == "__main__":
    asyncio.run(main())
