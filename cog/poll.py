import asyncio
from discord import ButtonStyle, Color, Embed, Guild, Interaction, Member, TextChannel, app_commands
from discord import utils
from discord.ext import commands, tasks
from discord.ui import Button, Modal, View, TextInput
from dotenv import load_dotenv
import os
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from manager.poll_service import PollManager
from repository.db_config import Base
from repository.poll_repo import PollRepository
from repository.poll_table import PollAnswerModel, PollGuildModel, PollMemberAnswerModel, PollModel, VoteType

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


class PollTransformError(app_commands.AppCommandError):
    pass


class AnswerTransformError(app_commands.AppCommandError):
    pass


class PollTransformer(app_commands.Transformer):

    def __init__(self):
        self._poll_manager = None

    def get_poll_manager(self, interaction: Interaction):
        if self._poll_manager is None:
            self._poll_manager = PollManager(
                bot=interaction.client,  # type: ignore
                repository=PollRepository(async_session),
            )
        return self._poll_manager

    async def transform(self, interaction: Interaction, argument: str) -> int:
        assert interaction.guild is not None
        poll_manager = self.get_poll_manager(interaction)
        poll_by_guild = await poll_manager.get_all_polls_by_guild_id(interaction.guild.id)
        try:
            value = int(argument)
            for poll in poll_by_guild:
                if value == poll.id:
                    return poll.id
            else:
                raise PollTransformError(f"Poll_id: {argument} not found")
        except ValueError:
            raise PollTransformError(f"Poll_id: {argument} not found")

    async def autocomplete(
        self,
        interaction: Interaction,
        value: int | float | str,
        /
    ) -> list[app_commands.Choice[int | float | str]]:
        assert interaction.guild is not None
        list_of_options: list[app_commands.Choice[int | float | str]] = []

        poll_manager = self.get_poll_manager(interaction)
        poll_by_guild = await poll_manager.get_all_polls_by_guild_id(interaction.guild.id)
        # If there are no games available, return an empty list
        if len(poll_by_guild) == 0:
            return list_of_options
        # If nothing is inputted, return all games
        if value == "":
            for poll in poll_by_guild:
                list_of_options.append(
                    app_commands.Choice(
                        name=str(poll.question),
                        value=str(poll.id)
                    )
                )
        else:
            # If there is an input, return all poll that start with the input
            for poll in poll_by_guild:
                if str(poll.id).startswith(str(value).lower()):
                    list_of_options.append(
                        app_commands.Choice(
                            name=str(poll.question),
                            value=str(poll.id)
                        )
                    )
        return list_of_options


class ActivePollTransformer(app_commands.Transformer):

    def __init__(self):
        self._poll_manager = None

    def get_poll_manager(self, interaction: Interaction):
        if self._poll_manager is None:
            self._poll_manager = PollManager(
                bot=interaction.client,  # type: ignore
                repository=PollRepository(async_session),
            )
        return self._poll_manager

    async def transform(self, interaction: Interaction, argument: str) -> int:
        assert interaction.guild is not None
        poll_manager = self.get_poll_manager(interaction)
        poll_by_guild = await poll_manager.get_all_active_polls_by_guild_id(interaction.guild.id)
        try:
            value = int(argument)
            for poll in poll_by_guild:
                if value == poll.id:
                    return poll.id
            else:
                raise PollTransformError(f"Poll_id: {argument} not found")
        except ValueError:
            raise PollTransformError(f"Poll_id: {argument} not found")

    async def autocomplete(
        self,
        interaction: Interaction,
        value: int | float | str,
        /
    ) -> list[app_commands.Choice[int | float | str]]:
        assert interaction.guild is not None
        list_of_options: list[app_commands.Choice[int | float | str]] = []

        poll_manager = self.get_poll_manager(interaction)
        poll_by_guild = await poll_manager.get_all_active_polls_by_guild_id(interaction.guild.id)
        # If there are no games available, return an empty list
        if len(poll_by_guild) == 0:
            return list_of_options
        # If nothing is inputted, return all games
        if value == "":
            for poll in poll_by_guild:
                list_of_options.append(
                    app_commands.Choice(
                        name=str(poll.question),
                        value=str(poll.id)
                    )
                )
        else:
            # If there is an input, return all poll that start with the input
            for poll in poll_by_guild:
                if str(poll.id).startswith(str(value).lower()):
                    list_of_options.append(
                        app_commands.Choice(
                            name=str(poll.question),
                            value=str(poll.id)
                        )
                    )
        return list_of_options


