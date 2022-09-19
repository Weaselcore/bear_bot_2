import discord
from discord.ext import commands


class OwnerButtonView(discord.ui.View):
    def __init__(
        self,
        bot: commands.Bot,
        lobby_id: int
    ):
        super().__init__(timeout=None)
        self.lobby_id = lobby_id
        self.bot = bot
        self.index = 0

    @discord.ui.button(label="Ready", style=discord.ButtonStyle.red)
    async def ready(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.bot.dispatch(
            "member_ready",
            self.lobby_id,
            self.index,
            self,
            interaction,
            button
        )

    @discord.ui.button(label="Lock", style=discord.ButtonStyle.green)
    async def lock(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.bot.dispatch(
            "lobby_lock",
            self.lobby_id,
            self,
            interaction,
            button
        )

    @discord.ui.button(label="Change Leader", style=discord.ButtonStyle.green)
    async def change_leader(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.bot.dispatch(
            "change_leader_press",
            self.lobby_id,
            interaction
        )

    @discord.ui.button(label="Edit Descr.", style=discord.ButtonStyle.blurple)
    async def edit_description(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.bot.dispatch(
            "descriptor_click",
            self.lobby_id,
            interaction
        )

    @discord.ui.button(label="Leave", style=discord.ButtonStyle.red)
    async def leave(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.bot.dispatch(
            'owner_leave',
            self.lobby_id,
            interaction
        )


class OpenSlotButtonView(discord.ui.View):
    def __init__(self, index: int, lobby_id: int, bot: commands.Bot):
        super().__init__(timeout=None)
        self.index = index
        self.lobby_id = lobby_id
        self.bot = bot

    @discord.ui.button(label="Join", style=discord.ButtonStyle.green)
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.bot.dispatch(
            'lobby_join',
            self.index,
            self.lobby_id,
            interaction
        )


class ClosedSlotButtonView(discord.ui.View):
    def __init__(self, index: int, lobby_id: int, bot: commands.Bot):
        super().__init__(timeout=None)
        self.index = index
        self.lobby_id = lobby_id
        self.bot = bot

    @discord.ui.button(label="Ready", style=discord.ButtonStyle.red)
    async def ready(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.bot.dispatch(
            "member_ready",
            self.lobby_id,
            self.index,
            self,
            interaction,
            button
        )

    @discord.ui.button(label="Leave", style=discord.ButtonStyle.green)
    async def leave(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.bot.dispatch(
            'lobby_leave',
            self.index,
            self.lobby_id,
            interaction
        )
