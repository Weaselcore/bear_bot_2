from collections import Counter

from discord import Colour, Embed, Guild
from discord.ext import commands

from repository.poll_repo import PollRepository
from repository.poll_table import (PollAnswerModel, PollMemberAnswerModel,
                                   PollModel, VoteType)


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
    
    async def get_owner_id(self, poll_id: int) -> int:
        return await self.repository.get_owner_id(poll_id)

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
        member_id: int,
        answer_id: int
    ) -> bool:
        is_owner = await self.repository.is_owner_of_answer(member_id, answer_id)
        if is_owner:
            await self.repository.remove_poll_answer(answer_id)
            return True
        return False

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
        match vote_type:
            case VoteType.SINGLE_VOTE:
                # Get all votes by user
                user_votes = await self.repository.get_poll_votes_by_member_id(poll_id, member_id)
                # If user has already voted, remove their vote
                if user_votes == []:
                    # Add new vote
                    await self.repository.add_vote(
                        answer_id,
                        member_id,
                    )
                    return
                else:
                    # If vote_types are able to switch, this will remove all previous votes
                    for vote in user_votes:
                        await self.repository.remove_vote(
                            answer_id=vote.id,
                            member_id=vote.member_id
                        )
                    await self.repository.add_vote(
                        answer_id,
                        member_id,
                    )
            case VoteType.MULTIPLE_VOTE:
                # Check if user has already voted
                user_vote = await self.repository.get_member_vote(answer_id, member_id)
                if user_vote:
                    await self.repository.remove_vote(answer_id=user_vote.id, member_id=member_id)
                else:
                    await self.repository.add_vote(
                        answer_id,
                        member_id,
                    )
            case _:
                raise NotImplementedError(f"{vote_type} is an invalid vote type")

    async def get_vote(
        self,
        answer_id: int,
    ) -> int:
        return await self.repository.get_vote(answer_id)
    
    async def get_poll_votes(
            self,
            poll_id: int,
    ) -> list[PollMemberAnswerModel]:
        return await self.repository.get_poll_votes(poll_id)

    async def end_poll(
        self,
        poll_id: int,
    ) -> None:
        await self.repository.end_poll(poll_id)

    async def get_poll_result_embed(
        self,
        poll_id: int,
    ) -> Embed:
        poll_votes: list[PollMemberAnswerModel] = await self.get_poll_votes(poll_id)
        results: dict[int, list[int]] = {}
        winner: str = ''

        for poll_vote in poll_votes:
            list_of_voters = results.get(poll_vote.poll_answer_id, [])
            list_of_voters.append(poll_vote.member_id)
            results[poll_vote.poll_answer_id] = list_of_voters

        counts: list[tuple[int, int]] = Counter(results).most_common()

        if len(counts) == 1:
            winner = await self.get_poll_answer(int(counts[0][0]))
        else:
            # There has been a tie
            for i in range(len(counts)):
                winner += f'{await self.get_poll_answer(int(counts[i][0]))}, '

        embed = Embed(
            title=f"📖  Poll Results: {(await self.get_poll(poll_id)).question}",
            description=f" 🥇  Winner(s): {winner}",
            colour=Colour.green()
        )
        value_string = '⠀⠀⠀⠀⤷  ✍  Votes:\n'
        # Print out members who voted for each answer
        for key, values in results.items():
            for value in values:
                value_string += f'⠀⠀⠀⠀⠀⠀⠀⠀⤷   <@{value}>\n'
            embed.add_field(
                name=f"Answer  ➡  {await self.get_poll_answer(key)}",
                value=value_string,
                inline=False,
            )
            value_string = '⠀⠀⠀⠀⤷  ✍  Votes:\n'

        embed.set_footer(text=f"[Poll ID: {poll_id}]")
        return embed


