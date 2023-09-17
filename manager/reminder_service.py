from datetime import datetime, timedelta
from functools import partial
from typing import Any, Coroutine

import human_readable
from discord import Colour, Embed, Guild, Interaction
from discord.ext import commands

from cog.classes.scheduler_task import SchedulerTask
from cog.scheduler import SchedulerCog
from repository.reminder_repo import ReminderRepository
from repository.table.reminder_table import ReminderModel


class ReminderManager:
    def __init__(self, bot: commands.Bot, repository: ReminderRepository) -> None:
        self.bot = bot
        self.repository = repository

    def _create_id_for_scheduler(self, id: str) -> str:
        return f"reminder_{id}"

    def _get_scheduler(self) -> SchedulerCog:
        scheduler = self.bot.get_cog("SchedulerCog")
        if scheduler is None:
            raise ValueError("SchedulerCog is not active or loaded.")
        return scheduler

    async def _reminder_callback(
        self, reminder: str, channel_id: int, user_id: int, id: int
    ):
        channel = self.bot.get_channel(channel_id)
        user = self.bot.get_user(user_id)

        # TODO: dispatch error if somehow id's are not present.

        await channel.send(f" # REMINDER: \n## *{reminder}* \n<@{user.id}>")
        await self.repository.update_reminder_has_triggered(id)

    def get_reminder_callback(
        self,
        reminder: str,
        channel_id: int,
        user_id: int,
        id: int,
    ) -> partial[Coroutine[Any, Any, None]]:
        return partial(
            self._reminder_callback,
            reminder=reminder,
            channel_id=channel_id,
            user_id=user_id,
            id=id,
        )

    async def get_all_reminders_by_guild_id(self, guild_id: int) -> list[ReminderModel]:
        return await self.repository.get_all_reminders_by_guild_id(guild_id=guild_id)

    async def get_all_active_reminders_by_user_id(
        self, user_id: int
    ) -> list[ReminderModel]:
        return await self.repository.get_all_active_reminders_by_user_id(
            user_id=user_id
        )

    async def create_reminder(
        self,
        interaction: Interaction,
        reminder: str,
        owner_id: int,
        guild: Guild,
        expire_at: datetime,
        delta: timedelta,
    ) -> int:
        # Add entry to database
        reminder_id = await self.repository.add_reminder(
            channel_id=interaction.channel.id,
            reminder=reminder,
            owner_id=owner_id,
            guild=guild,
            expire_at=expire_at,
        )
        # Add entry to scheduler
        try:
            scheduler = self._get_scheduler()
            embed = (
                Embed(
                    colour=Colour.random(),
                    title=f"Reminder for {interaction.user.display_name}",
                    description=reminder.capitalize(),
                    timestamp=expire_at,
                )
                .add_field(
                    name="When:",
                    value=f"⠀⠀⤷ **{human_readable.precise_delta(delta)}**",
                )
                .set_footer(text=f"[ ID: {reminder_id} ]")
            )
            # Send response to interaction
            await interaction.response.send_message(embed=embed)
            # Schedule reminder to scheduler
            scheduler.schedule_item(
                SchedulerTask(
                    id=self._create_id_for_scheduler(id=reminder_id),
                    expires_at=expire_at,
                    task=self.get_reminder_callback(
                        reminder=reminder,
                        channel_id=interaction.channel.id,
                        user_id=interaction.user.id,
                        id=reminder_id,
                    ),
                )
            )
        except ValueError:
            await interaction.response.send_message(
                "Scheduler Cog has not been initialised, event scheduling is disabled."
            )

    async def delete_reminder(self, interaction: Interaction, reminder_id: int):
        try:
            reminder_model = await self.repository.get_reminder(reminder_id)
            if reminder_model.owner_id != interaction.user.id:
                await interaction.response.send_message(
                    "Sorry, looks like this reminder doesn't belong to you."
                )
            reminder_id = await self.repository.remove_reminder(reminder_id)
            await interaction.response.send_message(
                f"The reminder with id {reminder_id} has been deleted!"
            )
            # Prepare to remove from scheduler
            scheduler = self._get_scheduler()
            # Remove from scheduler
            scheduler.remove_schedule(
                SchedulerTask(
                    id=self._create_id_for_scheduler(id=reminder_id),
                    expires_at=reminder_model.expire_at,
                    task=self.get_reminder_callback(
                        reminder=reminder_model.reminder,
                        channel_id=reminder_model.channel_id,
                        user_id=reminder_model.owner_id,
                        id=reminder_model.id,
                    ),
                )
            )
        except ValueError:
            await interaction.response.send_message(
                "Sorry, reminder with this ID doesn't exist."
            )

    async def populate_scheduler(self):
        await self.bot.wait_until_ready()
        reminders = await self.repository.get_all_active_reminders()
        scheduler = self._get_scheduler()
        for reminder in reminders:
            channel = self.bot.get_channel(reminder.channel_id)
            user = self.bot.get_user(reminder.owner_id)
            if channel is None or user is None:
                await self.repository.remove_reminder(reminder.id)
                continue
            scheduler.schedule_item(
                SchedulerTask(
                    id=self._create_id_for_scheduler(id=reminder.id),
                    expires_at=reminder.expire_at,
                    task=partial(
                        self._reminder_callback,
                        reminder=reminder.reminder,
                        channel=channel,
                        user=user,
                        id=reminder.id,
                    ),
                )
            )
