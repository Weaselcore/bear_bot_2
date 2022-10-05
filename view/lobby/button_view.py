import discord

from model.lobby_model import LobbyManager, LobbyState, MemberState
from view.lobby.embeds import UpdateMessageEmbed, UpdateMessageEmbedType


class DescriptionModal(discord.ui.Modal, title='Edit Description'):
    def __init__(self, lobby_id):
        super().__init__()
        self.lobby_id = lobby_id

    answer = discord.ui.TextInput(
        label='Edit Description',
        style=discord.TextStyle.paragraph,
        max_length=50
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        LobbyManager.set_descriptor(
            interaction.client, self.lobby_id, self.answer.value)
        # Send update embed
        thread = LobbyManager.get_thread(interaction.client, self.lobby_id)
        await thread.send(
            embed=UpdateMessageEmbed(
                bot=interaction.client,
                lobby_id=self.lobby_id,
                member=interaction.user,
                embed_type=UpdateMessageEmbedType.DESCRIPTION_CHANGE
            )
        )
        interaction.client.dispatch('update_lobby_embed', self.lobby_id)


class ConfirmationModal(discord.ui.Modal, title='Are you sure? Reason optional.'):
    def __init__(self, lobby_id):
        super().__init__()
        self.lobby_id = lobby_id

    reason = discord.ui.TextInput(
        label='Reason',
        max_length=150,
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        channel = LobbyManager.get_original_channel(
            interaction.client, self.lobby_id)
        extra_info = LobbyManager.get_session_time(
            interaction.client, self.lobby_id)
        await LobbyManager.delete_lobby(interaction.client, self.lobby_id)
        embed = UpdateMessageEmbed(
            bot=interaction.client,
            lobby_id=self.lobby_id,
            member=interaction.user,
            embed_type=UpdateMessageEmbedType.DELETE,
        ).add_field(
            name="Session Duration:",
            value=extra_info,
            inline=False
        )
        if self.reason.value:
            embed.add_field(
                name="Reason:",
                value=self.reason.value,
                inline=False
            )
        await channel.send(
            embed=embed,
        )


class OwnerSelectView(discord.ui.View):
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

    class OwnerDropdown(discord.ui.Select):
        def __init__(
            self,
            lobby_id: int,
            list_of_users: list[tuple[str, int]]
        ):
            options = []

            for user in list_of_users:
                options.append(discord.SelectOption(
                    label=user[0],
                    value=user[1]
                ))

            super().__init__(
                placeholder='Choose new owner...',
                min_values=1,
                max_values=1,
                options=options
            )
            self.lobby_id = lobby_id

        async def callback(self, interaction: discord.Interaction):
            lobby_owner = LobbyManager.get_lobby_owner(
                interaction.client, self.lobby_id)
            if interaction.user == lobby_owner:
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
            await self.view.stop()
            await original_channel.send(
                embed=UpdateMessageEmbed(
                    interaction.client,
                    self.lobby_id,
                    interaction.user,
                    UpdateMessageEmbedType.OWNER_CHANGE
                )
            )


class ButtonView(discord.ui.View):
    def __init__(
        self,
        lobby_id: int
    ):
        super().__init__(timeout=None)
        self.lobby_id = lobby_id

    @discord.ui.button(label='Join', style=discord.ButtonStyle.green)
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button,):
        if LobbyManager.has_joined(interaction.client, self.lobby_id, interaction.user):
            await interaction.response.defer()
            return
        LobbyManager.add_member(
            interaction.client, self.lobby_id, interaction.user)
        await interaction.response.edit_message(view=self)
        thread = LobbyManager.get_thread(interaction.client, self.lobby_id)
        await thread.send(
            embed=UpdateMessageEmbed(
                bot=interaction.client,
                lobby_id=self.lobby_id,
                member=interaction.user,
                embed_type=UpdateMessageEmbedType.JOIN
            )
        )
        if LobbyManager.is_full(interaction.client, self.lobby_id):
            interaction.client.dispatch("stop_promote_lobby", self.lobby_id)
        interaction.client.dispatch('update_lobby_embed', self.lobby_id)

    @discord.ui.button(label="Ready", style=discord.ButtonStyle.green)
    async def ready(self, interaction: discord.Interaction, button: discord.ui.Button):

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
        if lobby_state == LobbyState.LOCKED:
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

        if member_state == MemberState.READY:
            update_embed = UpdateMessageEmbed(
                interaction.client,
                self.lobby_id,
                interaction.user,
                UpdateMessageEmbedType.READY
            )
            members_ready = len(LobbyManager.get_members_ready(
                interaction.client, self.lobby_id))
            game_size = int(LobbyManager.get_gamesize(
                interaction.client, self.lobby_id))
            lobby_owner = LobbyManager.get_lobby_owner(
                interaction.client, self.lobby_id)
            if members_ready == game_size:
                # Add addional field in embed
                update_embed.add_field(
                    name="Everyone has readied up!",
                    value=f"🔒 <@{lobby_owner.id}>, please lock the lobby.",
                    inline=False
                )
            await thread.send(embed=update_embed)

    @discord.ui.button(label="Leave", style=discord.ButtonStyle.red)
    async def leave(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        embed_type = None
        lobby_owner = LobbyManager.get_lobby_owner(
            interaction.client, self.lobby_id)
        original_channel = LobbyManager.get_original_channel(
            interaction.client, self.lobby_id)
        # TODO: Merge with owner leave listener
        # Delete lobby if there is 1 person left
        if LobbyManager.get_member_length(interaction.client, self.lobby_id) == 1:
            interaction.client.dispatch("stop_promote_lobby", self.lobby_id)
            await LobbyManager.delete_lobby(interaction.client, self.lobby_id)
            embed_type = UpdateMessageEmbedType.DELETE
            await original_channel.send(
                embed=UpdateMessageEmbed(
                    interaction.client,
                    self.lobby_id,
                    interaction.user,
                    embed_type
                ).add_field(
                    name="Session Duration:",
                    value=LobbyManager.get_session_time(interaction.client, self.lobby_id),
                    inline=False
                )
            )
            return
        # Remove member from lobby
        elif interaction.user != lobby_owner:
            LobbyManager.remove_member(
                interaction.client, self.lobby_id, interaction.user)
            embed_type = UpdateMessageEmbedType.LEAVE
        # Remove user and find new leader
        else:
            LobbyManager.remove_owner(interaction.client, self.lobby_id)
            embed_type = UpdateMessageEmbedType.OWNER_CHANGE

        await original_channel.send(
            embed=UpdateMessageEmbed(
                interaction.client,
                self.lobby_id,
                interaction.user,
                embed_type
            )
        )
        # Update lobby embed
        interaction.client.dispatch('update_lobby_embed', self.lobby_id)

    @discord.ui.button(label="Lock", style=discord.ButtonStyle.danger)
    async def lock(self, interaction: discord.Interaction, button: discord.ui.Button):

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
        if lobby_status == LobbyState.LOCKED:
            status = UpdateMessageEmbedType.LOCK
        elif lobby_status == LobbyState.UNLOCKED:
            status = UpdateMessageEmbedType.UNLOCKED
        # Update lobby embed
        interaction.client.dispatch('update_lobby_embed', self.lobby_id)
        # Send update message
        if status:
            original_channel = LobbyManager.get_original_channel(
                interaction.client, self.lobby_id)
            await original_channel.send(
                embed=UpdateMessageEmbed(
                    interaction.client,
                    self.lobby_id,
                    interaction.user,
                    status
                )
            )

    @discord.ui.button(label="Change Leader", style=discord.ButtonStyle.blurple)
    async def change_leader(self, interaction: discord.Interaction, button: discord.ui.Button):
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
    async def edit_description(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != LobbyManager.get_lobby_owner(interaction.client, self.lobby_id):
            await interaction.response.defer()
        else:
            await interaction.response.send_modal(
                DescriptionModal(self.lobby_id),
            )

    @discord.ui.button(label="Disband", style=discord.ButtonStyle.blurple)
    async def disband(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user == LobbyManager.get_lobby_owner(interaction.client, self.lobby_id):
            await interaction.response.send_modal(
                ConfirmationModal(self.lobby_id)
            )
        interaction.response.defer()

    @discord.ui.button(label="Promote: OFF", style=discord.ButtonStyle.blurple)
    async def promote(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user == LobbyManager.get_lobby_owner(interaction.client, self.lobby_id):
            if button.label == "Promote: OFF":
                button.label = "Promote: ON"
                interaction.client.dispatch("promote_lobby", self.lobby_id,)
            else:
                button.label = "Promote: OFF"
                interaction.client.dispatch("stop_promote_lobby", self.lobby_id)
            await interaction.response.edit_message(view=self)
        else:
            await interaction.response.defer()
