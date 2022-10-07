import discord
from model.lobby_model import LobbyManager


# self.lobby_to_promote: list[Promotion] = []
# self.task = bot.loop.create_task(self.promotion_scheduler())
# self.has_schedule = asyncio.Event()

async def scheduler(self):
    await self.bot.wait_until_ready()

    while not self.bot.is_closed():
        # Get the next item to be scheduled
        self.current_promotion = await self.get_oldest_schedule()
        # Promote immediately if the lobby hasn't been promoted before
        if not self.current_promotion.has_promoted:
            await self._promote()
            self.current_promotion.has_promoted = True
        # Sleep till the promotion is due to be executed
        await discord.utils.sleep_until(self.current_promotion.date_time)
        # If the item is still in the list, promote it.
        if self.current_promotion in self.lobby_to_promote:
            await self._promote()
            # Recalculate new datetime
            self.current_promotion.update_date_time()


async def _promote(self):
    # Might not be the first time the lobby has been promoted; Delete old ad
    last_message = LobbyManager.get_last_promotion_message(
        self.bot,
        self.current_promotion.lobby_id
    )
    # Try to delete old message
    if last_message:
        try:
            await last_message.delete()
        except discord.errors.NotFound:
            pass
    # Send new ad
    message = await self.current_promotion.original_channel.send(
        content=f'<@&{self.current_promotion.game.role}>',
        embed=PromotionEmbed(
            bot=self.bot,
            promotion=self.current_promotion
        )
    )
    # Store last promotion message
    LobbyManager.set_last_promotion_message(
        self.bot,
        self.current_promotion.lobby_id,
        message
    )


async def get_oldest_schedule(self):
    # If the list is empty, wait for an item to be added
    if len(self.lobby_to_promote) == 0:
        await self.has_schedule.wait()
    # Get the oldest item
    return min(self.lobby_to_promote, key=lambda x: x.date_time)


def schedule_item(self, item):
    # Add item to list and resume the scheduler
    if len(self.lobby_to_promote) == 0:
        self.lobby_to_promote.append(item)
        self.has_schedule.set()
        return
    # Add item to list if the scheduler is running
    self.lobby_to_promote.append(item)
    # If the item is the oldest, cancel the current promotion and start a new one
    if self.current_promotion is not None and item.date_time < self.current_promotion.date_time:
        self.task.cancel()
        self.task = self.bot.loop.create_task(self.promotion_scheduler())


def remove_schedule(self, item):
    try:
        self.lobby_to_promote.remove(item)
    except ValueError:
        pass
    else:
        if len(self.lobby_to_promote) == 0:
            self.has_schedule.clear()
