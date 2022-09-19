import datetime
from discord.ext import commands
from discord import Interaction, app_commands
import discord

from view.lobby.button_view import OpenSlotButtonView, OwnerButtonView
from view.lobby.dropdown import DropdownView, NumberDropdown, OwnerSelectView
from view.lobby.modal import DescriptionModal
from model.lobby_model import (
    ClosedSlotEmbed,
    LobbyManager,
    LobbyModel,
    MemberState,
    OpenSlotEmbed,
    UpdateEmbed
)


class LobbyCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        print('LobbyCog loaded')

    # TODO: Use the discord utility find method.
    async def check_lobby_channel_exists(
        self,
        guild: discord.Guild
    ) -> discord.CategoryChannel | None:
        """Checks if the lobby channel exists in the guild"""
        channels = await guild.fetch_channels()
        for channel in channels:
            if channel.name == 'Lobbies':
                return channel
        return None

    @app_commands.command(description="Create lobby through UI", name='lobby')
    async def create_lobby(self, interaction: Interaction):
        """Creates a lobby through UI command"""
        exist = await self.check_lobby_channel_exists(interaction.guild)

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
            name='gametype-sizetype',
            category=exist
        )

        # Send a message to initiate a thread, it needs a [abc.snowflake] to
        # initiate a public thread
        thread_creation_message = await channel.send('Creating a history thread...')

        # Create new thread channel
        thread_channel = await channel.create_thread(
            name='Lobby History',
            message=thread_creation_message
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
            control_panel_message=control_panel,
            owner=interaction.user,
            original_channel=interaction.channel,
            lobby_channel=channel,
            thread=thread_channel,
        )
        LobbyManager.set_lobby(self.bot, interaction.user.id, lobby_model)
        # Create a custom view to hold logic, user id is used to have one instance per user
        view = DropdownView(bot=self.bot, id=interaction.user.id)
        # Message select dropdowns in the channel
        await control_panel.edit(view=view)

    @commands.Cog.listener()
    async def on_log_history(self, lobby_id: int, msg: str):
        """Event listener for when a loggable action occurs"""
        lobby_model = LobbyManager.get_lobby(self.bot, lobby_id)
        await lobby_model.thread.send(msg)

    @commands.Cog.listener()
    async def on_game_select(
        self,
        lobby_id: int,
        view: discord.ui.View,
        interaction: discord.Interaction
    ):
        """Event listener for when a game is selected"""
        if interaction.user == LobbyManager.get_lobby_owner(self.bot, lobby_id):
            # Save selected game code in state.
            lobby_model = LobbyManager.set_gamecode(
                self.bot,
                lobby_id,
                interaction.data['values'][0]
            )
            # Update history thread with game change
            self.bot.dispatch(
                'log_history',
                lobby_id,
                f'Game selected: {lobby_model.game_code}'
            )
            # Update view with [NumberDropdown]
            if lobby_model.game_code == 'VAL':
                number = 5
            elif lobby_model.game_code == 'ARK':
                number = 8
            elif lobby_model.game_code == 'LOL':
                number = 5
            else:
                number = 1

            if (len(view.children) != 1):
                # If the view already has a NumberDropdown for an updated one
                view.remove_item(view.children[1])

            view.children[0].placeholder = lobby_model.game_code
            view.add_item(NumberDropdown(lobby_id=lobby_id, bot=self.bot, number=number))
            lobby_model = LobbyManager.get_lobby(self.bot, lobby_id)
            # Edit game dropdown to reflect selected value
            await lobby_model.control_panel_message.edit(content="", view=view)

        else:
            self.bot.dispatch(
                "log_history",
                lobby_id,
                f'<@{interaction.user.id}>, only the owner can change the game.'
            )
        # Defer interaction update
        await interaction.response.defer()

    @commands.Cog.listener()
    async def on_number_select(
        self,
        lobby_id: int,
        view: DropdownView,
        interaction: Interaction
    ):
        """Event listener for when a lobby is ready"""
        await interaction.response.defer()
        if interaction.user == LobbyManager.get_lobby_owner(self.bot, lobby_id):
            lobby_model = LobbyManager.set_gamesize(
                self.bot,
                lobby_id,
                interaction.data['values'][0]
            )
            # Update history thread with size change
            self.bot.dispatch(
                'log_history',
                lobby_id,
                f'Game size selected: {lobby_model.game_size}'
            )
            channel = lobby_model.lobby_channel
            # Edit channel name
            await channel.edit(
                name=LobbyManager.get_lobby_name(self.bot, lobby_id)
            )
            lobby_model = LobbyManager.get_lobby(self.bot, lobby_id)
            view.children[1].placeholder = interaction.data['values'][0]
            await lobby_model.control_panel_message.edit(
                content="",
                view=view
            )
            lobby_model = LobbyManager.get_lobby(self.bot, lobby_id)
            # Resize lobby size if it's been initialised already
            if len(lobby_model.embeds) != 0:
                await LobbyManager.resize_lobby(self.bot, lobby_id)
                return
            # Fill owner slot
            if lobby_model.lobby_channel:
                # Create owner embed
                embed = ClosedSlotEmbed(
                    member=lobby_model.owner,
                    datetime=datetime.datetime.now()
                )
                # Create owner button view
                view = OwnerButtonView(
                    bot=self.bot,
                    lobby_id=lobby_id,
                )
                # Send owner embed and view
                owner_embed_message = await lobby_model.lobby_channel.send(
                    embed=embed,
                    view=view
                )
                # Store owner as member
                LobbyManager.add_slot(self.bot, lobby_id, embed, 0, owner_embed_message)
                LobbyManager.add_member(self.bot, lobby_id, lobby_model.owner, 0)
                # Populate channel with open slots
                for x in range(int(lobby_model.game_size) - 1):
                    embed = OpenSlotEmbed(index=x + 1)
                    message = await lobby_model.lobby_channel.send(
                        embed=embed,
                        view=OpenSlotButtonView(
                            index=x + 1,
                            lobby_id=lobby_model.owner.id,
                            bot=self.bot
                        )
                    )
                    LobbyManager.add_slot(self.bot, lobby_id, embed, x + 1, message)
        else:
            self.bot.dispatch(
                "log_history",
                lobby_id,
                f'<@{interaction.user.id}>, only the owner can change the game.'
            )

    @commands.Cog.listener()
    async def on_member_ready(
        self,
        lobby_id: int,
        index: int,
        view: discord,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        """Event listener for when a member is ready"""
        member = LobbyManager.get_member(self.bot, lobby_id, index)
        lobby_owner = LobbyManager.get_lobby_owner(self.bot, lobby_id)

        if interaction.user == member or interaction.user == lobby_owner:
            # Update button when owner clicks
            if button.label == "Ready":
                button.label = "Not Ready"
                button.style = discord.ButtonStyle.red
                member_state = MemberState.READY
            else:
                button.label = "Ready"
                button.style = discord.ButtonStyle.green
                member_state = MemberState.NOT_READY
            await interaction.response.edit_message(view=view)
            # Update embed to reflect change
            LobbyManager.update_member_state(self.bot, lobby_id, member, member_state, index)
            await LobbyManager.update_embed(self.bot, lobby_id, index)
        else:
            self.bot.dispatch(
                'log_history',
                lobby_id,
                f'<@{interaction.user.id}>, only the leader or \
                the respective user can click this button.'
            )
            await interaction.response.defer()

    @commands.Cog.listener()
    async def on_lobby_lock(
        self,
        lobby_id: int,
        view: discord.ui.View,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        lobby_owner = LobbyManager.get_lobby_owner(self.bot, lobby_id)
        if interaction.user != lobby_owner:
            self.bot.dispatch(
                "log_history",
                lobby_id,
                f'<@{interaction.user.id}>, only the leader can click this button.'
            )
            await interaction.response.defer()
            return
        msg = ""
        if button.label == "Lock":
            button.label = "Unlock"
            button.style = discord.ButtonStyle.green
            msg = f"@{interaction.user.name} locked the lobby"
        else:
            button.label = "Lock"
            button.style = discord.ButtonStyle.red
            msg = f"{interaction.user.name} unlocked the lobby"
        await interaction.response.edit_message(view=view)
        self.bot.dispatch(
            "log_history",
            lobby_id,
            msg
        )
        await LobbyManager.lock(self.bot, lobby_id)

    @commands.Cog.listener()
    async def on_lobby_join(
        self,
        index: int,
        lobby_id: int,
        interaction: discord.Interaction,
    ):
        lobby_owner = LobbyManager.get_lobby_owner(self.bot, lobby_id)
        if interaction.user == lobby_owner:
            # Search for a new owner and replace the owner
            success = await LobbyManager.search_new_owner(self.bot, lobby_id)
            if not success:
                self.bot.dispatch(
                    "log_history",
                    lobby_id,
                    f"<@{interaction.user.id}>, No members have been found to \
                    replace the owner."
                )
        elif LobbyManager.has_joined(self.bot, lobby_id, interaction.user):
            self.bot.dispatch(
                "log_history",
                lobby_id,
                f"<@{interaction.user.id}>, you are already in this lobby."
            )
        else:
            # If not owner, add member to the lobby
            await LobbyManager.fill_open_embed(
                bot=self.bot,
                lobby_id=lobby_id,
                index=index,
                member=interaction.user
            )
            channel = LobbyManager.get_original_channel(self.bot, lobby_id)
            member_count = LobbyManager.get_member_length(self.bot, lobby_id)
            game_size = LobbyManager.get_gamesize(self.bot, lobby_id)
            descriptor = LobbyManager.get_descriptor(self.bot, lobby_id)
            await channel.send(
                embed=UpdateEmbed(
                    title="Lobby Update",
                    value=f"<@{interaction.user.id}> has joined \
                    <#{interaction.channel.id}> lobby 🏃",
                    descriptor=descriptor,
                    color=discord.Color.green(),
                    footer=(f"{member_count} slots out of {game_size}")
                )
            )
        await interaction.response.defer()

    @commands.Cog.listener()
    async def on_lobby_leave(
        self,
        index: int,
        lobby_id: int,
        interaction: discord.Interaction,
    ):
        lobby_owner = LobbyManager.get_lobby_owner(self.bot, lobby_id)
        if interaction.user == lobby_owner:
            await LobbyManager.clear_closed_embed(
                bot=self.bot,
                lobby_id=lobby_id,
                index=index
            )
        else:
            self.bot.dispatch(
                "log_history",
                lobby_id,
                f'<@{interaction.user.id}>, only the \
                respective user or leader can click this button.'
            )
        await interaction.response.defer()

    @commands.Cog.listener()
    async def on_owner_leave(
        self,
        lobby_id: int,
        interaction: discord.Interaction,
    ):
        lobby_owner = LobbyManager.get_lobby_owner(self.bot, lobby_id)
        if interaction.user != lobby_owner:
            self.bot.dispatch(
                "log_history",
                lobby_id,
                f'<@{interaction.user.id}>, only the leader can click this button.'
            )
            await interaction.response.defer()
            return
        count = LobbyManager.get_member_length(self.bot, lobby_id)
        if count == 1:
            channel = LobbyManager.get_original_channel(self.bot, lobby_id)
            await channel.send(
                embed=UpdateEmbed(
                    title="Lobby Closed",
                    value=f"🛑 Lobby {interaction.channel.name} has been deleted.",
                    color=discord.Color.red()
                )
            )
            await LobbyManager.delete_lobby(self.bot, lobby_id)
        else:
            success = await LobbyManager.remove_owner(self.bot, lobby_id)
            if success:
                owner = LobbyManager.get_lobby_owner(self.bot, lobby_id)
                self.bot.dispatch(
                    "log_history",
                    lobby_id,
                    f"<@{owner.id}> is now the owner"
                )
        await interaction.response.defer()

    @commands.Cog.listener()
    async def on_change_leader_press(
        self,
        lobby_id: int,
        interaction: discord.Interaction
    ):
        lobby_owner = LobbyManager.get_lobby_owner(self.bot, lobby_id)
        if interaction.user != lobby_owner:
            self.bot.dispatch(
                "log_history",
                lobby_id,
                f'<@{interaction.user.id}>, only the leader can click this button.'
            )
            await interaction.response.defer()
        else:
            list_of_users = []
            for index, embed_model in self.bot.lobby[lobby_id].embeds.items():
                if embed_model.member_model is not None:
                    list_of_users.append((embed_model.member_model.member, int(index)))
            await interaction.response.send_message(
                view=OwnerSelectView(
                    self.bot,
                    lobby_id,
                    list_of_users
                ),
                ephemeral=True,
            )

    @commands.Cog.listener()
    async def on_owner_select(
        self,
        lobby_id: int,
        index: int,
        interaction: discord.Interaction,
    ):
        lobby_owner = LobbyManager.get_lobby_owner(self.bot, lobby_id)
        if interaction.user != lobby_owner:
            await LobbyManager.switch_owner(self.bot, lobby_id, index)
            owner = LobbyManager.get_lobby_owner(self.bot, lobby_id)
            self.bot.dispatch(
                "log_history",
                lobby_id,
                f"<@{owner.name}> is now the owner"
            )
        await interaction.response.defer()

    @commands.Cog.listener()
    async def on_descriptor_change(
        self,
        lobby_id: int,
        string: str,
    ):
        descriptor = string
        LobbyManager.set_descriptor(self.bot, lobby_id, descriptor)
        lobby_channel = LobbyManager.get_channel(self.bot, lobby_id)
        await lobby_channel.edit(topic=descriptor)

    @commands.Cog.listener()
    async def on_descriptor_click(
        self,
        lobby_id: int,
        interaction: discord.Interaction,
    ):
        lobby_owner = LobbyManager.get_lobby_owner(self.bot, lobby_id)
        if interaction.user != lobby_owner:
            self.bot.dispatch(
                "log_history",
                lobby_id,
                f'<@{interaction.user.id}>, only the leader can click this button.'
            )
            await interaction.response.defer()
        else:
            await interaction.response.send_modal(
                DescriptionModal(self.bot, lobby_id),
            )


async def setup(bot):
    await bot.add_cog(LobbyCog(bot))


async def teardown(bot):
    await bot.remove_cog(LobbyCog(bot))
