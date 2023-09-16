import asyncio
import time

import discord
import openai
from discord import app_commands
from discord.ext import commands

TITLE_FIELD_NAME_LIMIT = 256
DESCRIPTION_LIMIT = 4096
FIELD_VALUE_LIMIT = 1024


class AiCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot: commands.Bot = bot
        print("AiCog loaded")

    @app_commands.command(description="Ask an AI about a general query", name="query")
    async def query(self, interaction: discord.Interaction, query: str):
        def truncate(string: str, limit: int):
            if len(string) > limit:
                return string[:limit]
            else:
                return string

        def wait_for_response(response_query: str):
            response_to_wait = openai.Completion.create(
                model="text-davinci-003",
                prompt=response_query,
                temperature=0.6,
                max_tokens=1028 - len(response_query),
            )

            while not response_to_wait:
                time.sleep(1)

            return response_to_wait

        try:
            await interaction.response.defer()
            response = await asyncio.to_thread(wait_for_response, response_query=query)
            text: str = response["choices"][0]["text"]  # type: ignore
            text_to_send = text.strip().replace("\n", " ")

            model: str = response["model"]  # type: ignore
            embed = discord.Embed(
                title=truncate(query, TITLE_FIELD_NAME_LIMIT),
                description=truncate(text_to_send, DESCRIPTION_LIMIT),
                colour=discord.Colour.dark_gold(),
            ).set_footer(text="💾 AI-MODEL: " + model)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            print(e)
            await interaction.followup.send(content=str(e))


async def setup(bot):
    await bot.add_cog(AiCog(bot))


async def teardown(bot):
    await bot.remove_cog(AiCog(bot))
