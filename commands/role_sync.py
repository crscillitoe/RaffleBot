from datetime import datetime, timedelta
from discord import app_commands, Interaction, Client, User
from discord.app_commands.errors import AppCommandError, CheckFailure
import yaml
import logging

from controllers.role_sync_controller import RoleSyncController

LOG = logging.getLogger(__name__)


@app_commands.guild_only()
class RoleSyncCommands(app_commands.Group, name="role_sync"):
    def __init__(self, tree: app_commands.CommandTree, client: Client) -> None:
        super().__init__()
        self.tree = tree
        self.client = client

    @app_commands.command(name="creator")
    @app_commands.checks.has_role("Mod")
    @app_commands.describe(
        creator_name="Name of creator as configured (case insensitive)"
    )
    async def creator(self, interaction: Interaction, creator_name: str):
        """Sync roles for a configured creator"""
        try:
            await RoleSyncController.sync_creator(creator_name, self.client)
        except yaml.YAMLError as exc:
            return await interaction.response.send_message(
                f"Failed to read configuration for {creator_name}"
            )

        await interaction.response.send_message(f"Sync complete!")
