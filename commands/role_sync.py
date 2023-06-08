from datetime import datetime, timedelta
import discord
from discord import app_commands, Interaction, Client, User
from discord.app_commands.errors import AppCommandError, CheckFailure
from config import Config
import yaml
import logging

from controllers.role_sync_controller import RoleSyncController

SYNC_SERVER_ID = int(Config.CONFIG["Discord"]["SyncServerID"])
CONFIG_DIR = "synced_servers"
LOG = logging.getLogger(__name__)


@app_commands.guild_only()
class RoleSyncCommands(app_commands.Group, name="role_sync"):
    def __init__(self, tree: app_commands.CommandTree, client: Client) -> None:
        super().__init__()
        self.tree = tree
        self.client = client

    def load_config(self, creator_name: str) -> dict:
        with open(f"{CONFIG_DIR}/{creator_name.lower()}.yaml", "r") as stream:
            return yaml.safe_load(stream)

    @app_commands.command(name="creator")
    @app_commands.checks.has_role("Mod")
    @app_commands.describe(
        creator_name="Name of creator as configured (case insensitive)"
    )
    async def creator(self, interaction: Interaction, creator_name: str):
        """Sync roles for a configured creator"""
        config = {}
        try:
            config = self.load_config(creator_name)
        except yaml.YAMLError as exc:
            return await interaction.response.send_message(
                f"Failed to read configuration for {creator_name}"
            )

        source_server_id = config["server_id"]
        roles = config["roles"]

        # Must completely process cleanups first in case
        # we must reapply a role based on a different config
        for role_config in roles:
            await RoleSyncController.cleanup_role_config(
                self.client, source_server_id, SYNC_SERVER_ID, role_config
            )

        for role_config in roles:
            await RoleSyncController.apply_role_config(
                self.client, source_server_id, SYNC_SERVER_ID, role_config
            )

        await interaction.response.send_message(f"Sync complete!")
