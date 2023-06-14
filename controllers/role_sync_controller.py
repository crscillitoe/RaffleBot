import asyncio
import yaml
import discord
from discord import Client, Guild, Member, NotFound, Role
from discord.ext import tasks
from config import Config
import logging
from os import listdir
from os.path import isfile, join

LOG = logging.getLogger(__name__)
SYNC_SERVER_ID = int(Config.CONFIG["Discord"]["SyncServerID"])
CONFIG_DIR = "synced_servers"


class RoleSyncController:
    def __init__(self, client: Client):
        self.client = client

    @staticmethod
    async def _assign_role(
        dest_guild: Guild,
        source_member: Member,
        source_role: Role,
        dest_role: Role,
    ):
        try:
            # Only assign to users that have the configured source role
            if discord.utils.get(source_member.roles, id=source_role.id) is None:
                return
            dest_member = await dest_guild.fetch_member(source_member.id)
            # Do not reassign a role that the user already has - this is slow
            if discord.utils.get(dest_member.roles, id=dest_role.id) is not None:
                LOG.debug(f"Role already assigned! Continuing...")
                return
            await dest_member.add_roles(dest_role)
            # Rate limit
            await asyncio.sleep(1)
        except NotFound:
            LOG.warn(
                f"Could not find member with id {source_member.id} to assign role to"
            )
            return

    @staticmethod
    async def _remove_role(member: Member, role: Role):
        await member.remove_roles(role)

    @staticmethod
    async def _cleanup_roles(
        source_guild: Guild,
        dest_member: Member,
        source_role: Role,
        dest_role: Role,
    ):
        # Only cleanup users that have the configured role
        if discord.utils.get(dest_member.roles, id=dest_role.id) is None:
            return
        try:
            source_member = await source_guild.fetch_member(dest_member.id)
            # Only cleanup users that DO NOT have the required role in the source server anymore
            if discord.utils.get(source_member.roles, id=source_role.id) is not None:
                LOG.debug(
                    "User still has required role in source server. Continuing..."
                )
                return
            await dest_member.remove_roles(dest_role)
        except NotFound:
            LOG.warn(
                f"Could not find member with id {dest_member.id} in source server during cleanup. Removing destination role..."
            )
            await dest_member.remove_roles(dest_role)

    @staticmethod
    async def _cleanup_role_config(
        client: Client, source_server_id: str, dest_server_id: str, role_config: dict
    ):
        source_role_id = int(role_config["sourceServerRole"])
        dest_role_id = int(role_config["destServerRole"])

        source_guild = await client.fetch_guild(source_server_id)
        source_role = source_guild.get_role(source_role_id)

        dest_guild = await client.fetch_guild(dest_server_id)
        dest_guild_members = dest_guild.fetch_members(limit=None)
        dest_role = dest_guild.get_role(dest_role_id)

        # Cleanup destination roles from users who have had their
        # source roles removed since last sync
        async for dest_member in dest_guild_members:
            await RoleSyncController._cleanup_roles(
                source_guild, dest_member, source_role, dest_role
            )

    @staticmethod
    async def _apply_role_config(
        client: Client, source_server_id: str, dest_server_id: str, role_config: dict
    ):
        source_role_id = int(role_config["sourceServerRole"])
        dest_role_id = int(role_config["destServerRole"])

        source_guild = await client.fetch_guild(source_server_id)
        source_guild_members = source_guild.fetch_members(limit=None)
        source_role = source_guild.get_role(source_role_id)

        dest_guild = await client.fetch_guild(dest_server_id)
        dest_role = dest_guild.get_role(dest_role_id)

        # Add roles to destination server if user has one of the
        # configured source roles
        async for source_member in source_guild_members:
            await RoleSyncController._assign_role(
                dest_guild,
                source_member,
                source_role,
                dest_role,
            )

    @staticmethod
    def _load_creator_config(creator_name: str) -> dict:
        return RoleSyncController._load_config(
            f"{CONFIG_DIR}/{creator_name.lower()}.yaml"
        )

    @staticmethod
    def _load_config(config_file_path: str) -> dict:
        with open(config_file_path, "r") as stream:
            return yaml.safe_load(stream)

    @staticmethod
    async def _sync_from_creator_config(config: dict, client: Client):
        source_server_id = config["server_id"]
        roles = config["roles"]

        # Must completely process cleanups first in case
        # we must reapply a role based on a different config
        for role_config in roles:
            await RoleSyncController._cleanup_role_config(
                client, source_server_id, SYNC_SERVER_ID, role_config
            )

        for role_config in roles:
            await RoleSyncController._apply_role_config(
                client, source_server_id, SYNC_SERVER_ID, role_config
            )

    @staticmethod
    async def sync_creator(creator_name: str, client: Client):
        """Sync roles for a configured creator"""
        config = RoleSyncController._load_creator_config(creator_name)
        await RoleSyncController._sync_from_creator_config(config, client)

    @tasks.loop(minutes=1)
    async def sync_all_creators(self):
        LOG.debug("Syncing all creators...")
        all_creator_files = [
            f"{CONFIG_DIR}/{f}"
            for f in listdir(CONFIG_DIR)
            if isfile(join(CONFIG_DIR, f))
        ]
        for config_file in all_creator_files:
            # Ignore example config file that comes with repo
            if config_file == f"{CONFIG_DIR}/example.yaml":
                continue
            config = RoleSyncController._load_config(config_file)
            asyncio.get_event_loop().create_task(
                RoleSyncController._sync_from_creator_config(config, self.client)
            )
