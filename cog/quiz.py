from dataclasses import dataclass
import datetime
import html
import random
from dataclasses_json import dataclass_json
from discord.ext import commands
from discord import ButtonStyle, Member, User, app_commands, Interaction, Embed
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


@dataclass_json
@dataclass
class Question:
    category: str
    type: str
    difficulty: str
    question: str
    correct_answer: str
    incorrect_answers: list[str]

    def validate(self, answer: str) -> bool:
        if answer.lower() == self.correct_answer.lower():
            return True
        else:
            return False


class QuestionEmbed(Embed):
    def __init__(self, question: Question):
        self.question = question
        super().__init__(
            title=html.unescape(question.question),
            timestamp=datetime.datetime.now(),
            description="Click buttons to answer question."
        )

class QuizAnswerButton(Button):
    def __init__(self,
        answer: str,
        correct_answer: str,
        click_whitelist: list[Member | User],
        parent_view: View,
        style: ButtonStyle = ButtonStyle.secondary,
    ):
        super().__init__(style=style)
        self.correct_answer = correct_answer.lower()
        self.label = answer.upper()
        self.click_whitelist = click_whitelist
        self.parent_view = parent_view

    def on_correct(self) -> None:
        self.style = ButtonStyle.green

    def on_wrong(self) -> None:
        self.style = ButtonStyle.red
        child: QuizAnswerButton
        for child in self.parent_view.children: # type: ignore
            if not child.label:
                raise ValueError("Button label cannot be None")
            else:
                if child.label.lower() == self.correct_answer:
                    child.on_correct()

    def is_correct(self) -> bool:
        if self.label:
            return self.label.lower() == self.correct_answer
        else:
            raise ValueError("Label has no string, cannot validate answer.")


    async def callback(self, interaction: Interaction):
        await interaction.response.defer()
        if interaction.user not in self.click_whitelist:
            return
        if self.is_correct():
            self.on_correct()
        else:
            self.on_wrong()

        item: Button
        for item in self.parent_view.children: # type: ignore
            item.disabled = True
        if self.view:
            # Remember, you need to respond to the interaction before this works.
            await interaction.edit_original_response(view=self.view)


class QuizButtonView(View):
    def __init__(self, question: Question, click_whitelist: list[Member | User], timeout: float | None = 180):
        super().__init__(timeout=timeout)
        self.question = question

        if question.type == "multiple":
            answers = self.shuffle_answers(question)
        else:
            answers = ['TRUE', 'FALSE']

        for answer in answers:
            self.add_item(
                QuizAnswerButton(
                    answer=html.unescape(answer),
                    correct_answer=html.unescape(question.correct_answer),
                    click_whitelist=click_whitelist,
                    parent_view=self,
                )
            )

    def shuffle_answers(self, question: Question) -> list[str]:
        answer_copy = question.incorrect_answers.copy()
        answer_copy.append(question.correct_answer)
        random.shuffle(answer_copy)
        return answer_copy

    async def on_timeout(self) -> None:
        await super().on_timeout()
        item: Button
        for item in self.children: # type: ignore
            item.disabled = False

    # TODO: Write a manager or function within view to spawn another question.


# Construct API Url from parameters
def get_url(amount: int, difficulty: str, q_type: str, category: str) -> str:

    print(f"{amount=}")

    ROOT_URL = "https://opentdb.com/api.php?"
    DIFFICULTY_PREFIX = "&difficulty="
    Q_TYPE_PREFIX  = "&type="
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
    print(f"{url=}")
    return url


class QuizCog(commands.Cog):

    async def amount_autocomplete(self, interaction: Interaction, current: str) -> list[app_commands.Choice[str]]:
        return [app_commands.Choice(name=str(number), value=str(number)) for number in AMOUNT if current in AMOUNT]

    async def difficulty_autocomplete(self, interaction: Interaction, current: str) -> list[app_commands.Choice[str]]:
        return [app_commands.Choice(name=difficulty[0], value=difficulty[1]) for difficulty in DIFFICULTY if current.lower() in difficulty[0].lower()]

    async def type_autocomplete(self, interaction: Interaction, current: str) -> list[app_commands.Choice[str]]:
        return [app_commands.Choice(name=question_type[0], value=question_type[1]) for question_type in TYPE if current.lower() in question_type[0].lower()]

    async def genre_autocomplete(self, interaction: Interaction, current: str) -> list[app_commands.Choice[str]]:
        return [app_commands.Choice(name=category[0], value=str(category[1])) for category in CATEGORY if current.lower() in category[0].lower()]
    
    @app_commands.command(description="Ask for any difficulty/genre question", name="trivia_any")
    async def any_trivia(self, interaction: Interaction):
        await interaction.response.defer()
        async with aiohttp.ClientSession() as session:

            value = random.random()
            q_type_choices = ["multiple", "boolean"]
            q_type = random.choice(q_type_choices)

            async with session.get(get_url(amount=1, difficulty="None", q_type=q_type, category="None")) as response:

                print(response.status)

                if response.status == 200:
                    json_body = await response.text()
                    json_to_dict = json.loads(json_body)
                    print(json_to_dict)
                    questions = [Question.from_dict(question) for question in json_to_dict["results"]] # type: ignore
                    if json_to_dict["response_code"] == 0:
                        # await interaction.response.send_message(embed=QuestionEmbed(question=questions[0]))
                        await interaction.followup.send(
                            embed=QuestionEmbed(
                                    question=questions[0]
                                ),
                                view=QuizButtonView(
                                    question=questions[0],
                                click_whitelist=[interaction.user],
                            ),
                        )
                        # await interaction.channel.send(view=QuizButtonView(question=questions[0]))
                    else:
                        await interaction.followup.send("Server could not complete request.")
                else: 
                    await interaction.followup.send("Server could not complete request.")


    @app_commands.command(description="Ask for trivia questions", name="trivia")
    @app_commands.autocomplete(amount=amount_autocomplete, difficulty=difficulty_autocomplete, type=type_autocomplete, category=genre_autocomplete)
    async def trivia(self, interaction: Interaction, amount: str, difficulty: str, type: str, category: str):

        async with aiohttp.ClientSession() as session:
            async with session.get(get_url(int(amount), difficulty, type, category)) as response:

                print(response.status)

                if response.status == 200:
                    json_body = await response.text()
                    json_to_dict = json.loads(json_body)
                    print(json_to_dict)
                    questions = [Question.from_dict(question) for question in json_to_dict["results"]] # type: ignore
                    if json_to_dict["response_code"] == 0:
                        # await interaction.response.send_message(embed=QuestionEmbed(question=questions[0]))
                        await interaction.response.send_message(embed=QuestionEmbed(question=questions[0]), view=QuizButtonView(question=questions[0], click_whitelist=[interaction.user]))
                        # await interaction.channel.send(view=QuizButtonView(question=questions[0]))
                    else:
                        await interaction.response.send_message(f"Server could not complete request. {get_url(int(amount), difficulty, type, category)}")
                else: 
                    await interaction.response.send_message(f"Server could not complete request. {get_url(int(amount), difficulty, type, category)}")



async def setup(bot):
    await bot.add_cog(QuizCog(bot))


async def teardown(bot):
    await bot.remove_cog(QuizCog(bot))