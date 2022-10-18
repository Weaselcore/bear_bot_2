from typing import Any, cast
import discord
from model.lobby.game_model import GameManager, GameModel
from discord.ui import Button, View, Modal, TextInput, Select
from discord import Interaction, SelectOption

from model.lobby.lobby_model import LobbyManager, LobbyState, MemberState
from view.lobby.embeds import UpdateEmbedManager, UpdateEmbedType


class DescriptionModal(Modal):
    def __init__(self, lobby_id: int):
        super().__init__(title='Edit Description')
        self.lobby_id = lobby_id

    answer: TextInput[Any] = TextInput(
        label='Edit Description',
        style=discord.TextStyle.paragraph,
        max_length=50
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        LobbyManager.set_descriptor(
            interaction.client, self.lobby_id, self.answer.value)
        # Send update embed
        thread = LobbyManager.get_thread(interaction.client, self.lobby_id)
        message_details = UpdateEmbedManager.get_message_details(
            interaction.client,
            self.lobby_id,
            UpdateEmbedType.DESCRIPTION_CHANGE,
            interaction.user
        )
        await thread.send(
            content=message_details[0],
            embed=message_details[1]
        )
        interaction.client.dispatch('update_lobby_embed', self.lobby_id)


class ConfirmationModal(discord.ui.Modal):
    def __init__(self, lobby_id: int):
        super().__init__(title='Are you sure? Reason optional.')
        self.lobby_id = lobby_id

    reason: TextInput[Any] = TextInput(
        label='Reason',
        max_length=150,
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        channel = LobbyManager.get_original_channel(
            interaction.client, self.lobby_id)

        message_details = UpdateEmbedManager.get_message_details(
            interaction.client,
            self.lobby_id,
            UpdateEmbedType.DELETE,
            interaction.user
        )

        embed = message_details[1]

        if self.reason.value:
            embed.add_field(
                name='Reason:',
                value=self.reason.value,
                inline=False
            )

        await LobbyManager.delete_lobby(interaction.client, self.lobby_id)
        await channel.send(
            content=message_details[0],
            embed=embed
        )


class OwnerSelectView(View):
    def __init__(
        self,
        lobby_id: int,
        list_of_users: list[tuple[str, int]]
    ):
        super().__init__()
        self.list_of_users = list_of_users
        self.add_item(
            self.OwnerDropdown(lobby_id, list_of_users)
        )

    class OwnerDropdown(Select[Any]):
        def __init__(
            self,
            lobby_id: int,
            list_of_users: list[tuple[str, int]]
        ):
            options = []

            for user in list_of_users:
                options.append(SelectOption(
                    label=user[0],
                    value=str(user[1])
                ))

            super().__init__(
                placeholder='Choose new owner...',
                min_values=1,
                max_values=1,
                options=options
            )
            self.lobby_id = lobby_id

        async def callback(self, interaction: Interaction) -> None:
            lobby_owner = LobbyManager.get_lobby_owner(
                interaction.client, self.lobby_id)
            if interaction.user == lobby_owner:
                if interaction.guild is None:
                    raise Exception('Guild is None')
                member = interaction.guild.get_member(int(self.values[0]))
                LobbyManager.switch_owner(
                    interaction.client,
                    self.lobby_id,
                    member)
                LobbyManager.get_lobby_owner(interaction.client, self.lobby_id)
                interaction.client.dispatch(
                    'update_lobby_embed', self.lobby_id)
            await interaction.response.defer()
            original_channel = LobbyManager.get_original_channel(
                interaction.client, self.lobby_id)
            # Disable view after selection
            view = cast(OwnerSelectView, self.view)
            view.stop()

            message_detail = UpdateEmbedManager.get_message_details(
                interaction.client,
                self.lobby_id,
                UpdateEmbedType.OWNER_CHANGE,
                interaction.user
            )

            await original_channel.send(
                content=message_detail[0],
                embed=message_detail[1]
            )


class ButtonView(discord.ui.View):
    def __init__(
        self,
        lobby_id: int
    ):
        super().__init__(timeout=None)
        self.lobby_id = lobby_id

    @discord.ui.button(label='Join', style=discord.ButtonStyle.green)
    async def join_button(self, interaction: Interaction, _: Button[Any]) -> None:
        # Check if the member has already joined
        if LobbyManager.has_joined(interaction.client, self.lobby_id, interaction.user):
            await interaction.response.defer()
            return

        LobbyManager.add_member(
            interaction.client, self.lobby_id, interaction.user)
        thread = LobbyManager.get_thread(interaction.client, self.lobby_id)

        message_details = UpdateEmbedManager.get_message_details(
            interaction.client,
            self.lobby_id,
            UpdateEmbedType.JOIN,
            interaction.user
        )

        await thread.send(
            content=message_details[0],
            embed=message_details[1]
        )

        interaction.client.dispatch('update_lobby_embed', self.lobby_id)
        await interaction.response.defer()

    @discord.ui.button(label="Ready", style=discord.ButtonStyle.green)
    async def ready(self, interaction: Interaction, button: Button[Any]) -> None:

        # Reject interaction if user is not in lobby
        has_joined = LobbyManager.has_joined(
            interaction.client, self.lobby_id, interaction.user)
        if not has_joined:
            # Defer interaction update
            await interaction.response.defer()
            return

        # Reject interaction if lobby is locked
        lobby_state = LobbyManager.get_lobby_lock(
            interaction.client, self.lobby_id)
        if lobby_state == LobbyState.LOCK:
            # Defer interaction update
            await interaction.response.defer()
            return

        # Update member state
        member_state = LobbyManager.update_member_state(
            interaction.client,
            self.lobby_id,
            interaction.user
        )

        # Update button
        number_filled = len(LobbyManager.get_members_ready(
            interaction.client, self.lobby_id))
        button.label = f"Ready: {number_filled}"
        await interaction.response.edit_message(view=self)

        # Update lobby embed
        interaction.client.dispatch('update_lobby_embed', self.lobby_id)

        # Send update message
        thread = LobbyManager.get_thread(interaction.client, self.lobby_id)

        # Send update message when member readies up
        if member_state == MemberState.READY:
            message_details = UpdateEmbedManager.get_message_details(
                interaction.client,
                self.lobby_id,
                UpdateEmbedType.READY,
                interaction.user
            )

            await thread.send(
                content=message_details[0],
                embed=message_details[1]
            )
        await interaction.response.defer()

    @discord.ui.button(label="Leave", style=discord.ButtonStyle.red)
    async def leave(self, interaction: discord.Interaction, _: Button[Any]) -> None:
        # Check if user is in lobby
        if not LobbyManager.has_joined(interaction.client, self.lobby_id, interaction.user):
            await interaction.response.defer()
            return

        embed_type = None
        lobby_owner = LobbyManager.get_lobby_owner(
            interaction.client, self.lobby_id)
        original_channel = LobbyManager.get_original_channel(
            interaction.client, self.lobby_id)

        # Delete lobby if there is 1 person left
        if LobbyManager.get_member_length(interaction.client, self.lobby_id) == 1:
            interaction.client.dispatch("stop_promote_lobby", self.lobby_id)
            message_details = UpdateEmbedManager.get_message_details(
                interaction.client,
                self.lobby_id,
                UpdateEmbedType.DELETE,
                interaction.user
            )
            await original_channel.send(
                content=message_details[0],
                embed=message_details[1]
            )
            await LobbyManager.delete_lobby(interaction.client, self.lobby_id)
            return
        # Remove member from lobby
        elif interaction.user != lobby_owner:
            LobbyManager.remove_member(
                interaction.client, self.lobby_id, interaction.user)
            embed_type = UpdateEmbedType.LEAVE
        # Remove user and find new leader
        elif interaction.user == lobby_owner:
            LobbyManager.remove_owner(interaction.client, self.lobby_id)
            embed_type = UpdateEmbedType.OWNER_CHANGE

        # Update Ready button
        number_filled = len(LobbyManager.get_members_ready(interaction.client, self.lobby_id))
        self.ready.label = f"Ready: {number_filled}"
        await interaction.response.edit_message(view=self)

        message_details = UpdateEmbedManager.get_message_details(
            interaction.client,
            self.lobby_id,
            embed_type,
            interaction.user
        )

        await original_channel.send(
            content=message_details[0],
            embed=message_details[1]
        )
        # Update lobby embed
        interaction.client.dispatch('update_lobby_embed', self.lobby_id)

    @discord.ui.button(label="Lock", style=discord.ButtonStyle.danger)
    async def lock(self, interaction: Interaction, button: Button[Any]) -> None:

        # Reject interaction if user is not lobby owner
        lobby_owner = LobbyManager.get_lobby_owner(
            interaction.client, self.lobby_id)
        if interaction.user != lobby_owner:
            # Defer interaction update
            await interaction.response.defer()
            return

        # Reject interaction if all members are not ready
        member_ready = len(LobbyManager.get_members_ready(
            interaction.client, self.lobby_id))
        game_size = int(LobbyManager.get_gamesize(
            interaction.client, self.lobby_id))
        if member_ready < game_size:
            # Defer interaction update
            await interaction.response.defer()
            return

        # Update button
        if button.label == "Lock":
            button.label = "Unlock"
        else:
            button.label = "Lock"
        await interaction.response.edit_message(view=self)

        # Update lobby state
        lobby_status = LobbyManager.lock(interaction.client, self.lobby_id)

        status = None
        # Send update message
        if lobby_status == LobbyState.LOCK:
            status = UpdateEmbedType.LOCK
        elif lobby_status == LobbyState.UNLOCK:
            status = UpdateEmbedType.UNLOCK
        # Update lobby embed
        interaction.client.dispatch('update_lobby_embed', self.lobby_id)
        # Send update message
        if status:
            original_channel = LobbyManager.get_original_channel(
                interaction.client, self.lobby_id)
            message_details = UpdateEmbedManager.get_message_details(
                interaction.client,
                self.lobby_id,
                status,
                interaction.user
            )
            await original_channel.send(
                content=message_details[0],
                embed=message_details[1]
            )

    @discord.ui.button(label="Change Leader", style=discord.ButtonStyle.blurple)
    async def change_leader(self, interaction: Interaction, _: Button[Any]) -> None:
        lobby_owner = LobbyManager.get_lobby_owner(
            interaction.client, self.lobby_id)
        if interaction.user != lobby_owner:
            await interaction.response.defer()
        else:
            options = []
            list_of_users = LobbyManager.get_members(
                interaction.client, self.lobby_id)
            # Get a list of users
            for member_model in list_of_users:
                options.append(
                    (member_model.member.display_name, member_model.member.id))
            await interaction.response.send_message(
                view=OwnerSelectView(
                    self.lobby_id,
                    options
                ),
                ephemeral=True,
            )

    @discord.ui.button(label="Edit Descr.", style=discord.ButtonStyle.blurple)
    async def edit_description(self, interaction: Interaction, _: Button[Any]) -> None:
        if interaction.user != LobbyManager.get_lobby_owner(interaction.client, self.lobby_id):
            await interaction.response.defer()
        else:
            await interaction.response.send_modal(
                DescriptionModal(self.lobby_id),
            )

    @discord.ui.button(label="Disband", style=discord.ButtonStyle.blurple)
    async def disband(self, interaction: Interaction, _: Button[Any]) -> None:
        if interaction.user == LobbyManager.get_lobby_owner(interaction.client, self.lobby_id):
            await interaction.response.send_modal(
                ConfirmationModal(self.lobby_id)
            )
        else:
            await interaction.response.defer()

    @discord.ui.button(label="Promote", style=discord.ButtonStyle.blurple)
    async def promote(self, interaction: Interaction, _: Button[Any]) -> None:

        class PromotionEmbed(discord.Embed):
            def __init__(self, game_model_inner: GameModel, lobby_id: int):
                super().__init__(
                    title=f'Sponsor Friendly Ad for {game_model_inner.game_name}',
                    color=discord.Color.dark_orange(),
                )
                channel = LobbyManager.get_channel(interaction.client, lobby_id)
                self.description = f'Click on lobby <#{channel.id}> to join!'
                lobby_size = LobbyManager.get_member_length(interaction.client, lobby_id)
                game_size = int(LobbyManager.get_gamesize(interaction.client, lobby_id))
                self.add_field(
                    name='Slots Left:',
                    value=f'R>{game_size - lobby_size}',
                )
                if game_model_inner.icon_url:
                    self.set_thumbnail(url=game_model_inner.icon_url)

        # If user is not lobby owner, defer interaction
        if interaction.user != LobbyManager.get_lobby_owner(interaction.client, self.lobby_id):
            await interaction.response.defer()
            return
        # If last promotion was older than 10 minutes, defer interaction
        if not LobbyManager.can_promote(interaction.client, self.lobby_id):
            await interaction.response.defer()
            return

        is_full = LobbyManager.is_full(interaction.client, self.lobby_id)
        game_manager = GameManager()
        game_model: GameModel = game_manager.get_game(
            LobbyManager.get_gamecode(interaction.client, self.lobby_id)
        )
        # If the lobby is not full, promote
        if not is_full:
            original_channel = LobbyManager.get_original_channel(
                interaction.client,
                self.lobby_id
            )
            last_message = LobbyManager.get_last_promotion_message(
                interaction.client, self.lobby_id
            )
            # If there was an older promotion, delete it
            if last_message:
                await last_message.delete()
            message = await original_channel.send(
                content=f'<@&{game_model.role}>',
                embed=PromotionEmbed(game_model_inner=game_model, lobby_id=self.lobby_id)
            )
            LobbyManager.set_last_promotion_message(interaction.client, self.lobby_id, message)
