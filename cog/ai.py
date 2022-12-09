from discord.ext import commands


class AiCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot: commands.Bot = bot
        print('AiCog loaded')


async def setup(bot):
    await bot.add_cog(AiCog(bot))


async def teardown(bot):
    await bot.remove_cog(AiCog(bot))
