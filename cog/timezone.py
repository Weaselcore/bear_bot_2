from datetime import datetime
import os
from discord.ext import commands
from discord import Colour, Embed, Interaction, User, app_commands
import pytz
from cog.classes.utils import set_logger

from manager.timezone_service import TimezoneManager
from repository.db_config import DatabaseManager
from repository.table.timezone_table import TimezoneGuildModel, TimezoneUserModel
from repository.timezone_repo import TimezoneRepository

# Construct database url from environment variables
engine = DatabaseManager.create_engine(
    username=os.getenv("TZ_PG_USER") or os.environ["PG_USER"],
    password=os.getenv("TZ_PG_PASSWORD") or os.environ["PG_PASSWORD"],
    host=os.getenv("TZ_PG_HOST") or os.environ["PG_HOST"],
    port=os.getenv("TZ_PG_PORT") or os.environ["PG_PORT"],
    database_name=os.environ["TZ_PG_DATABASE"],
)

# This is the database session factory, invoking this variable creates a new session
async_session = DatabaseManager.create_async_session_maker(engine=engine)


def get_available_timezones() -> list[str]:
    """Function that returns the cached list of timezones from the zoneinfo module."""
    if not hasattr(get_available_timezones, "cached_timezones"):
        get_available_timezones.cached_timezones = list(
            pytz.all_timezones)
    return get_available_timezones.cached_timezones


class TimezoneTransformer(app_commands.Transformer):

    async def transform(self, interaction: Interaction, argument: str) -> str:
        list_of_time = get_available_timezones()
        if argument not in list_of_time:
            raise TimezoneTransformerError(
                f"{argument=} does not return a proper timezone")
        return argument

    async def autocomplete(
        self, interaction: Interaction, value: int | float | str, /
    ) -> list[app_commands.Choice[int | float | str]]:
        # Get all available timezone info, from tzdata package (Windows) or system timezones data (mac/linux).
        # This is all handled by Python's zoneinfo module.
        list_of_time = get_available_timezones()
        # Treat value given as substring and not just a prefix
        substring = str(value).lower()
        results = [app_commands.Choice(name=tz, value=tz)
                   for tz in list_of_time if substring in tz.lower()]
        return results[:25]


class TimezoneTransformerError(app_commands.AppCommandError):
    pass


