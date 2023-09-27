from datetime import datetime, timedelta
from discord import Guild
from discord.ext import commands
import human_readable
import pytz

from repository.timezone_repo import TimezoneRepository
from cog.classes.utils import set_logger

logger = set_logger("timezone_manager")


class TimezoneManager:
    def __init__(
        self,
        bot: commands.Bot,
        repository: TimezoneRepository
    ) -> None:
        self.bot = bot
        self.repository = repository

    async def get_timezone(self, user_id: int) -> str:
        return await self.repository.get_timezone_of_user(user_id)

    async def register_timezone(self, user_id: int, timezone: str, guild: Guild) -> int:
        return await self.repository.register_timezone(
            user_id=user_id,
            timezone=timezone,
            guild=guild
        )
    
    async def update_timezone(self, user_id: int, timezone: str) -> tuple[str, str]:
        return await self.repository.update_timezone(
            user_id=user_id,
            timezone=timezone
        )
    
    async def get_all_registered_timezones(self, guild_id: int) -> list[str]:
        return await self.repository.get_all_registered_timezones(
            guild_id=guild_id,
        )
    
    async def compare_timezones(self, comparer_id: int, comparee_id: int) -> tuple[str, datetime, str, datetime]:
        """Return (comparer timezone, comparer datetime, comparee timezone, comparee datetime)"""
        comparer_tz = await self.repository.get_timezone_of_user(comparer_id)
        comparee_tz = await self.repository.get_timezone_of_user(comparee_id)
        datetime_now = datetime.now(pytz.timezone('UTC'))
        return comparer_tz, self.convert_datetime(datetime_now, comparer_tz), comparee_tz, self.convert_datetime(datetime_now, comparee_tz),

    @staticmethod
    def get_datetime_difference(comparer_dt: datetime, comparee_dt: datetime) -> tuple[str, timedelta, str]:
        """Returns formatted timedelta, timedelta and if its ahead or behind"""

        logger.info(str(comparer_dt))
        logger.info(str(comparee_dt))

        timezone1 = pytz.timezone(str(comparer_dt.tzinfo))
        timezone2 = pytz.timezone(str(comparee_dt.tzinfo))

        # Get the current time in each timezone
        current_time1 = timezone1.localize(datetime.now())
        current_time2 = timezone2.localize(datetime.now())

        # Calculate the time difference between the two timezones
        time_difference: timedelta = current_time1.utcoffset() - current_time2.utcoffset()
        formatted_time_difference = human_readable.precise_delta(abs(time_difference))

        # if the time difference is negative it's ahead else its behind
        # Due to how things are compared, its the inverse of the calculation
        descriptor = "behind" if time_difference.total_seconds() > 0 else "ahead"

        logger.info(f"{formatted_time_difference=}, {time_difference=}, {descriptor=}")
        
        return formatted_time_difference, time_difference, descriptor

    @staticmethod
    def convert_datetime(datetime: datetime, timezone: str) -> datetime:
        new_timezone = pytz.timezone(timezone)
        return datetime.astimezone(new_timezone)

