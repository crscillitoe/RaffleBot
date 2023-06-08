from datetime import datetime, timedelta
import discord
from discord import app_commands, Interaction, Client, User
from discord.app_commands.errors import AppCommandError, CheckFailure
from config import Config
import yaml
import logging

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

        creator_server = config["server_id"]
        roles = config["roles"]
        for role_config in roles:
            source_role_id = int(role_config["sourceServerRole"])
            dest_role_id = int(role_config["destServerRole"])

            source_guild = await self.client.fetch_guild(creator_server)
            source_guild_members = source_guild.fetch_members(limit=None)

            dest_guild = await self.client.fetch_guild(SYNC_SERVER_ID)
            dest_server_role = dest_guild.get_role(dest_role_id)

            async for member in source_guild_members:
                # Only assign to users that have the configured source role
                if discord.utils.get(member.roles, id=source_role_id) is None:
                    continue
                dest_member = await dest_guild.fetch_member(member.id)
                if dest_member is None:
                    LOG.warn(f"Could not find member with id {member.id}")
                    continue
                # Do not reassign a role that the user already has - this is slow
                if discord.utils.get(dest_member.roles, id=dest_role_id) is not None:
                    LOG.debug(f"Role already assigned! Continuing...")
                    continue
                await dest_member.add_roles(dest_server_role)
        await interaction.response.send_message(f"Sync complete!")
