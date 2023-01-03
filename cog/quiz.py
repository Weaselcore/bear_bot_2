from dataclasses import dataclass, field
import datetime
from enum import Enum
import html
import random
from dataclasses_json import dataclass_json
from discord.ext import commands
from discord import ButtonStyle, Member, Message, User, app_commands, Interaction, Embed, TextChannel, Colour
from discord.ui import View, Button
import aiohttp
import json

MAX_AMOUNT = 50

DIFFICULTY = [
    ("Any", "None"),
    ("Easy", "easy"),
    ("Medium", "medium"),
    ("Hard", "hard")
]

TYPE = [
    # There is an any type, but might lower complexity by giving a binary option.
    ("Multiple Choice", "multiple"),
    ("True/False", "boolean")
]

CATEGORY = [
    ("Any Category", "None"),
    ("General", 9),
    ("Books", 10),
    ("Film", 11),
    ("Music", 12),
    ("Musical & Theatre", 13),
    ("Television", 14),
    ("Video Games", 15),
    ("Board Games", 16),
    ("Science & Nature", 17),
    ("Computers", 18),
    ("Mathematics", 19),
    ("Mythology", 20),
    ("Sports", 21),
    ("Geography", 22),
    ("History", 23),
    ("Politics", 24),
    ("Art", 25),
    ("Celebrities", 26),
    ("Animals", 27),
    ("Vehicles", 28),
    ("Comics", 29),
    ("Science: Gadgets", 30),
    ("Anime & Manga", 31),
    ("Cartoons & Animation", 32)
]

AMOUNT = [str(x) for x in range(1, 11)]

MODE = [
    ("SOLO", "Solo"),
    ("FREE-FOR-ALL", "Free-For-All"),
    ("TEAM", "Team"),
]

class Mode(Enum):
    SOLO = "Solo"
    FREE_FOR_ALL = "Free-For-All"
    TEAM = "Team"

    @staticmethod
    def from_str(option: str):
        value = option.lower()
        if value in ('solo'):
            return Mode.SOLO
        elif value in ('free-for-all'):
            return Mode.FREE_FOR_ALL
        elif value in ('team'):
            return Mode.TEAM
        else:
            raise NotImplementedError


@dataclass_json
@dataclass
class Question:
    category: str
    type: str
    difficulty: str
    question: str
    correct_answer: str
    incorrect_answers: list[str]


@dataclass
class UserStat:
    user: Member | User
    correct: int = 0
    wrong: int = 0
    unanswered: int = 0


@dataclass
class QuizSession:
    owner: User | Member
    questions: list[Question]
    mode: Mode
    timeout: int
    click_whitelist: list[User | Member] | None = field(init=False)
    user_statistics: dict[int, UserStat] = field(default_factory=dict)
    current_question: Question = field(init=False)
    max_questions: int = field(init=False)
    user_answered: set[int] = field(default_factory=set)
    _index: int = 0

    def __post_init__(self):
        self.max_questions = len(self.questions)
        self.current_question = self.questions[self._index]
        # Always has someone initialised in stats.
        self.user_statistics[self.owner.id] = UserStat(self.owner)
        if self.mode == Mode.SOLO:
            self.click_whitelist = [self.owner]
        elif self.mode == Mode.FREE_FOR_ALL:
            self.click_whitelist = None
        else:
            raise NotImplementedError("Teams have not been implemented.")

    def next_question(self) -> None:
        self._index += 1
        self.current_question = self.questions[self._index]
        self.user_answered.clear()
    
    def get_index(self) -> int:
        return self._index + 1

    # TODO: Refactor these 2 functions below, too much repetition.
    def user_correct(self, user: User | Member):
        self.user_answered.add(user.id)
        if not user.id in self.user_statistics.keys():
            new_stat = UserStat(user=user)
            new_stat.correct += 1
            self.user_statistics[user.id] = new_stat
        else:
            user_stat = self.user_statistics[user.id]
            user_stat.correct += 1
            self.user_statistics[user.id] = user_stat

    def user_wrong(self, user: User | Member):
        self.user_answered.add(user.id)
        if not user.id in self.user_statistics.keys():
            new_stat = UserStat(user=user)
            new_stat.wrong += 1
            self.user_statistics[user.id] = new_stat
        else:
            user_stat = self.user_statistics[user.id]
            user_stat.wrong += 1
            self.user_statistics[user.id] = user_stat

    def user_unanswer(self):
        for user_id, user_stat in self.user_statistics.items():
            if user_id in self.user_answered:
                continue
            user_stat.unanswered += 1
            self.user_statistics[user_id] = user_stat
    
    def are_users_done(self) -> bool:
        if len(self.user_answered) == len(self.user_statistics):
            return True
        else:
            return False

    def get_progress_label(self) -> str:
        return f"☑️ {len(self.user_answered)}/{len(self.user_statistics)}"


