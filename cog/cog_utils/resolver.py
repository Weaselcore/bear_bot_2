import discord
from discord.ext import commands


async def get_guild_object(bot: commands.Bot, guild_id: int) -> discord.Guild:
    guild_from_cache = bot.get_guild(guild_id)
    if guild_from_cache:
        return guild_from_cache
    guild = await bot.fetch_guild(guild_id)
    if not guild:
        raise ValueError('Guild not found')
    return guild


async def get_channel_object(
    bot: commands.Bot,
    channel_id: int,
) -> discord.TextChannel:
    channel_from_cache = bot.get_channel(channel_id)
    if isinstance(channel_from_cache, discord.TextChannel):
        return channel_from_cache
    try:
        channel = await bot.fetch_channel(channel_id)
        if isinstance(channel, discord.TextChannel):
            return channel
        else:
            raise ValueError('Channel with the right type could not be found')
    except discord.NotFound:
        raise ValueError('Channel not found')


async def get_message_object(
    bot: commands.Bot,
    channel_id: int,
    message_id: int
) -> discord.Message | discord.PartialMessage:

    channel = await get_channel_object(bot, channel_id)

    assert not isinstance(channel, discord.GroupChannel)

    message_from_cache = channel.get_partial_message(message_id)

    if message_from_cache:
        return message_from_cache
    message = await channel.fetch_message(message_id)
    if not message:
        raise ValueError('Message not found')
    return message
