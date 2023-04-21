from discord import Guild
from discord.ext import commands

from repository.poll_repo import PollRepository
from repository.poll_table import PollAnswerModel, PollModel, PollType, VoteType


class PollManager:

    def __init__(
        self,
        bot: commands.Bot,
        repository: PollRepository
    ) -> None:
        self.bot = bot
        self.repository = repository

    async def get_poll(self, poll_id: int) -> PollModel:
        return await self.repository.get_poll(poll_id)

    async def create_poll(
        self,
        question: str,
        owner_id: int,
        guild: Guild,
        poll_type: PollType,
        vote_type: VoteType,
    ) -> int:

        new_guild_id = None

        guild_model = await self.repository.get_guild(guild_id=guild.id)

        if guild_model is None:
            new_guild_id = await self.repository.add_guild(guild.id, guild_name=guild.name)

        return await self.repository.create_poll(
            question=question,
            owner_id=owner_id,
            guild_id=new_guild_id or guild.id,
            poll_type=poll_type,
            vote_type=vote_type,
        )
    async def get_poll_answers(self, poll_id: int) -> list[PollAnswerModel]:
        return await self.repository.get_poll_answers(poll_id)

    async def add_answer(
        self,
        poll_id: int,
        answer: str
    ) -> int:
        return await self.repository.add_poll_answer(poll_id, answer)
    
    async def remove_answer(
        self,
        answer_id: int
    ):
        return await self.repository.remove_poll_answer(answer_id)
    
    async def get_channel_message_id(
        self,
        poll_id: int,
    ) -> tuple[int, int]:
        return await self.repository.get_channel_message_id(poll_id)
    
    async def set_channel_message_id(
        self,
        poll_id: int,
        channel_id: int,
        message_id: int
    ) -> None:
        await self.repository.set_channel_message_id(
            poll_id=poll_id,
            channel_id=channel_id,
            message_id=message_id
        )
    
    async def add_vote(
        self,
        answer_id: int,
        member_id: int
    ):
       await self.repository.add_vote(answer_id, member_id)

    async def get_vote(
        self,
        answer_id: int,
    ) -> int:
        return await self.repository.get_vote(answer_id)
    
    async def update_poll_view(
        self,
        poll_id: int,
    ):
        pass
