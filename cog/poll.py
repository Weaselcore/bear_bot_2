import asyncio
from discord import ButtonStyle, Color, Embed, Guild, Interaction, Member, TextChannel, app_commands
from discord import utils
from discord.ext import commands, tasks
from discord.ui import Button, View
from dotenv import load_dotenv
import os
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from manager.poll_service import PollManager
from repository.db_config import Base
from repository.poll_repo import PollRepository
from repository.poll_table import PollAnswerModel, PollGuildModel, PollMemberAnswerModel, PollModel, PollType, VoteType

load_dotenv()

# Construct database url from environment variables
DATABASE_URL = "postgresql+asyncpg://{}:{}@{}:{}/{}".format(
    os.environ['P_PG_USER'],
    os.environ['P_PG_PASSWORD'],
    os.environ['P_PG_HOST'],
    os.environ['P_PG_PORT'],
    os.environ['P_PG_DATABASE']
)

# Create database engine
engine = create_async_engine(
    DATABASE_URL,
    pool_size=3,
    future=True,
    echo=True,
)


# This is the database session factory, invoking this variable creates a new session
async_session = async_sessionmaker(
    engine,
    expire_on_commit=False,
)


class AnswerButton(Button):
    def __init__(
        self,
        label: str,
        style: ButtonStyle,
        custom_id: str,
        parent_view: "PollView",
    ) -> None:
        super().__init__(label=label, style=style, custom_id=custom_id)
        self.parent_view = parent_view
        self.button_id = int(custom_id)

    async def callback(self, interaction: Interaction):
        await interaction.response.defer()
        await self.parent_view.poll_manager.add_vote(answer_id=self.button_id, member_id=interaction.user.id)
        self.parent_view.bot.dispatch("poll_button_update", self.parent_view.poll_id)

class PollView(View):
    def __init__(
        self,
        bot: commands.Bot,
        poll_id: int,
        question: str,
        owner: Member,
        poll_manager: PollManager,
        poll_type: PollType,
        vote_type: VoteType,
    ) -> None:
        super().__init__(timeout=None)
        self.bot = bot
        self.poll_id = poll_id
        self.question = question.capitalize()
        self.owner = owner
        self.poll_manager = poll_manager
        self.poll_type = poll_type
        self.vote_type = vote_type

    async def create_buttons(self):
        self.options = [answer for answer in await self.poll_manager.get_poll_answers(self.poll_id)]
        for option in self.options:
            self.add_item(
                AnswerButton(
                    custom_id=str(option.id),
                    label=option.answer,
                    style=ButtonStyle.primary,
                    parent_view=self,
                )
            )
                

    async def create_embed(self) -> Embed:
        embed = Embed(title=self.question, color=Color.random())
        url = None
        if self.owner.avatar is not None:
            url = self.owner.avatar.url
        embed.set_author(name=self.owner.name, icon_url=url)
        for button in self.children:
            assert isinstance(button, AnswerButton)
            embed.add_field(
                name=button.label,
                value=f"Votes: {await self.poll_manager.get_vote(button.button_id)}",
            )
        embed.set_footer(text=f"[Poll ID: {self.poll_id}]")
        return embed
        


class PollCog(commands.Cog):

    def __init__(
        self,
        bot: commands.Bot,
        poll_manager: PollManager,
    ) -> None:
        self.bot = bot
        self.poll_manager = poll_manager
        print("Poll Cog Loaded")

    @tasks.loop(count=1, reconnect=True)
    async def poll_button_update(self, poll_id: int):
        # Reconstruct View with buttons.
        poll_model = await self.poll_manager.get_poll(poll_id)
        answer_model = await self.poll_manager.get_poll_answers(poll_id)

        poll_view = PollView(
            bot=self.bot,
            poll_id=poll_id,
            question=poll_model.question,
            owner=utils.get(self.bot.get_all_members(), id=poll_model.owner_id), # type: ignore
            poll_manager=self.poll_manager,
            poll_type=poll_model.poll_type,
            vote_type=poll_model.vote_type,
        )

        await poll_view.create_buttons()
        embed = await poll_view.create_embed()

        channel = self.bot.get_channel(poll_model.channel_id)
        if channel is None:
            channel = await self.bot.fetch_channel(poll_model.channel_id)

        message = channel.get_partial_message(poll_model.message_id) # type: ignore

        await message.edit(embed=embed, view=poll_view)


    @poll_button_update.before_loop
    async def before_poll_button_update(self):
        await asyncio.sleep(3)

    @commands.Cog.listener()
    async def on_poll_button_update(self, poll_id: int):
        if not self.poll_button_update.is_running():
            self.poll_button_update.start(poll_id)

    @app_commands.command(description="Create a poll, separate options with a comma", name="poll")
    async def poll(
        self,
        interaction: Interaction,
        question: str,
        options: str,
        # TODO: add poll type and vote type transformers/autocomplete
        # poll_type: PollType = PollType.MULTIPLE_CHOICE,
        # vote_type: VoteType = VoteType.SINGLE_VOTE
    ):
        await interaction.response.defer()

        assert isinstance(interaction.channel, TextChannel)
        assert isinstance(interaction.guild, Guild)

        cleaned_options = tuple(option.strip() for option in options.split(","))

        poll_id = await self.poll_manager.create_poll(
            question=question,
            owner_id=interaction.user.id,
            guild=interaction.guild,
            poll_type=PollType.BINARY,
            vote_type=VoteType.SINGLE_VOTE,
        )

        for option in cleaned_options:
            await self.poll_manager.add_answer(
                poll_id=poll_id,
                answer=option,
            )

        poll_view = PollView(
            bot=self.bot,
            poll_id=poll_id,
            owner=utils.get(self.bot.get_all_members(), id=interaction.user.id), # type: ignore
            question=question,
            poll_type=PollType.BINARY,
            vote_type=VoteType.SINGLE_VOTE,
            poll_manager=self.poll_manager,
        )

        await poll_view.create_buttons()

        await interaction.followup.send(
            content="Poll created, you can now add/remove answers with commands",
            ephemeral=True,
        )

        message = await interaction.channel.send(
            embed=await poll_view.create_embed(),
            view=poll_view,
        )
        await self.poll_manager.set_channel_message_id(
            poll_id=poll_id,
            channel_id=interaction.channel.id,
            message_id=message.id
        )

    @app_commands.command(description="Add an extra answer button through a poll id", name="add_answer")
    async def add_answer(self, interaction: Interaction, poll_id: int, answer: str):
        await self.poll_manager.add_answer(poll_id, answer)
        self.bot.dispatch("poll_button_update", poll_id=poll_id)

    @app_commands.command(description="Remove answer button through a poll id", name="remove_answer")
    async def remove_answer(self, interaction: Interaction, poll_id: int, answer: str):
        await self.poll_manager.remove_answer(answer) # type: ignore
        self.bot.dispatch("poll_button_update", poll_id=poll_id)

async def setup(bot: commands.Bot):
    async with engine.begin() as conn:
        await conn.run_sync(
            Base.metadata.create_all,
            tables=[
                PollAnswerModel.__table__,
                PollGuildModel.__table__,
                PollMemberAnswerModel.__table__,
                PollModel.__table__,
            ]
        )
    poll_repository = PollRepository(async_session)
    poll_manager = PollManager(bot, poll_repository)

    # TODO: Add a way to load all polls from the database and add them to the bot.

    await bot.add_cog(
        PollCog(bot, poll_manager)
    )


async def teardown(bot: commands.Bot):
    cog = bot.get_cog("PollCog")
    if isinstance(cog, commands.Cog):
        await bot.remove_cog(cog.__cog_name__)