class QuestionEmbed(Embed):
    def __init__(self, quiz_manager: QuizSession):
        super().__init__(
            title=html.unescape(quiz_manager.current_question.question),
            timestamp=datetime.datetime.now(),
            description=f"👇 Select a button to answer question within {quiz_manager.timeout} seconds.",
            colour=Colour.random()
        )
        self.add_field(name="Category:", value=quiz_manager.current_question.category)
        self.add_field(name="Difficulty:", value=quiz_manager.current_question.difficulty.capitalize())
        self.set_footer(text=f"📝 {quiz_manager.get_index()} out of {quiz_manager.max_questions} questions")


class ProgressButton(Button):
    def __init__(
        self,
        label: str,
        style: ButtonStyle = ButtonStyle.blurple
    ):
        super().__init__(style=style)
        self.label = label

    def update_label(self, new_label: str):
        self.label =  new_label


class AnswerButton(Button):
    def __init__(self,
                 answer: str,
                 quiz_manager: QuizSession,
                 # Wrapping type in string quotes allows for linting to be delayed avoiding definition errors.
                 parent_view: "QuestionButtonView",
                 style: ButtonStyle = ButtonStyle.secondary,
                 ):
        super().__init__(style=style)
        self.quiz_manager = quiz_manager
        self.correct_answer = html.unescape(quiz_manager.current_question.correct_answer.lower())
        self.answer = answer
        self.label = answer.upper()
        self.parent_view = parent_view

    async def on_correct(self, user: User | Member | None = None) -> None:
        if self.quiz_manager.are_users_done():
            self.style = ButtonStyle.green
        if not user:
            return
        self.parent_view.on_user_correct(user)

    async def on_wrong(self, user: User | Member) -> None:
        if self.quiz_manager.mode == Mode.SOLO:
            self.style = ButtonStyle.red
            await self.parent_view.show_correct_answer()
        self.parent_view.on_user_wrong(user)

    def is_correct(self) -> bool:
        if self.label:
            return self.label.lower() == self.correct_answer
        else:
            raise ValueError("Label has no string, cannot validate answer.")

    async def callback(self, interaction: Interaction):
        await interaction.response.defer()
        if self.quiz_manager.click_whitelist:
            # If there is a whitelist and user is not in it, do nothing.
            if interaction.user not in self.quiz_manager.click_whitelist:
                return
        if interaction.user.id in self.quiz_manager.user_answered:
            return
        if self.is_correct():
            await self.on_correct(interaction.user)
        else:
            await self.on_wrong(interaction.user)

        if self.quiz_manager.are_users_done():
            item: AnswerButton
            for item in self.parent_view.children:  # type: ignore
                item.disabled = True
            await self.parent_view.send_next()
        if self.view:
            # Remember, you need to respond to the interaction before this works.
            await interaction.edit_original_response(view=self.view)
            

