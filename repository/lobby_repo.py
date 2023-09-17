from collections.abc import Sequence
from datetime import datetime, timedelta

from sqlalchemy import Result, delete, func, text, update
from sqlalchemy.future import select

from exceptions.lobby_exceptions import (GuildNotFound, LobbyCreationError,
                                         LobbyNotFound, MemberNotFound)
from repository.table.game_lobby_tables import (GuildModel, LobbyModel,
                                                MemberLobbyModel, MemberModel,
                                                QueueMemberLobbyModel)


class LobbyPostgresRepository:
    def __init__(self, session):
        self.database = session

    async def get_lobby(self, lobby_id: int) -> LobbyModel:
        async with self.database() as session:
            result: Result = await session.execute(
                select(LobbyModel).where(LobbyModel.id == lobby_id)
            )
            lobby = result.scalars().first()

            if not lobby:
                raise LobbyNotFound(lobby_id)
            return lobby

    async def get_next_lobby_id(self) -> int:
        async with self.database() as session:
            result: Result = await session.execute(
                text(
                    """SELECT last_value FROM lobby_id_seq""",
                )
            )
            max_id = result.scalars().first()
            if max_id is None:
                raise ValueError("Could not get current value of lobby_id_seq sequence")
            else:
                return max_id + 1

    async def get_all_lobbies(self) -> Sequence[LobbyModel]:
        async with self.database() as session:
            result: Result = await session.execute(select(LobbyModel))
            return result.scalars().unique().all()  # type: ignore

    async def get_all_lobbies_by_guild(self, guild_id: int) -> list[LobbyModel | None]:
        async with self.database() as session:
            result: Result = await session.execute(
                select(LobbyModel).where(LobbyModel.id == guild_id)
            )
            return result.scalars().unique().all()  # type: ignore

    async def get_lobbies_by_member(self, member_id: int) -> list[LobbyModel | None]:
        async with self.database() as session:
            result: Result = await session.execute(
                select(LobbyModel).filter(
                    LobbyModel.members.any(MemberModel.id == member_id)
                )
            )
            return result.scalars().unique().all()  # type: ignore

    async def create_lobby(
        self,
        control_panel_message_id: int,
        original_channel_id: int,
        lobby_channel_id: int,
        guild_id: int,
        guild_name: str,
        user_id: int,
        game_id: int,
        max_size: int,
        description: str,
    ) -> int:
        async with self.database() as session:
            # Check if guild is already in the database
            try:
                guild = await self.get_guild(guild_id)
            except GuildNotFound:
                guild = GuildModel(id=guild_id, name=guild_name)
                session.add(guild)

            # Check if member is already in the database
            try:
                member = await self.get_member(user_id)
            except MemberNotFound:
                member = MemberModel(id=user_id)
                session.add(member)

            await session.flush()

            # Create a new lobby model
            lobby_data = LobbyModel(
                control_panel_message_id=control_panel_message_id,
                owner_id=member.id,
                original_channel_id=original_channel_id,
                lobby_channel_id=lobby_channel_id,
                game_id=game_id,
                game_size=max_size,
                guild_id=guild.id,
                description=description,
                created_datetime=datetime.utcnow(),
            )
            # Add owner to the lobby
            lobby_data.members.append(member)
            session.add(lobby_data)
            await session.commit()

            if lobby_data.id is None:
                raise LobbyCreationError("Lobby creation failed")
            return lobby_data.id

    async def get_guild_id(self, lobby_id: int) -> int:
        async with self.database() as session:
            result: Result = await session.execute(
                select(LobbyModel.guild_id).where(  # type: ignore
                    LobbyModel.id == lobby_id
                )
            )
            guild_id = result.scalars().first()
            if not guild_id:
                raise GuildNotFound(lobby_id)
        return guild_id

    async def get_guild(self, guild_id: int) -> GuildModel:
        async with self.database() as session:
            result: Result = await session.execute(
                select(GuildModel).where(GuildModel.id == guild_id)
            )
            guild = result.scalars().first()
            if not guild:
                raise GuildNotFound(guild_id)
        return guild

    async def delete_lobby(self, lobby_id: int) -> None:
        async with self.database() as session:
            await session.execute(delete(LobbyModel).where(LobbyModel.id == lobby_id))
            await session.commit()

    async def get_thread_id(self, lobby_id: int) -> int | None:
        async with self.database() as session:
            result: Result = await session.execute(
                select(LobbyModel.history_thread_id).where(LobbyModel.id == lobby_id)
            )
            history_thread_id = result.scalars().first()
            return history_thread_id

    async def set_thread_id(self, lobby_id: int, thread_id: int) -> None:
        async with self.database() as session:
            await session.execute(
                update(LobbyModel)  # type: ignore
                .where(LobbyModel.id == lobby_id)
                .values(history_thread_id=thread_id)
            )
            await session.commit()

    async def get_game_id(self, lobby_id: int) -> int:
        async with self.database() as session:
            result: Result = await session.execute(
                select(LobbyModel.game_id).where(LobbyModel.id == lobby_id)
            )
            game_id = result.scalars().first()
            if not game_id:
                raise AttributeError("Lobby has no game id")
            return game_id

    async def set_game_id(self, lobby_id: int, game_id: int) -> int:
        async with self.database() as session:
            result = await session.execute(
                update(LobbyModel)  # type: ignore
                .where(LobbyModel.id == lobby_id)
                .values(game_id=game_id)
                .returning(LobbyModel.game_id)
            )
            await session.commit()
            return result.scalars().first()

    async def get_gamesize(self, lobby_id: int) -> int:
        async with self.database() as session:
            result: Result = await session.execute(
                select(LobbyModel.game_size).where(LobbyModel.id == lobby_id)
            )
            gamesize = result.scalars().first()
            if not gamesize:
                raise AttributeError("Lobby has no game size")
            return gamesize

    async def set_gamesize(self, lobby_id: int, game_size: int) -> int:
        async with self.database() as session:
            result = await session.execute(
                update(LobbyModel)  # type: ignore
                .where(LobbyModel.id == lobby_id)
                .values(game_size=game_size)
                .returning(LobbyModel.game_size)
            )
            await session.commit()
            game_size = result.scalars().first()
            if not result:
                raise AttributeError("Lobby has no game size")
            return game_size

    async def get_description(self, lobby_id: int) -> str | None:
        async with self.database() as session:
            result: Result = await session.execute(
                select(LobbyModel.description).where(LobbyModel.id == lobby_id)
            )
            return result.scalars().first()

    async def set_description(self, lobby_id: int, description: str) -> str:
        async with self.database() as session:
            result: Result = await session.execute(
                update(LobbyModel)  # type: ignore
                .where(LobbyModel.id == lobby_id)
                .values(description=description)
                .returning(
                    LobbyModel.description,
                )
            )
            description = result.scalars().first()  # type: ignore
            if not description:
                raise AttributeError("Failed to set description")
            await session.commit()
            return description

    async def get_owner(self, lobby_id: int) -> MemberModel:
        async with self.database() as session:
            result: Result = await session.execute(
                select(MemberModel)  # type: ignore
                .filter(LobbyModel.owner_id == MemberModel.id)
                .filter(LobbyModel.id == lobby_id)
            )
            owner = result.scalars().first()
            if not owner:
                raise LobbyNotFound(lobby_id)

            return owner

    async def set_owner(self, lobby_id: int, member_id: int) -> int:
        async with self.database() as session:
            lobby = await self.get_lobby(lobby_id)
            lobby.owner_id = member_id
            session.add(lobby)
            await session.commit()
            if not lobby.owner_id:
                raise AttributeError("Failed to set owner")
            return lobby.owner_id

    async def search_new_owner(self, lobby_id: int) -> int | None:
        async with self.database() as session:
            result = await session.execute(
                select(MemberModel)  # type: ignore
                .filter(MemberLobbyModel.lobby_id == lobby_id)
                .filter(MemberLobbyModel.member_id == MemberModel.id)
                .order_by(MemberLobbyModel.join_datetime)
            )
            members = result.scalars().fetchmany()
            owner = await self.get_owner(lobby_id)

            for member in members:
                # If the member is a owner of a another lobby, skip them
                if await self.is_owner_of_lobby(member.id):
                    continue
                if not member.id == owner.id:
                    return member.id
            else:
                return None

    async def get_member(self, member_id: int) -> MemberModel:
        async with self.database() as session:
            result: Result = await session.execute(
                select(MemberModel).filter(MemberModel.id == member_id)
            )
            member = result.scalars().first()
            if not member:
                raise MemberNotFound(member_id)
            return member

    async def get_members(self, lobby_id: int) -> Sequence[MemberModel]:
        async with self.database() as session:
            result: Result = await session.execute(
                select(MemberModel)  # type: ignore
                .filter(MemberLobbyModel.lobby_id == lobby_id)
                .filter(MemberLobbyModel.member_id == MemberModel.id)
            )
            return result.scalars().all()

    async def get_queue_member(
        self, lobby_id: int, member_id: int
    ) -> MemberModel | None:
        async with self.database() as session:
            member = await self.get_member(member_id)
            if not member:
                raise MemberNotFound(member_id)
            result: Result = await session.execute(
                select(MemberModel)  # type: ignore
                .filter(QueueMemberLobbyModel.lobby_id == lobby_id)
                .filter(QueueMemberLobbyModel.member_id == member.id)
                .filter(QueueMemberLobbyModel.member_id == MemberModel.id)
            )
            return result.scalars().first()

    async def is_lobby_locked(self, lobby_id: int) -> bool:
        async with self.database() as session:
            result: Result = await session.execute(
                select(LobbyModel.is_locked).where(LobbyModel.id == lobby_id)
            )

            is_lobby_locked = result.scalars().first()

            if is_lobby_locked is None:
                raise LobbyNotFound(lobby_id)

            return is_lobby_locked

    async def set_is_lobby_locked(self, lobby_id: int, is_locked: bool) -> bool:
        async with self.database() as session:
            result: Result = await session.execute(
                update(LobbyModel)  # type: ignore
                .where(LobbyModel.id == lobby_id)
                .values(is_locked=is_locked)
                .returning(LobbyModel.is_locked)
            )
            is_lobby_locked = result.scalars().first()
            if is_lobby_locked is None:
                raise AttributeError("Failed to set is_lobby_locked")
            await session.commit()
            return is_lobby_locked

    async def get_lobby_channel_id(self, lobby_id: int) -> int:
        async with self.database() as session:
            result: Result = await session.execute(
                select(LobbyModel.lobby_channel_id).where(LobbyModel.id == lobby_id)
            )
            lobby_channel_id = result.scalars().first()
            if not lobby_channel_id:
                raise LobbyNotFound(lobby_id)
            return lobby_channel_id

    async def get_original_channel_id(self, lobby_id: int) -> int:
        async with self.database() as session:
            result: Result = await session.execute(
                select(LobbyModel.original_channel_id).where(LobbyModel.id == lobby_id)
            )
            original_channel_id = result.scalars().first()
            if not original_channel_id:
                raise LobbyNotFound(lobby_id)
            return original_channel_id

    async def get_control_panel_message_id(self, lobby_id: int) -> int:
        async with self.database() as session:
            result: Result = await session.execute(
                select(LobbyModel.control_panel_message_id).where(
                    LobbyModel.id == lobby_id
                )
            )
            control_panel_message_id = result.scalars().first()
            if not control_panel_message_id:
                raise LobbyNotFound(lobby_id)
            return control_panel_message_id

    async def set_control_panel_message_id(
        self, lobby_id: int, control_panel_message_id: int
    ) -> None:
        async with self.database() as session:
            await session.execute(
                update(LobbyModel)  # type: ignore
                .where(LobbyModel.id == lobby_id)
                .values(control_panel_message_id=control_panel_message_id)
            )

    async def get_embed_message_id(self, lobby_id: int) -> int | None:
        async with self.database() as session:
            result: Result = await session.execute(
                select(LobbyModel.embed_message_id).where(LobbyModel.id == lobby_id)
            )
            embed_message_id = result.scalars().first()
            return embed_message_id

    async def set_embed_message_id(self, lobby_id: int, embed_message_id: int) -> None:
        async with self.database() as session:
            await session.execute(
                update(LobbyModel)  # type: ignore
                .where(LobbyModel.id == lobby_id)
                .values(embed_message_id=embed_message_id)
            )
            await session.commit()

    async def get_queue_message_id(self, lobby_id: int):
        async with self.database() as session:
            result: Result = await session.execute(
                select(LobbyModel.queue_message_id).where(LobbyModel.id == lobby_id)
            )
            return result.scalars().first()

    async def set_queue_message_id(self, lobby_id: int, queue_message_id: int) -> None:
        async with self.database() as session:
            await session.execute(
                update(LobbyModel)  # type: ignore
                .where(LobbyModel.id == lobby_id)
                .values(queue_message_id=queue_message_id)
            )
            await session.commit()

    async def get_last_promotion_message_id(self, lobby_id: int) -> int | None:
        async with self.database() as session:
            result: Result = await session.execute(
                select(LobbyModel.last_promotion_message_id).where(
                    LobbyModel.id == lobby_id
                )
            )
            return result.scalars().first()

    async def set_last_promotion_message_id(
        self, lobby_id: int, lobby_message_id: int
    ) -> None:
        async with self.database() as session:
            await session.execute(
                update(LobbyModel)  # type: ignore
                .where(LobbyModel.id == lobby_id)
                .values(
                    last_promotion_message_id=lobby_message_id,
                    last_promotion_datetime=datetime.now(),
                )
            )
            await session.commit()

    async def can_promote(self, lobby_id: int) -> bool:
        async with self.database() as session:
            result: Result = await session.execute(
                select(LobbyModel.last_promotion_datetime).where(
                    LobbyModel.id == lobby_id
                )
            )
            last_promotion_datetime = result.scalars().first()

            if not last_promotion_datetime:
                return True

            if last_promotion_datetime is None or (
                datetime.now() - last_promotion_datetime
            ) > timedelta(minutes=10):
                return True
            else:
                return False

    async def has_joined(self, lobby_id: int, member_id: int) -> bool:
        async with self.database() as session:
            exists_in_memberlobby: Result = await session.execute(
                select(MemberLobbyModel.member_id)  # type: ignore
                .filter(MemberLobbyModel.lobby_id == lobby_id)
                .filter(MemberLobbyModel.member_id == member_id)
            )
            exists_in_queuememberlobby: Result = await session.execute(
                select(QueueMemberLobbyModel.member_id)  # type: ignore
                .filter(QueueMemberLobbyModel.lobby_id == lobby_id)
                .filter(QueueMemberLobbyModel.member_id == member_id)
            )
            has_joined_in_memberlobby = exists_in_memberlobby.scalars().first()
            has_joined_in_queuememberlobby = (
                exists_in_queuememberlobby.scalars().first()
            )

            if has_joined_in_memberlobby or has_joined_in_queuememberlobby:
                return True
            else:
                return False

    async def add_member(self, lobby_id: int, member_id: int) -> None:
        async with self.database() as session:
            try:
                member = await self.get_member(member_id)
            except MemberNotFound:
                member = MemberModel(id=member_id)
                session.add(member)
                await session.flush()

            lobby = await self.get_lobby(lobby_id)
            session.add(lobby)
            lobby.members.append(member)
            await session.commit()

    async def add_queue_member(self, lobby_id: int, member_id: int) -> None:
        async with self.database() as session:
            try:
                member = await self.get_member(member_id)
            except MemberNotFound:
                member = MemberModel(id=member_id)
                session.add(member)
                await session.flush()

            lobby = await self.get_lobby(lobby_id)
            session.add(lobby)
            lobby.queue_members.append(member)
            await session.commit()

    async def get_queue_members(self, lobby_id: int) -> list[MemberModel]:
        async with self.database() as session:
            result = await session.execute(
                select(MemberModel)  # type: ignore
                .filter(QueueMemberLobbyModel.lobby_id == lobby_id)
                .filter(QueueMemberLobbyModel.member_id == MemberModel.id)
                .order_by(QueueMemberLobbyModel.join_datetime)
            )
            return result.scalars().fetchall()

    async def move_queue_members(self, lobby_id: int) -> None:
        lobby = await self.get_lobby(lobby_id)
        game_size = lobby.game_size

        empty_slots = game_size - len(lobby.members)
        if empty_slots <= 0:
            return

        queue_members_ordered_by_datetime = await self.get_queue_members(lobby_id)

        for member in queue_members_ordered_by_datetime:
            await self.remove_queue_member(lobby_id, member.id)
            await self.add_member(lobby_id, member.id)
            if await self.is_full(lobby_id):
                break

    async def remove_queue_member(self, lobby_id: int, member_id: int) -> None:
        member = await self.get_queue_member(lobby_id, member_id)
        lobby = await self.get_lobby(lobby_id)
        async with self.database() as session:
            if member in lobby.queue_members:
                session.add(lobby)
                lobby.queue_members.remove(member)
                await session.commit()

    async def remove_member(self, lobby_id: int, member_id: int) -> None:
        try:
            member = await self.get_member(member_id)
            lobby = await self.get_lobby(lobby_id)

            async with self.database() as session:
                if member in lobby.members:
                    session.add(lobby)
                    lobby.members.remove(member)
                    await session.commit()
        except MemberNotFound:
            raise MemberNotFound(member_id)

    async def set_member_state(self, lobby_id: int, member_id: int) -> bool:
        is_ready = await self.get_member_state(lobby_id, member_id)
        async with self.database() as session:
            result: Result = await session.execute(
                update(MemberLobbyModel)  # type: ignore
                .where(
                    MemberLobbyModel.member_id == member_id,
                    MemberLobbyModel.lobby_id == lobby_id,
                )
                .values(ready=not is_ready)
                .returning(
                    MemberLobbyModel.ready,
                )
            )
            await session.commit()
            is_ready = result.scalars().first()  # type: ignore
            if is_ready is None:
                raise MemberNotFound(member_id)
            return is_ready

    async def get_member_state(self, lobby_id: int, member_id: int) -> bool:
        async with self.database() as session:
            member = await self.get_member(member_id)
            if not member:
                raise MemberNotFound(member_id)

            result: Result = await session.execute(
                select(MemberLobbyModel)  # type: ignore
                .filter(MemberLobbyModel.member_id == member.id)
                .filter(MemberLobbyModel.lobby_id == lobby_id)
            )
            member_lobby_model = result.scalars().first()

            if member_lobby_model:
                return member_lobby_model.ready
            else:
                raise MemberNotFound(member_id)

    async def is_full(self, lobby_id: int) -> bool:
        async with self.database() as session:
            result: Result = await session.execute(
                select(LobbyModel).filter(LobbyModel.id == lobby_id)
            )
            lobby = result.scalars().first()

            if not lobby:
                raise LobbyNotFound(lobby_id)

            if lobby.game_size == 0:
                return False
            else:
                return len(lobby.members) >= lobby.game_size

    async def get_session_time(self, lobby_id: int) -> datetime:
        async with self.database() as session:
            result: Result = await session.execute(
                select(LobbyModel.created_datetime).filter(LobbyModel.id == lobby_id)
            )
            created_datetime = result.scalars().first()

            if not created_datetime:
                raise LobbyNotFound(lobby_id)

            return created_datetime

    async def has_joined_vc(self, lobby_id: int, member_id: int) -> bool:
        async with self.database() as session:
            result: Result = await session.execute(
                select(MemberLobbyModel.has_joined_vc)  # type: ignore
                .filter(MemberLobbyModel.lobby_id == lobby_id)
                .filter(MemberLobbyModel.member_id == member_id)
            )
            has_joined_vc = result.scalars().first()

            if has_joined_vc is None:
                raise MemberNotFound(member_id)
            return has_joined_vc

    async def set_has_joined_vc(
        self, lobby_id: int, member_id: int, has_joined_vc: bool
    ) -> bool:
        async with self.database() as session:
            result: Result = await session.execute(
                update(MemberLobbyModel)  # type: ignore
                .values(has_joined_vc=has_joined_vc)
                .filter(MemberLobbyModel.lobby_id == lobby_id)
                .filter(MemberLobbyModel.member_id == member_id)
                .returning(MemberLobbyModel.has_joined_vc)
            )
            updated_has_joined_vc = result.scalars().first()

            if not updated_has_joined_vc:
                raise ValueError("Member not in a lobby")
            return updated_has_joined_vc

    async def get_members_not_ready(self, lobby_id: int) -> Sequence[int]:
        async with self.database() as session:
            result: Result = await session.execute(
                select(MemberLobbyModel.member_id)  # type: ignore
                .filter(MemberLobbyModel.lobby_id == lobby_id)
                .filter(MemberLobbyModel.ready == False)  # noqa
            )
            return result.scalars().all()

    async def get_members_ready(self, lobby_id: int) -> Sequence[int]:
        async with self.database() as session:
            result: Result = await session.execute(
                select(MemberLobbyModel.member_id)  # type: ignore
                .filter(MemberLobbyModel.lobby_id == lobby_id)
                .filter(MemberLobbyModel.ready == True)  # noqa
            )
            members = result.scalars().all()
            print(members)
            return members

    async def is_owner_of_lobby(self, member_id: int) -> bool:
        async with self.database() as session:
            result: Result = await session.execute(
                select(LobbyModel).filter(  # type: ignore
                    LobbyModel.owner_id == member_id
                )
            )
            return result.scalars().first() is not None

    async def get_lobbies_count(self) -> int:
        async with self.database() as session:
            result: Result = await session.execute(
                select(func.count(LobbyModel.id)).select_from(  # type: ignore
                    LobbyModel
                )
            )
            count = result.scalar()
            return count if count else 0

    async def get_lobby_by_owner_id(self, owner_id: int) -> LobbyModel:
        async with self.database() as session:
            result: Result = await session.execute(
                select(LobbyModel).filter(  # type: ignore
                    LobbyModel.owner_id == owner_id
                )
            )
            lobby_model = result.scalars().first()
            if not lobby_model:
                raise LobbyNotFound(f"owner_id {owner_id}")
            return lobby_model

    async def get_lobby_id_by_owner_id(self, owner_id: int) -> int:
        async with self.database() as session:
            result: Result = await session.execute(
                select(LobbyModel.id).filter(  # type: ignore
                    LobbyModel.owner_id == owner_id
                )
            )
            lobby_id = result.scalar()
            if not lobby_id:
                raise LobbyNotFound(f"owner_id {owner_id}")
            return lobby_id
