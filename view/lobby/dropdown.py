import discord
from discord.ext import commands
from model.game_model import GameManager

from model.lobby_model import LobbyManager
from view.lobby.button_view import ButtonView

from view.lobby.embeds import LobbyEmbed, UpdateMessageEmbed, UpdateMessageEmbedType


class DropdownView(discord.ui.View):
    def __init__(
        self,
        lobby_id: int,
        game_manager: GameManager,
    ):
        super().__init__(timeout=None)

        # Adds the dropdown to our view object
        self.add_item(
            GameDropdown(
                lobby_id=lobby_id,
                game_manager=game_manager,
            )
        )


class GameDropdown(discord.ui.Select):
    """A select dropdown for a list of games."""

    def __init__(self, lobby_id: str, game_manager: GameManager):
        # Set the options that will be presented inside the dropdown
        self.game_manager = game_manager
        options = []
        # Create select dropdown options from file.
        for game in game_manager.load_games():
            options.append(
                discord.SelectOption(
                    label=game.game_name,
                    value=game.game_code,
                )
            )

        super().__init__(placeholder='Choose your game...',
                         min_values=1, max_values=1, options=options)
        self.lobby_id = lobby_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.user == LobbyManager.get_lobby_owner(interaction.client, self.lobby_id):
            # Save selected game code in state.
            lobby_model = LobbyManager.set_gamecode(
                interaction.client,
                self.lobby_id,
                interaction.data['values'][0]
            )
            # Get max number from stored [GameModel] object.
            number = self.game_manager.get_max_size(lobby_model.game_code)

            # If the view already has a NumberDropdown for an updated one
            if (len(self.view.children) != 1):
                self.view.remove_item(self.view.children[1])

            self.view.children[0].placeholder = lobby_model.game_code
            self.view.add_item(
                NumberDropdown(
                    lobby_id=self.lobby_id,
                    bot=interaction.client,
                    number=number
                )
            )
            lobby_model = LobbyManager.get_lobby(
                interaction.client, self.lobby_id)
            # Edit game dropdown to reflect selected value
            await lobby_model.control_panel.edit(content="", view=self.view)
            # Send update message
            thread = LobbyManager.get_thread(interaction.client, self.lobby_id)
            await thread.send(
                embed=UpdateMessageEmbed(
                    bot=interaction.client,
                    lobby_id=self.lobby_id,
                    member=interaction.user,
                    embed_type=UpdateMessageEmbedType.GAME_CHANGE
                )
            )
        # Defer interaction update
        await interaction.response.defer()


class NumberDropdown(discord.ui.Select):
    # A select dropdown for a list of numbers.
    def __init__(
        self,
        lobby_id: int,
        bot: commands.Bot,
        number: int,
    ):
        # Set the options that will be presented inside the dropdown
        options = [
            discord.SelectOption(
                label=str(x + 1)) for x in range(1, number)
        ]
        super().__init__(
            placeholder='Choose your number...',
            min_values=1,
            max_values=1,
            options=options,
        )
        self.lobby_id = lobby_id
        self.bot = bot

    async def callback(self, interaction: discord.Interaction):

        await interaction.response.defer()
        # Reject interaction if user is not lobby owner
        if interaction.user != LobbyManager.get_lobby_owner(self.bot, self.lobby_id):
            return

        lobby_model = LobbyManager.set_gamesize(
            self.bot,
            self.lobby_id,
            interaction.data['values'][0]
        )

        # Set placeholder of dropdown to reflect selected value
        self.view.children[1].placeholder = interaction.data['values'][0]

        if lobby_model.embed_message is None:
            await lobby_model.control_panel.edit(
                content="",
                view=self.view
            )
            # Create owner embed
            embed = LobbyEmbed(
                lobby_id=self.lobby_id,
                bot=self.bot,
            )
            # Generate embed details from lobby_model
            await embed.update()
            LobbyManager.set_embed(self.bot, self.lobby_id, embed)
            # Create owner button view
            button = ButtonView(
                lobby_id=self.lobby_id,
            )
            # Send owner embed and view
            embed_message = await lobby_model.lobby_channel.send(
                embed=embed,
                view=button
            )

            LobbyManager.set_embed_message(
                self.bot, self.lobby_id, embed_message)
        else:
            self.bot.dispatch('update_lobby_embed', self.lobby_id)

        # Send update message
        thread = LobbyManager.get_thread(interaction.client, self.lobby_id)
        await thread.send(
            embed=UpdateMessageEmbed(
                bot=interaction.client,
                lobby_id=self.lobby_id,
                member=interaction.user,
                embed_type=UpdateMessageEmbedType.SIZE_CHANGE
            )
        )
