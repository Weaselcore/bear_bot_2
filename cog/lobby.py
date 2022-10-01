import asyncio
from discord.ext import commands, tasks
from discord import Interaction, app_commands
import discord

from view.lobby.dropdown import DropdownView
from view.lobby.embeds import UpdateMessageEmbed
from model.lobby_model import (
    LobbyManager,
    LobbyModel,
)


class LobbyCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        print('LobbyCog loaded')

    @tasks.loop(count=1, reconnect=True)
    async def update_lobby_embed(self, lobby_id: int):
        """Updates the embed of the lobby message"""
        embed = LobbyManager.get_embed(self.bot, lobby_id)
        await embed.update()

    @update_lobby_embed.before_loop
    async def before_update_lobby_embed(self):
        await asyncio.sleep(5)

    @commands.Cog.listener()
    async def on_update_lobby_embed(self, lobby_id: int):
        """Updates the lobby embed"""
        if not self.update_lobby_embed.is_running():
            self.update_lobby_embed.start(lobby_id)

    @app_commands.command(description="Create lobby through UI", name='lobby')
    async def create_lobby(self, interaction: Interaction):
        """Creates a lobby through UI command"""
        exist = discord.utils.get(interaction.guild.channels, name='Lobbies')

        if not exist:
            print('Lobby Category Channel does not exist, creating one...')
            exist = await interaction.guild.create_category_channel('Lobbies')

        # Check if user has created a lobby previously.
        if interaction.user.id in self.bot.lobby.keys():
            await interaction.response.send_message(
                'You have already created a lobby!',
                ephemeral=True
            )
            return

        # Create new text channel
        channel = await interaction.guild.create_text_channel(
            name=f'{LobbyManager.get_lobby_name(self.bot)}',
            category=exist
        )

        # Create embed to redirect user to the new lobby channel
        await interaction.response.send_message(
            embed=discord.Embed(
                title=f'{interaction.user.name} created a lobby ✨',
                description=f'Click <#{channel.id}> to join the lobby',
                color=discord.Color.green()
            ),
        )
        control_panel = await channel.send('Initialising lobby...')
        # Create a new lobby model
        lobby_model = LobbyModel(
            control_panel=control_panel,
            owner=interaction.user,
            original_channel=interaction.channel,
            lobby_channel=channel
        )
        LobbyManager.set_lobby(self.bot, interaction.user.id, lobby_model)
        LobbyManager.add_member(interaction.client, interaction.user.id, interaction.user),
        # Create a custom view to hold logic, user id is used to have one instance per user
        view = DropdownView(lobby_id=interaction.user.id)
        # Message select dropdowns in the channel
        await control_panel.edit(view=view)

    @commands.Cog.listener()
    async def on_owner_leave(
        self,
        lobby_id: int,
        interaction: discord.Interaction,
    ):
        lobby_owner = LobbyManager.get_lobby_owner(self.bot, lobby_id)
        if interaction.user != lobby_owner:
            await interaction.response.defer()
            return
        count = LobbyManager.get_member_length(self.bot, lobby_id)
        if count == 1:
            channel = LobbyManager.get_original_channel(self.bot, lobby_id)
            await channel.send(
                embed=UpdateMessageEmbed(
                    title="Lobby Closed",
                    value=f"🛑 Lobby {interaction.channel.name} has been deleted.",
                    color=discord.Color.red()
                )
            )
            await LobbyManager.delete_lobby(self.bot, lobby_id)
        else:
            success = await LobbyManager.remove_owner(self.bot, lobby_id)
            if success:
                LobbyManager.get_lobby_owner(self.bot, lobby_id)
        interaction.client.dispatch('update_lobby_embed', lobby_id)
        await interaction.response.defer()


async def setup(bot):
    await bot.add_cog(LobbyCog(bot))


async def teardown(bot):
    await bot.remove_cog(LobbyCog(bot))
