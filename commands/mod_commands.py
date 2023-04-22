from datetime import datetime, timedelta
from discord import app_commands, Interaction, Client, User
from discord.app_commands.errors import AppCommandError, CheckFailure
from db import DB, RaffleType
from views.raffle.new_raffle_modal import NewRaffleModal
from controllers.raffle_controller import RaffleController
import logging


@app_commands.guild_only()
class ModCommands(app_commands.Group, name="mod"):
    def __init__(self, tree: app_commands.CommandTree, client: Client) -> None:
        super().__init__()
        self.tree = tree
        self.client = client

    async def on_error(self, interaction: Interaction, error: AppCommandError):
        if isinstance(error, CheckFailure):
            return await interaction.response.send_message(
                "Failed to perform command - please verify permissions.", ephemeral=True
            )
        logging.error(error)
        return await super().on_error(interaction, error)

    @app_commands.command(name="sync")
    @app_commands.checks.has_role("Mod")
    async def sync(self, interaction: Interaction) -> None:
        """Manually sync slash commands to guild"""

        guild = interaction.guild
        self.tree.clear_commands(guild=guild)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
        await interaction.response.send_message("Commands synced", ephemeral=True)

    @app_commands.command(name="start")
    @app_commands.checks.has_role("Mod")
    @app_commands.describe(raffle_type="Raffle Type (default: normal)")
    async def start(
        self, interaction: Interaction, raffle_type: RaffleType = RaffleType.normal
    ):
        """Starts a new raffle"""

        if DB().has_ongoing_raffle(interaction.guild.id):
            await interaction.response.send_message(
                "There is already an ongoing raffle!"
            )
            return

        modal = NewRaffleModal(raffle_type=raffle_type)
        await interaction.response.send_modal(modal)

    @app_commands.command(name="end")
    @app_commands.checks.has_role("Mod")
    async def end(
        self,
        interaction: Interaction,
        num_winners: int = 1,
    ) -> None:
        """Closes an existing raffle and pick the winner(s)"""

        if not DB().has_ongoing_raffle(interaction.guild.id):
            await interaction.response.send_message(
                "There is no ongoing raffle! You need to start a new one."
            )
            return

        raffle_message_id = DB().get_raffle_message_id(interaction.guild.id)
        if raffle_message_id is None:
            await interaction.response.send_message(
                "Oops! That raffle does not exist anymore."
            )
            return

        await RaffleController._end_raffle_impl(
            interaction, raffle_message_id, num_winners
        )
        DB().close_raffle(interaction.guild.id, end_time=datetime.now())

    @app_commands.command(name="remove_raffle_winner")
    @app_commands.checks.has_role("Mod")
    @app_commands.describe(user="User ID to remove win from")
    async def remove_raffle_winner(self, interaction: Interaction, user: User):
        """Deletes recent raffle win for user"""
        one_week_ago = datetime.now().date() - timedelta(days=6)

        if not DB().remove_raffle_winner(interaction.guild_id, user.id, one_week_ago):
            await interaction.response.send_message(
                "This user has not recently won a raffle!"
            )
            return

        await interaction.response.send_message("Winner removed!")
