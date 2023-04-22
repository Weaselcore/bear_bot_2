from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from repository.poll_table import (
    PollAnswerModel,
    PollGuildModel,
    PollMemberAnswerModel,
    PollModel,
    PollType,
    VoteType
)


class PollRepository:

    def __init__(self, database: async_sessionmaker[AsyncSession]):
        self.database = database

    async def get_guild(self, guild_id: int) -> PollGuildModel | None:
        async with self.database() as session:
            async with session.begin():
                guild = await session.get(PollGuildModel, guild_id)
                return guild

    async def add_guild(self, guild_id: int, guild_name: str) -> int:
        async with self.database() as session:
            async with session.begin():
                session.add(
                    PollGuildModel(
                        id=guild_id,
                        name=guild_name,
                    )
                )
                await session.commit()
                return guild_id
            
    async def get_all_polls_by_guild_id(self, guild_id: int) -> list[PollModel]:
        async with self.database() as session:
            async with session.begin():
                result = await session.execute(
                    select(PollModel).where(
                        PollModel.guild_id == guild_id
                    )
                )
                return list(result.scalars().all())
            
    async def get_all_active_polls(self) -> list[PollModel]:
        async with self.database() as session:
            async with session.begin():
                result = await session.execute(
                    select(PollModel).where(PollModel.is_active == True)
                )
                return list(result.scalars().all())
            
    async def get_poll(self, poll_id: int) -> PollModel:
        async with self.database() as session:
            async with session.begin():
                poll = await session.get(PollModel, poll_id)
                if poll is None:
                    raise ValueError(f"Poll with id {poll_id} does not exist")
                return poll

    async def create_poll(
        self,
        question: str,
        owner_id: int,
        guild_id: int,
        poll_type: PollType,
        vote_type: VoteType,
    ) -> int:
        async with self.database() as session:
            async with session.begin():
                poll = PollModel(
                    question=question,
                    owner_id=owner_id,
                    guild_id=guild_id,
                    poll_type=poll_type,
                    vote_type=vote_type,
                )
                session.add(poll)
                await session.commit()
                return poll.id

    async def get_channel_message_id(
        self,
        poll_id: int,
    ) -> tuple[int, int]:
        async with self.database() as session:
            async with session.begin():
                poll = await session.get(PollModel, poll_id)
                if poll is None:
                    raise ValueError(f"Poll with id {poll_id} does not exist")
                return (poll.message_id, poll.channel_id,)

    async def set_channel_message_id(
        self,
        poll_id: int,
        message_id: int,
        channel_id: int,
    ) -> None:
        async with self.database() as session:
            async with session.begin():
                poll = await session.get(PollModel, poll_id)
                if poll is None:
                    raise ValueError(f"Poll with id {poll_id} does not exist")
                poll.message_id = message_id
                poll.channel_id = channel_id
                await session.commit()

    async def get_poll_answers(self, poll_id: int) -> list[PollAnswerModel]:
        async with self.database() as session:
            async with session.begin():
                result = await session.execute(
                    select(PollAnswerModel).where(
                        PollAnswerModel.poll_id == poll_id
                    )
                )
                return list(result.scalars().all())
    
    async def get_answers_by_poll_id(self, poll_id: int) -> list[PollAnswerModel]:
        async with self.database() as session:
            async with session.begin():
                result = await session.execute(
                    select(PollAnswerModel).where(
                        PollAnswerModel.poll_id == poll_id
                    )
                )
                return list(result.scalars().all())
            
    async def add_poll_answer(
        self,
        poll_id: int,
        answer: str,
    ) -> int:
        async with self.database() as session:
            async with session.begin():
                poll_answer = PollAnswerModel(
                    poll_id=poll_id,
                    answer=answer,
                )
                session.add(poll_answer)
                await session.commit()
                return poll_answer.id

    async def remove_poll_answer(
        self,
        answer_id: int,
    ):
        async with self.database() as session:
            async with session.begin():
                poll_answer = await session.get(PollAnswerModel, answer_id)
                if poll_answer is None:
                    raise ValueError(
                        f"Poll answer with id {answer_id} does not exist")
                await session.delete(poll_answer)
                await session.commit()

    async def get_poll_answer(self, answer_id: int) -> str:
        async with self.database() as session:
            async with session.begin():
                poll_answer = await session.get(PollAnswerModel, answer_id)
                if poll_answer is None:
                    raise ValueError(
                        f"Poll answer with id {answer_id} does not exist")
                return poll_answer.answer

    async def add_vote(
        self,
        poll_answer_id: int,
        member_id: int,
    ) -> None:
        async with self.database() as session:
            async with session.begin():
                session.add(
                    PollMemberAnswerModel(
                        poll_answer_id=poll_answer_id,
                        member_id=member_id,
                    )
                )
                await session.commit()

    async def get_vote(
        self,
        poll_answer_id: int,
    )-> int:
        async with self.database() as session:
            async with session.begin():
                result = await session.execute(
                    select(PollMemberAnswerModel).where(
                        PollMemberAnswerModel.poll_answer_id == poll_answer_id
                    )
                )
                return len(result.scalars().all())