class AnswerTransformer(app_commands.Transformer):

    def __init__(self):
        self._poll_manager = None

    def get_poll_manager(self, interaction: Interaction):
        if self._poll_manager is None:
            self._poll_manager = PollManager(
                bot=interaction.client,  # type: ignore
                repository=PollRepository(async_session),
            )
        return self._poll_manager

    async def transform(self, interaction: Interaction, argument: str) -> int:
        assert interaction.guild is not None
        poll_manager = self.get_poll_manager(interaction)
        try:
            poll_id = interaction.namespace["poll_id"]
            value = int(argument)
            answers = await poll_manager.get_answers_by_poll_id(int(poll_id))
            for answer_model in answers:
                if value == answer_model.id:
                    return answer_model.id
            else:
                raise AnswerTransformError(f"Answer_id: {argument} not found")
        except ValueError:
            raise AnswerTransformError(f"Answer_id: {argument} not found")

    async def autocomplete(
        self,
        interaction: Interaction,
        value: int | float | str,
        /
    ) -> list[app_commands.Choice[int | float | str]]:
        list_of_options: list[app_commands.Choice[int | float | str]] = []
        poll_id = interaction.namespace["poll_id"]
        poll_manager = self.get_poll_manager(interaction)
        if poll_id is None:
            return list_of_options
        try:
            answers = await poll_manager.get_answers_by_poll_id(int(poll_id))
            if value is None:
                for answer_model in answers:
                    list_of_options.append(
                        app_commands.Choice(
                            name=answer_model.answer,
                            value=str(answer_model.id)
                        )
                    )
            else:
                for answer_model in answers:
                    if answer_model.answer.startswith(str(value)):
                        list_of_options.append(
                            app_commands.Choice(
                                name=answer_model.answer,
                                value=str(answer_model.id)
                            )
                        )
            return list_of_options
        except ValueError:
            return []


class AnswerButton(Button):
    def __init__(
        self,
        label: str,
        style: ButtonStyle,
        custom_id: str,
        parent_view: "PollView",
        is_disabled: bool = False,
    ) -> None:
        super().__init__(label=label, style=style, custom_id=custom_id)
        self.parent_view = parent_view
        self.button_id = int(custom_id)
        self.disabled = is_disabled

    async def callback(self, interaction: Interaction):
        await interaction.response.defer()
        await self.parent_view.poll_manager.add_vote(
            poll_id=self.parent_view.poll_id,
            answer_id=self.button_id,
            member_id=interaction.user.id,
            vote_type=self.parent_view.vote_type
        )
        self.parent_view.bot.dispatch(
            "poll_button_update", self.parent_view.poll_id)


class EditModalModal(Modal):
    def __init__(
        self,
        answers: list[PollAnswerModel],
        bot: commands.Bot,
        poll_id: int,
        poll_manager: PollManager
    ) -> None:
        super().__init__(timeout=None, title="Add URL to an option")
        self.answers = answers
        self.bot=bot
        self.poll_id = poll_id
        self.poll_manager = poll_manager
        self.custom_id = f"edit_modal_{self.poll_id}"

        for answer in self.answers:
            self.add_item(
                TextInput(
                    label=answer.answer,
                    placeholder="Enter URL starting with HTTP:// or HTTPS://",
                    default=answer.url,
                    required=False,
                    custom_id=str(answer.id),
                )
            )

    async def on_submit(self, interaction: Interaction):
        for text_input in self.children:
            if text_input.custom_id is None: # type: ignore
                continue
            for answer in self.answers:
                if answer.id == int(text_input.custom_id): # type: ignore
                    answer.url = text_input.value if text_input.value != "" else None # type: ignore
                    if answer.url is not None:
                        if (answer.url.startswith("http://") or answer.url.startswith("https://")):
                            await self.poll_manager.add_url(answer.id, answer.url)
                        else:
                            await interaction.response.send_message("URL must start with HTTP:// or HTTPS://", ephemeral=True)
                            return
        else:
            self.bot.dispatch("poll_button_update", self.poll_id)
            await interaction.response.send_message("URLs updated", ephemeral=True)


