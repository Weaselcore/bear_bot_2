from discord import Embed, Interaction, User, app_commands, colour
from discord.ext import commands


class UtilsCog(commands.GroupCog, name="utils"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(description="Display user's profile picture", name="dp")
    async def dp(self, interaction: Interaction, user: User):
        await interaction.response.send_message(
            embed=Embed(
                title=f"{user.display_name}'s DP", color=colour.Color.random()
            ).set_image(
                url=user.display_avatar.url,
            ),
        )


async def setup(bot):
    await bot.add_cog(UtilsCog(bot))


async def teardown(bot):
    await bot.remove_cog(UtilsCog(bot))
