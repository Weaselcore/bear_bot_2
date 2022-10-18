from typing import Any
from discord import Interaction, ButtonStyle
from discord.ext.commands import Bot # type: ignore
from discord.ui import View, Button

"""
Persistent View requirements:
- Timeout must be set to None
- Each component must have a unique custom_id
"""


class SoundButton(Button[Any]):
    def __init__(self, bot: Bot, file_path: str):
        super().__init__()
        self.bot = bot
        self.custom_id = file_path
        self.label = file_path
        self.style = ButtonStyle.blurple

    def callback(self, interaction: Interaction) -> None: # type: ignore
        self.bot.dispatch("play", interaction, self.custom_id)


class SoundBoardView(View):
    def __init__(self) -> None:
        super().__init__(timeout=None)
