import discord
from discord import Client, Guild, Member, NotFound, Role
import logging

LOG = logging.getLogger(__name__)


class RoleSyncController:
    @staticmethod
    async def assign_role(
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
        except NotFound:
            LOG.warn(
                f"Could not find member with id {source_member.id} to assign role to"
            )
            return

    @staticmethod
    async def remove_role(member: Member, role: Role):
        await member.remove_roles(role)

    @staticmethod
    async def cleanup_roles(
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
    async def cleanup_role_config(
        client: Client, source_server_id: str, dest_server_id: str, role_config: dict
    ):
        source_role_id = int(role_config["sourceServerRole"])
        dest_role_id = int(role_config["destServerRole"])

        source_guild = await client.fetch_guild(source_server_id)
        source_guild_members = source_guild.fetch_members(limit=None)
        source_role = source_guild.get_role(source_role_id)

        dest_guild = await client.fetch_guild(dest_server_id)
        dest_guild_members = dest_guild.fetch_members(limit=None)
        dest_role = dest_guild.get_role(dest_role_id)

        # Cleanup destination roles from users who have had their
        # source roles removed since last sync
        async for dest_member in dest_guild_members:
            await RoleSyncController.cleanup_roles(
                source_guild, dest_member, source_role, dest_role
            )

    @staticmethod
    async def apply_role_config(
        client: Client, source_server_id: str, dest_server_id: str, role_config: dict
    ):
        source_role_id = int(role_config["sourceServerRole"])
        dest_role_id = int(role_config["destServerRole"])

        source_guild = await client.fetch_guild(source_server_id)
        source_guild_members = source_guild.fetch_members(limit=None)
        source_role = source_guild.get_role(source_role_id)

        dest_guild = await client.fetch_guild(dest_server_id)
        dest_guild_members = dest_guild.fetch_members(limit=None)
        dest_role = dest_guild.get_role(dest_role_id)

        # Add roles to destination server if user has one of the
        # configured source roles
        async for source_member in source_guild_members:
            await RoleSyncController.assign_role(
                dest_guild,
                source_member,
                source_role,
                dest_role,
            )