class TimezoneCog(commands.GroupCog, group_name="timezone"):
    def __init__(self, bot: commands.Bot, timezone_manager: TimezoneManager):
        self.bot: commands.Bot = bot
        self.timezone_manager = timezone_manager
        self.logger = set_logger(logger_name="timezone")
        self.default_timezone = "NZ"
        print(f"{self.__cog_name__} loaded")

    @app_commands.command(
        name="register",
        description="Register a timezone with your account"
    )
    async def register_timezone(
        self,
        interaction: Interaction,
        timezone: app_commands.Transform[str, TimezoneTransformer]
    ) -> None:
        try:
            id = await self.timezone_manager.register_timezone(
                user_id=interaction.user.id,
                timezone=timezone,
                guild=interaction.guild,
            )
            self.logger.info(
                f"{interaction.user.display_name} is now registered with {timezone=}")
            await interaction.response.send_message(
                embed=Embed(
                    title="Timezone Registered",
                    description=f"{interaction.user.display_name.capitalize()} is now registered with timezone: {timezone}",
                    color=Colour.dark_gold()
                ).set_footer(text=f"[ID: {id}]")
            )
        except Exception as e:
            await interaction.response.send_message(e.args[0])

    @app_commands.command(
        name="get",
        description="Get the timezone registered with your account"
    )
    async def get_timezone(
        self,
        interaction: Interaction,
    ) -> None:
        try:
            timezone = await self.timezone_manager.get_timezone(
                user_id=interaction.user.id,
            )
            self.logger.info(
                f"{interaction.user.display_name} has requested their timezone of {timezone}")
            await interaction.response.send_message(
                embed=Embed(
                    title=f"{interaction.user.display_name.capitalize()}'s Timezone",
                    description=timezone,
                    color=Colour.dark_gold()
                )
            )
        except Exception as e:
            await interaction.response.send_message(e.args[0])

    @app_commands.command(
        name="change",
        description="Change the timezone registered with your account"
    )
    async def change_timezone(
        self,
        interaction: Interaction,
        timezone: app_commands.Transform[str, TimezoneTransformer]
    ) -> None:
        try:
            change_tuple = await self.timezone_manager.update_timezone(
                user_id=interaction.user.id,
                timezone=timezone
            )

            datetime_now = datetime.now(pytz.timezone('UTC'))
            old_datetime = self.timezone_manager.convert_datetime(
                datetime=datetime_now, timezone=change_tuple[0])
            new_datetime = self.timezone_manager.convert_datetime(
                datetime=datetime_now, timezone=change_tuple[1])

            self.logger.info(
                f"{interaction.user.display_name} has changed timezones from {change_tuple[0]} to {change_tuple[1]}")
            
            formatted_timedelta, _, descriptor = self.timezone_manager.get_datetime_difference(old_datetime, new_datetime)

            await interaction.response.send_message(
                embed=Embed(
                    title="Timezone Changed",
                    description=f"{interaction.user.display_name.capitalize()} has changed registered timezone from: {change_tuple[0]} to {change_tuple[1]}",
                    color=Colour.dark_gold()
                ).set_footer(text=f"Difference: {formatted_timedelta} {descriptor}")
            )
        except Exception as e:
            await interaction.response.send_message(e.args[0])

    @app_commands.command(
        name="all",
        description="Show all times across registered timezones"
    )
    async def show_all_times(self, interaction: Interaction) -> None:
        list_of_timezones = await self.timezone_manager.get_all_registered_timezones(interaction.guild_id)
        self.logger.info(
            f"{interaction.user.display_name} has requested all {list_of_timezones=}")
        datetime_now = datetime.now(pytz.timezone('UTC'))

        page = 1
        title = f"All Timezones Registered in Server | #{page}"
        count = 0

        try:
            embed = Embed(title=title, colour=Colour.dark_gold())
            for timezone in list_of_timezones:
                if count == 25:
                    if interaction.response.is_done():
                        await interaction.channel.send(
                            embed=embed
                        )
                    else:
                        await interaction.response.send_message(embed=embed)
                    count = 0
                    page += 1
                    self.logger.info(
                        f"25 field limit has been reached, creating new embed with page number {page}")
                    embed = Embed(title=title, colour=Colour.dark_gold())

                embed.add_field(
                    name=timezone,
                    value=self.timezone_manager.convert_datetime(
                        datetime_now, timezone).strftime('%#I:%M %p %d/%m/%Y'),
                    inline=False,
                )
                count += 1
            else:
                if interaction.response.is_done():
                    await interaction.channel.send(
                        embed=embed
                    )
                else:
                    await interaction.response.send_message(embed=embed)

        except Exception as e:
            await interaction.response.send_message(e.args[0])

    @app_commands.command(
        name="compare",
        description="Compare times with another person"
    )
    async def show_time(self, interaction: Interaction, user: User) -> None:
        comparer_tz, comparer_dt, comparee_tz, comparee_dt = await self.timezone_manager.compare_timezones(comparer_id=interaction.user.id, comparee_id=user.id)
        formatted_timedelta, _, descriptor = self.timezone_manager.get_datetime_difference(comparer_dt, comparee_dt)
        footer = f"{user.display_name.capitalize()}'s time is {formatted_timedelta} {descriptor}"

        self.logger.info(
            f"{interaction.user.display_name} is comparing time with {user.display_name}")
        self.logger.info(
            f"{comparer_tz=}| {comparer_dt=}, {comparee_tz=}| {comparee_dt}=")
        self.logger.info(f"Footer constructed: {footer}")

        await interaction.response.send_message(
            embed=Embed(
                title="Comparing Times",
                color=Colour.dark_gold()
            ).add_field(
                name=f"{interaction.user.display_name.capitalize()}'s Timezone is {comparer_tz}",
                value=f"{comparer_dt.strftime('%#I:%M %p')}"
            ).add_field(
                name=f"{user.display_name.capitalize()}'s Timezone is {comparee_tz}",
                value=f"{comparee_dt.strftime('%#I:%M %p')}",
                inline=False
            ).set_footer(
                text=footer
            )
        )


async def setup(bot: commands.Bot):
    # Create tables
    await DatabaseManager.create_tables(
        engine=engine,
        tables=[
            TimezoneGuildModel,
            TimezoneUserModel
        ]
    )
    # Create dependencies
    timezone_repository = TimezoneRepository(async_session)
    timezone_manager = TimezoneManager(bot=bot, repository=timezone_repository)
    await bot.add_cog(TimezoneCog(bot=bot, timezone_manager=timezone_manager))


async def teardown(bot: commands.Bot):
    cog = bot.get_cog("TimezoneCog")
    if isinstance(cog, commands.Cog):
        await bot.remove_cog(cog.__cog_name__)
