from typing import Tuple
import discord
from discord.ext import commands


class DropdownView(discord.ui.View):
    def __init__(
        self,
        bot: commands.Bot,
        id: int
    ):
        super().__init__(timeout=None)

        # Adds the dropdown to our view object
        self.add_item(
            GameDropdown(
                bot=bot,
                id=id,
            )
        )


class GameDropdown(discord.ui.Select):
    """A select dropdown for a list of games."""
    def __init__(self, bot: commands.Bot, id: str):
        # Set the options that will be presented inside the dropdown
        options = [
            discord.SelectOption(
                label='Valorant',
                value='VAL'),
            discord.SelectOption(
                label='Lost Ark',
                value='ARK'),
            discord.SelectOption(
                label='League of Legends',
                value='LOL'),
        ]

        super().__init__(placeholder='Choose your game...',
                         min_values=1, max_values=1, options=options)
        self.id = id
        self.bot = bot

    async def callback(self, interaction: discord.Interaction):
        self.bot.dispatch(
            'game_select',
            self.id,
            self.view,
            interaction
        )


class NumberDropdown(discord.ui.Select):
    # A select dropdown for a list of numbers.
    def __init__(self, lobby_id: int, bot: commands.Bot, number: int):
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
        self.bot.dispatch(
            'number_select',
            self.lobby_id,
            self.view,
            interaction
        )


class OwnerSelectView(discord.ui.View):
    def __init__(
        self,
        bot: commands.Bot,
        lobby_id: int,
        list_of_users: list[Tuple[discord.User, int]]
    ):
        super().__init__()
        self.list_of_users = list_of_users
        self.add_item(OwnerDropdown(bot, lobby_id, list_of_users))


class OwnerDropdown(discord.ui.Select):
    def __init__(
        self,
        bot: commands.Bot,
        lobby_id: int,
        list_of_users: list[Tuple[discord.User, int]]
    ):
        options = []

        for user in list_of_users:
            options.append(discord.SelectOption(
                label=user[0].name,
                value=str(user[1])
            ))

        super().__init__(
            placeholder='Choose new owner...',
            min_values=1,
            max_values=1,
            options=options
        )
        self.bot = bot
        self.lobby_id = lobby_id

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        self.bot.dispatch(
            'owner_select',
            self.lobby_id,
            int(interaction.data['values'][0]),
            interaction
        )
