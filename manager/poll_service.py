from discord import Guild
from discord.ext import commands

from repository.poll_repo import PollRepository
from repository.poll_table import PollAnswerModel, PollModel, VoteType


class PollManager:

    def __init__(
        self,
        bot: commands.Bot,
        repository: PollRepository
    ) -> None:
        self.bot = bot
        self.repository = repository

    async def get_all_polls_by_guild_id(self, guild_id: int) -> list[PollModel]:
        return await self.repository.get_all_polls_by_guild_id(guild_id)
    
    async def get_all_active_polls(self) -> list[PollModel]:
        return await self.repository.get_all_active_polls()
    
    async def get_all_active_polls_by_guild_id(self, guild_id: int) -> list[PollModel]:
        return await self.repository.get_all_active_polls_by_guild_id(guild_id)

    async def get_poll(self, poll_id: int) -> PollModel:
        return await self.repository.get_poll(poll_id)

    async def create_poll(
        self,
        colour: str,
        guild: Guild,
        owner_id: int,
        question: str,
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
            vote_type=vote_type,
            colour=colour
        )
    async def get_poll_answers(self, poll_id: int) -> list[PollAnswerModel]:
        return await self.repository.get_poll_answers(poll_id)
    
    async def get_answers_by_poll_id(self, poll_id: int) -> list[PollAnswerModel]:
        return await self.repository.get_answers_by_poll_id(poll_id)
    
    async def get_poll_answer_by_user_id(self, poll_id: int, user_id: int) -> list[PollAnswerModel]:
        return await self.repository.get_poll_answer_by_user_id(poll_id, user_id)

    async def get_poll_answer(self, answer_id: int) -> str:
        return await self.repository.get_poll_answer(answer_id)

    async def add_answer(
        self,
        answer: str,
        owner_id: int,
        poll_id: int,
    ) -> int:
        return await self.repository.add_poll_answer(
            answer=answer,
            poll_id=poll_id,
            owner_id=owner_id
        )
    
    async def remove_answer(
        self,
        answer_id: int
    ):
        return await self.repository.remove_poll_answer(answer_id)
    
    async def add_url(
        self,
        answer_id: int,
        url: str
    ):
        return await self.repository.add_url(answer_id, url)
    
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
        poll_id: int,
        answer_id: int,
        member_id: int,
        vote_type: VoteType,
    ):
        if vote_type is VoteType.SINGLE_VOTE:
            # Check if user has already voted
            user_votes = await self.repository.get_poll_votes_by_member_id(poll_id, member_id)
            # If user has already voted, remove their vote
            if user_votes is not None:
                for vote in user_votes:
                    await self.repository.remove_vote(
                        answer_id=vote.id,
                        member_id=member_id
                    )
            # Add new vote
            await self.repository.add_vote(
                    answer_id,
                    member_id,
                )
        elif vote_type is VoteType.MULTIPLE_VOTE:
            # Check if user has already voted
            user_vote = await self.repository.has_voted(answer_id, member_id)
            if user_vote:
                return
            await self.repository.add_vote(
                    answer_id,
                    member_id,
                )
        else:
            raise NotImplementedError("Invalid vote type")

    async def get_vote(
        self,
        answer_id: int,
    ) -> int:
        return await self.repository.get_vote(answer_id)
    
    async def has_voted(
        self,
        answer_id: int,
        member_id: int
    ) -> bool:
        return await self.repository.has_voted(answer_id, member_id)
    
    async def end_poll(
        self,
        poll_id: int,
    ) -> None:
        await self.repository.end_poll(poll_id)