class PollView(View):
    def __init__(
        self,
        bot: commands.Bot,
        poll_id: int,
        question: str,
        owner: Member,
        poll_manager: PollManager,
        vote_type: VoteType,
        colour: str,
        is_disabled: bool = False,
    ) -> None:
        super().__init__(timeout=None)
        self.bot = bot
        self.poll_id = poll_id
        self.question = question.capitalize()
        self.owner = owner
        self.poll_manager = poll_manager
        self.vote_type = vote_type
        self.colour = colour
        self.disable = is_disabled

    async def create_buttons(self):
        self.options = [answer for answer in await self.poll_manager.get_poll_answers(self.poll_id)]
        for option in self.options:
            self.add_item(
                AnswerButton(
                    custom_id=str(option.id),
                    label=option.answer,
                    style=ButtonStyle.primary,
                    parent_view=self,
                    is_disabled=self.disable,
                )
            )
        if self.disable:
            self.stop()

    async def create_embed(self) -> Embed:
        embed = Embed(title=self.question, color=Color.from_str(self.colour))
        url = None

        if self.owner.avatar is not None:
            url = self.owner.avatar.url
        embed.set_author(name=self.owner.name, icon_url=url)

        for option in self.options:
            url_value = ""
            if option.url is not None:
                url_value = f"[Click here to view]({option.url})\n"
            embed.add_field(
                name=option.answer,
                value=url_value + f"Votes: {await self.poll_manager.get_vote(option.id)}",
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

        poll_view = PollView(
            bot=self.bot,
            poll_id=poll_id,
            question=poll_model.question,
            owner=utils.get(self.bot.get_all_members(),
                            id=poll_model.owner_id),  # type: ignore
            poll_manager=self.poll_manager,
            vote_type=poll_model.vote_type,
            colour=poll_model.colour,
            is_disabled=not poll_model.is_active
        )

        await poll_view.create_buttons()
        embed = await poll_view.create_embed()

        channel = self.bot.get_channel(poll_model.channel_id)
        if channel is None:
            channel = await self.bot.fetch_channel(poll_model.channel_id)

        message = channel.get_partial_message(  # type: ignore
            poll_model.message_id
        )

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
        # vote_type: VoteType = VoteType.SINGLE_VOTE
    ):
        await interaction.response.defer()

        assert isinstance(interaction.channel, TextChannel)
        assert isinstance(interaction.guild, Guild)

        cleaned_options = tuple(option.strip()
                                for option in options.split(","))
        
        colour = str(Color.random())

        poll_id = await self.poll_manager.create_poll(
            question=question,
            owner_id=interaction.user.id,
            guild=interaction.guild,
            vote_type=VoteType.SINGLE_VOTE,
            colour=colour
        )

        for option in cleaned_options:
            await self.poll_manager.add_answer(
                answer=option,
                owner_id=interaction.user.id,
                poll_id=poll_id,
            )

        poll_view = PollView(
            bot=self.bot,
            poll_id=poll_id,
            owner=utils.get(self.bot.get_all_members(),
                            id=interaction.user.id),  # type: ignore
            question=question,
            vote_type=VoteType.MULTIPLE_VOTE,
            poll_manager=self.poll_manager,
            colour=colour
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
    async def add_answer(
        self,
        interaction: Interaction,
        poll_id: app_commands.Transform[int, ActivePollTransformer],
        answer: str,
    ):
        await self.poll_manager.add_answer(
            answer=answer,
            owner_id=interaction.user.id,
            poll_id=poll_id,
        )
        self.bot.dispatch("poll_button_update", poll_id=poll_id)
        await interaction.response.send_message(
            content=f"Adding button for answer: {answer}",
        )

    @app_commands.command(description="Remove answer button through a poll id", name="remove_answer")
    async def remove_answer(
        self,
        interaction: Interaction,
        poll_id: app_commands.Transform[int, ActivePollTransformer],
        answer_id: app_commands.Transform[int, AnswerTransformer]
    ):
        answer = await self.poll_manager.get_poll_answer(answer_id)
        await self.poll_manager.remove_answer(answer_id)
        self.bot.dispatch("poll_button_update", poll_id=poll_id)
        await interaction.response.send_message(
            content=f"Removing button for answer: {answer}",
        )

    @app_commands.command(description="Mark a poll inactive", name="end_poll")
    async def end_poll(
        self,
        interaction: Interaction,
        poll_id: app_commands.Transform[int, ActivePollTransformer],
    ):
        await self.poll_manager.end_poll(poll_id)
        await interaction.response.send_message(
            content=f"Poll ended",
        )
        self.bot.dispatch("poll_button_update", poll_id=poll_id)

    @app_commands.command(description="Add urls to your own options", name="add_url")
    async def add_url(
        self,
        interaction: Interaction,
        poll_id: app_commands.Transform[int, ActivePollTransformer],
    ):
        answers = await self.poll_manager.get_poll_answer_by_user_id(poll_id, interaction.user.id)
        await interaction.response.send_modal(
            EditModalModal(
                answers=answers,
                bot=self.bot,
                poll_id=poll_id,
                poll_manager=self.poll_manager,
            ),
        )


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

    active_polls = await poll_repository.get_all_active_polls()
    for poll in active_polls:
        poll_view = PollView(
            bot=bot,
            poll_id=poll.id,
            question=poll.question,
            owner=utils.get(bot.get_all_members(),
                            id=poll.owner_id),  # type: ignore
            poll_manager=poll_manager,
            vote_type=poll.vote_type,
            colour=poll.colour,
            is_disabled=not poll.is_active
        )
        await poll_view.create_buttons()
        bot.add_view(
            view=poll_view,
            message_id=poll.message_id
        )

    await bot.add_cog(
        PollCog(bot, poll_manager)
    )


async def teardown(bot: commands.Bot):
    cog = bot.get_cog("PollCog")
    if isinstance(cog, commands.Cog):
        await bot.remove_cog(cog.__cog_name__)