class QuestionButtonView(View):
    def __init__(
        self,
        bot: commands.Bot,
        quiz_manager: QuizSession,
        timeout: float | None = 15
    ):
        super().__init__(timeout=timeout)
        self.quiz_manager = quiz_manager
        self._message: Message | None = None
        self.bot = bot
        # Flag to stop infinite loop when on timeout handler.
        self.finished = False
        self.progress_button: ProgressButton | None = None

        current_question = self.quiz_manager.current_question

        if current_question.type == "multiple":
            answers = self.shuffle_answers(current_question)
        else:
            answers = ['TRUE', 'FALSE']

        for answer in answers:
            self.add_item(
                AnswerButton(
                    quiz_manager=self.quiz_manager,
                    answer=html.unescape(answer),
                    parent_view=self,
                )
            )
        if not quiz_manager.mode == Mode.SOLO:
            self.progress_button = ProgressButton(label=quiz_manager.get_progress_label())
            self.add_item(self.progress_button)

    @property
    def message(self):
        if self._message:
            return self._message
        else:
            raise ValueError("Message has not been set.")
    
    @message.setter
    def message(self, new_message: Message):
        self._message = new_message

    def shuffle_answers(self, question: Question) -> list[str]:
        answer_copy = question.incorrect_answers.copy()
        answer_copy.append(question.correct_answer)
        random.shuffle(answer_copy)
        return answer_copy

    def next_question(self) -> None:
        self.quiz_manager.next_question()

    async def send_next(self):
        try:
            await self.show_correct_answer()
            self.next_question()

            channel = self.message.channel
            if channel:
                new_view = QuestionButtonView(
                    quiz_manager=self.quiz_manager,
                    bot=self.bot,
                    timeout=self.timeout
                )
                new_embed = QuestionEmbed(
                    quiz_manager=self.quiz_manager
                )
                new_view.message = await channel.send(embed=new_embed, view=new_view)
                self.finished = True
        except IndexError:
            if self.message:
                self.bot.dispatch("quiz_finish", self.message.channel, self.quiz_manager.user_statistics, self.quiz_manager.max_questions)
                self.finished = True

    async def on_timeout(self) -> None:
        if not self.finished:
            self.on_user_unanswer()
            await self.show_correct_answer()
            if self.message:
                await self.message.edit(view=self)
            await self.send_next()

    async def show_correct_answer(self):
        for item in self.children:
            if isinstance(item, AnswerButton) and item.label:
                if item.correct_answer.lower() == item.label.lower():
                    await item.on_correct()
            item.disabled = True
        await self.message.edit(view=self)

    def on_user_correct(self, user: Member | User):
        if self.progress_button:
            self.progress_button.update_label(self.quiz_manager.get_progress_label())
        self.quiz_manager.user_correct(user)

    def on_user_wrong(self, user: Member | User):
        if self.progress_button:
            self.progress_button.update_label(self.quiz_manager.get_progress_label())
        self.quiz_manager.user_wrong(user)

    def on_user_unanswer(self):
        self.quiz_manager.user_unanswer()


# Construct API Url from parameters
def get_url(amount: int, difficulty: str, q_type: str, category: str) -> str:

    print(f"{amount=}")

    ROOT_URL = "https://opentdb.com/api.php?"
    DIFFICULTY_PREFIX = "&difficulty="
    Q_TYPE_PREFIX = "&type="
    CATEGORY_PREFIX = "&category="

    if difficulty == "None":
        difficulty_url = ""
    else:
        difficulty_url = DIFFICULTY_PREFIX + difficulty
    if category == "None":
        category_url = ""
    else:
        category_url = CATEGORY_PREFIX + category

    url = f"{ROOT_URL}amount={amount}{category_url}{difficulty_url}{Q_TYPE_PREFIX}{q_type}"
    return url


class QuizCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.quiz_lobby = {}  # type: ignore

    @commands.Cog.listener()
    async def on_quiz_finish(self, channel: TextChannel, user_stats: dict[int, UserStat], max_question: int):
        embed = Embed(
            title="Quiz Statistics",
            description=f"There were {max_question} questions for this session.",
            colour=Colour.blue(),
        )
        for _, user_stat in user_stats.items():
            embed.add_field(
                name=user_stat.user.display_name, value=f"Correct: {user_stat.correct} | Wrong: {user_stat.wrong} | Unanswered: {user_stat.unanswered}",
                inline=False
            )
        await channel.send(embed=embed)

    async def amount_autocomplete(self, interaction: Interaction, current: str) -> list[app_commands.Choice[str]]:
        return [app_commands.Choice(name=str(number), value=str(number)) for number in AMOUNT if current in AMOUNT]

    async def difficulty_autocomplete(self, interaction: Interaction, current: str) -> list[app_commands.Choice[str]]:
        return [app_commands.Choice(name=difficulty[0], value=difficulty[1]) for difficulty in DIFFICULTY if current.lower() in difficulty[0].lower()]

    async def type_autocomplete(self, interaction: Interaction, current: str) -> list[app_commands.Choice[str]]:
        return [app_commands.Choice(name=question_type[0], value=question_type[1]) for question_type in TYPE if current.lower() in question_type[0].lower()]

    async def genre_autocomplete(self, interaction: Interaction, current: str) -> list[app_commands.Choice[str]]:
        return [app_commands.Choice(name=category[0], value=str(category[1])) for category in CATEGORY if current.lower() in category[0].lower()]

    async def mode_autocomplete(self, interaction: Interaction, current: str) -> list[app_commands.Choice[str]]:
        return [app_commands.Choice(name=mode[0], value=mode[1]) for mode in MODE if current.lower() in mode[0].lower()]

    @app_commands.command(description="Ask for any difficulty/genre question", name="trivia_any")
    @app_commands.autocomplete(
        amount=amount_autocomplete,
        mode=mode_autocomplete
    )
    async def any_trivia(self, interaction: Interaction, amount: int = 5, mode: str = Mode.FREE_FOR_ALL.value, timeout: int = 15):
        await interaction.response.defer()
        async with aiohttp.ClientSession() as session:

            q_type_choices = ["multiple", "boolean"]
            q_type = random.choice(q_type_choices)

            async with session.get(get_url(amount=amount, difficulty="None", q_type=q_type, category="None")) as response:

                if response.status == 200:
                    json_body = await response.text()
                    json_to_dict = json.loads(json_body)
                    questions: list[Question] = [Question.from_dict(  # type: ignore
                        question) for question in json_to_dict["results"]]
                    print(questions)
                    if json_to_dict["response_code"] == 0:
                        quiz_manager = QuizSession(
                            owner=interaction.user,
                            questions=questions,
                            mode=Mode.from_str(mode),
                            timeout=timeout
                        )
                        view = QuestionButtonView(
                            quiz_manager=quiz_manager,
                            bot=self.bot,
                            timeout=timeout
                        )
                        # Remember this line, gamechanger.
                        view.message = await interaction.followup.send(
                            embed=QuestionEmbed(
                                quiz_manager=quiz_manager
                            ),
                            view=view,
                            # This parameter makes the command wait, so a message it collected/returned when coro is complete.
                            wait=True
                        )
                    else:
                        await interaction.followup.send("Server could not complete request.")
                else:
                    await interaction.followup.send("Server could not complete request.")

    @app_commands.command(description="Ask for trivia questions", name="trivia")
    @app_commands.autocomplete(
        amount=amount_autocomplete,
        difficulty=difficulty_autocomplete,
        type=type_autocomplete,
        category=genre_autocomplete,
        mode=mode_autocomplete
    )
    async def trivia(self, interaction: Interaction, amount: str, difficulty: str, type: str, category: str, mode: str = Mode.FREE_FOR_ALL.value, timeout: int = 15):
        await interaction.response.defer()

        async with aiohttp.ClientSession() as session:
            async with session.get(get_url(int(amount), difficulty, type, category)) as response:

                if response.status == 200:
                    json_body = await response.text()
                    json_to_dict = json.loads(json_body)
                    print(json_to_dict)
                    questions = [Question.from_dict(  # type: ignore
                        question) for question in json_to_dict["results"]]
                    if json_to_dict["response_code"] == 0:
                        quiz_manager = QuizSession(
                            owner=interaction.user,
                            questions=questions,
                            mode=Mode.from_str(mode),
                            timeout=timeout
                        )
                        view = QuestionButtonView(
                            quiz_manager=quiz_manager,
                            bot=self.bot
                        )
                        view.message = await interaction.followup.send(
                            embed=QuestionEmbed(
                                quiz_manager=quiz_manager,
                            ),
                            view=view,
                            wait=True,
                        )
                    else:
                        await interaction.edit_original_response(content=f"Server could not complete request. {get_url(int(amount), difficulty, type, category)}")
                else:
                    await interaction.edit_original_response(content=f"Server could not complete request. {get_url(int(amount), difficulty, type, category)}")


async def setup(bot):
    await bot.add_cog(QuizCog(bot))


async def teardown(bot):
    await bot.remove_cog(QuizCog(bot))
