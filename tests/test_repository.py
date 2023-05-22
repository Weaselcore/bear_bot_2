from time import gmtime, strftime
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

import pytest

from repository.lobby_repo import LobbyPostgresRepository


class TestRepository:

    """QUEUE MEMBER TESTS"""

    @pytest.mark.asyncio
    async def test_get_queue_member(self, session: AsyncSession):
        lobbydal = LobbyPostgresRepository(session)
        result = await lobbydal.get_queue_member(1, 321)
        assert result is not None
        assert result.id == 321

    """LOBBY TESTS"""

    @pytest.mark.asyncio
    async def test_get_all_lobbies_number(self, session: AsyncSession):
        lobbydal = LobbyPostgresRepository(session)
        result = await lobbydal.get_all_lobbies()
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_is_lobby_locked(self, session: AsyncSession):
        lobbydal = LobbyPostgresRepository(session)
        result = await lobbydal.is_lobby_locked(1)
        assert result is False

    @pytest.mark.asyncio
    async def test_set_is_lobby_locked(self, session: AsyncSession):
        lobbydal = LobbyPostgresRepository(session)
        await lobbydal.set_is_lobby_locked(1, True)
        result = await lobbydal.is_lobby_locked(1)
        assert result is True

    """RETRIEVE LOBBY ATTRIBUTES"""

    @pytest.mark.asyncio
    async def test_get_original_channel_id(self, session: AsyncSession):
        lobbydal = LobbyPostgresRepository(session)
        result = await lobbydal.get_original_channel_id(1)
        assert result == 12

    @pytest.mark.asyncio
    async def test_get_lobby_channel_id(self, session: AsyncSession):
        lobbydal = LobbyPostgresRepository(session)
        result = await lobbydal.get_lobby_channel_id(1)
        assert result == 34

    @pytest.mark.asyncio
    async def test_get_control_panel_message_id(self, session: AsyncSession):
        lobbydal = LobbyPostgresRepository(session)
        result = await lobbydal.get_control_panel_message_id(1)
        assert result == 56

    @pytest.mark.asyncio
    async def test_get_embed_message_id(self, session: AsyncSession):
        lobbydal = LobbyPostgresRepository(session)
        result = await lobbydal.get_embed_message_id(1)
        assert result == 78

    @pytest.mark.asyncio
    async def test_set_embed_message_id(self, session: AsyncSession):
        lobbydal = LobbyPostgresRepository(session)
        await lobbydal.set_embed_message_id(1, 999)
        result = await lobbydal.get_embed_message_id(1)
        assert result == 999

    @pytest.mark.asyncio
    async def test_get_queue_message_id(self, session: AsyncSession):
        lobbydal = LobbyPostgresRepository(session)
        result = await lobbydal.get_queue_message_id(1)
        assert result == 91

    @pytest.mark.asyncio
    async def test_get_last_promotion_message_id(self, session: AsyncSession):
        lobbydal = LobbyPostgresRepository(session)
        result = await lobbydal.get_last_promotion_message_id(1)
        assert result is None

    @pytest.mark.asyncio
    async def test_set_last_promotion_message_id(self, session: AsyncSession):
        lobbydal = LobbyPostgresRepository(session)
        await lobbydal.set_last_promotion_message_id(1, 789)
        result = await lobbydal.get_last_promotion_message_id(1)
        assert result == 789

    @pytest.mark.asyncio
    async def test_get_descriptor(self, session: AsyncSession):
        lobbydal = LobbyPostgresRepository(session)
        result = await lobbydal.get_description(1)
        assert result == "test"

    @pytest.mark.asyncio
    async def test_set_descriptor(self, session: AsyncSession):
        lobbydal = LobbyPostgresRepository(session)
        await lobbydal.set_description(1, "new descriptor")
        result = await lobbydal.get_description(1)
        assert result == "new descriptor"

    @pytest.mark.asyncio
    async def test_get_gamesize(self, session: AsyncSession):
        lobbydal = LobbyPostgresRepository(session)
        result = await lobbydal.get_gamesize(1)
        assert result == 5

    @pytest.mark.asyncio
    async def test_set_gamesize(self, session: AsyncSession):
        lobbydal = LobbyPostgresRepository(session)
        await lobbydal.set_gamesize(1, 6)
        result = await lobbydal.get_gamesize(1)
        assert result == 6

    @pytest.mark.asyncio
    async def test_get_game_code(self, session: AsyncSession):
        lobbydal = LobbyPostgresRepository(session)
        result = await lobbydal.get_game_id(1)
        assert result == 1

    @pytest.mark.asyncio
    async def test_set_game_code(self, session: AsyncSession):
        lobbydal = LobbyPostgresRepository(session)
        await lobbydal.set_game_id(1, 2)
        result = await lobbydal.get_game_id(1)
        assert result == 2

    """MEMBER TESTS"""

    @pytest.mark.asyncio
    async def test_get_member_fail(self, session: AsyncSession):
        lobbydal = LobbyPostgresRepository(session)
        with pytest.raises(Exception) as exc_info:
            await lobbydal.get_member(123321)
            assert str(exc_info.value) == "Member with 123321 not found"

    @pytest.mark.asyncio
    async def test_get_member_success(self, session: AsyncSession):
        lobbydal = LobbyPostgresRepository(session)
        result = await lobbydal.get_member(123)
        assert result.id == 123

    @pytest.mark.asyncio
    async def test_add_member(self, session: AsyncSession):
        lobbydal = LobbyPostgresRepository(session)
        await lobbydal.add_member(1, 1234)
        result = await lobbydal.get_member(1234)
        assert result.id == 1234

    @pytest.mark.asyncio
    async def test_remove_member(self, session: AsyncSession):
        lobbydal = LobbyPostgresRepository(session)
        member = await lobbydal.get_member(123)
        await lobbydal.remove_member(1, 123)
        result = await lobbydal.get_lobby(1)
        assert member not in result.members

    @pytest.mark.asyncio
    async def test_add_queue_member(self, session: AsyncSession):
        lobbydal = LobbyPostgresRepository(session)
        await lobbydal.add_queue_member(1, 1234)
        lobby = await lobbydal.get_lobby(1)
        member = await lobbydal.get_member(1234)
        assert member in lobby.queue_members

    @pytest.mark.asyncio
    async def test_remove_queue_member(self, session: AsyncSession):
        lobbydal = LobbyPostgresRepository(session)
        member = await lobbydal.get_member(123)
        await lobbydal.remove_queue_member(1, 123)
        lobby = await lobbydal.get_lobby(1)
        assert member not in lobby.queue_members

    @pytest.mark.asyncio
    async def test_get_members(self, session: AsyncSession):
        lobbydal = LobbyPostgresRepository(session)
        result = await lobbydal.get_members(1)
        assert type(result) is list

    @pytest.mark.asyncio
    async def test_get_members_add_one(self, session: AsyncSession):
        lobbydal = LobbyPostgresRepository(session)
        await lobbydal.add_member(1, 1234)
        result = await lobbydal.get_members(1)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_members_empty(self, session: AsyncSession):
        lobbydal = LobbyPostgresRepository(session)
        await lobbydal.remove_member(1, 123)
        result = await lobbydal.get_members(1)
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_get_member_unready_state(self, session: AsyncSession):
        lobbydal = LobbyPostgresRepository(session)
        result = await lobbydal.get_member_state(1, 123)
        assert result is False

    @pytest.mark.asyncio
    async def test_set_member_state(self, session: AsyncSession):
        lobbydal = LobbyPostgresRepository(session)
        old_state = await lobbydal.get_member_state(1, 123)
        await lobbydal.set_member_state(1, 123)
        new_state = await lobbydal.get_member_state(1, 123)
        assert not old_state == new_state

    @pytest.mark.asyncio
    async def test_get_owner(self, session: AsyncSession):
        lobbydal = LobbyPostgresRepository(session)
        result = await lobbydal.get_owner(1)
        assert result.id == 123

    @pytest.mark.asyncio
    async def test_set_owner(self, session: AsyncSession):
        lobbydal = LobbyPostgresRepository(session)
        await lobbydal.add_member(1, 234)
        await lobbydal.set_owner(1, 234)
        result = await lobbydal.get_owner(1)
        assert result.id == 234

    @pytest.mark.asyncio
    async def test_find_owner_with_no_candidate(self, session: AsyncSession):
        lobbydal = LobbyPostgresRepository(session)
        result = await lobbydal.search_new_owner(1)
        assert result is None

    @pytest.mark.asyncio
    async def test_find_owner_with_candidate(self, session: AsyncSession):
        lobbydal = LobbyPostgresRepository(session)
        await lobbydal.add_member(1, 234)
        result = await lobbydal.search_new_owner(1)
        assert result == 234

    @pytest.mark.asyncio
    async def test_find_owner_by_join_datetime(self, session: AsyncSession):
        lobbydal = LobbyPostgresRepository(session)
        await lobbydal.add_member(1, 234)
        await lobbydal.add_member(1, 345)
        result = await lobbydal.search_new_owner(1)
        assert result == 234

    @pytest.mark.asyncio
    async def test_find_owner_by_join_datetime_incorrect(self, session: AsyncSession):
        lobbydal = LobbyPostgresRepository(session)
        await lobbydal.add_member(1, 234)
        await lobbydal.add_member(1, 345)
        result = await lobbydal.search_new_owner(1)
        assert not result == 345

    """Utility Tests"""

    @pytest.mark.asyncio
    async def test_can_promote(self, session: AsyncSession):
        lobbydal = LobbyPostgresRepository(session)
        result = await lobbydal.can_promote(1)
        assert result is True

    @pytest.mark.asyncio
    async def test_can_promote_fail(self, session: AsyncSession):
        lobbydal = LobbyPostgresRepository(session)
        await lobbydal.set_last_promotion_message_id(1, 123)
        result = await lobbydal.can_promote(1)
        assert result is False

    @pytest.mark.asyncio
    async def test_has_joined(self, session: AsyncSession):
        lobbydal = LobbyPostgresRepository(session)
        result = await lobbydal.has_joined(1, 123)
        assert result is True

    @pytest.mark.asyncio
    async def test_has_joined_fail(self, session: AsyncSession):
        lobbydal = LobbyPostgresRepository(session)
        result = await lobbydal.has_joined(1, 1234)
        assert result is False

    @pytest.mark.asyncio
    async def test_has_joined_queue(self, session: AsyncSession):
        lobbydal = LobbyPostgresRepository(session)
        result = await lobbydal.has_joined(1, 321)
        assert result is True

    @pytest.mark.asyncio
    async def test_has_joined_queue_fail(self, session: AsyncSession):
        lobbydal = LobbyPostgresRepository(session)
        result = await lobbydal.has_joined(1, 4321)
        assert result is False

    @pytest.mark.asyncio
    async def test_is_full_false(self, session: AsyncSession):
        lobbydal = LobbyPostgresRepository(session)
        result = await lobbydal.is_full(1)
        assert result is False

    @pytest.mark.asyncio
    async def test_is_full_fail_true(self, session: AsyncSession):
        lobbydal = LobbyPostgresRepository(session)
        await lobbydal.set_gamesize(1, 1)
        result = await lobbydal.is_full(1)
        assert result is True

    @pytest.mark.asyncio
    async def test_move_queue_member(self, session: AsyncSession):
        lobbydal = LobbyPostgresRepository(session)
        await lobbydal.move_queue_members(1)
        lobby = await lobbydal.get_lobby(1)
        member = await lobbydal.get_member(321)
        assert member in lobby.members

    @pytest.mark.asyncio
    async def test_move_queue_member_fail(self, session: AsyncSession):
        lobbydal = LobbyPostgresRepository(session)
        await lobbydal.set_gamesize(1, 1)
        await lobbydal.move_queue_members(1)
        lobby = await lobbydal.get_lobby(1)
        member = await lobbydal.get_member(321)
        assert member not in lobby.members

    @pytest.mark.asyncio
    async def test_get_session_time(self):
        date_time = datetime.now()
        duration = date_time - (date_time - timedelta(minutes=5))
        result = "Session Duration: " + \
            strftime("%H:%M:%S", gmtime(duration.total_seconds()))
        assert result == "Session Duration: 00:05:00"

    @pytest.mark.asyncio
    async def test_has_joined_vc(self, session: AsyncSession):
        lobbydal = LobbyPostgresRepository(session)
        result = await lobbydal.has_joined_vc(1, 123)
        assert result is False

    @pytest.mark.asyncio
    async def test_set_has_joined_vc(self, session: AsyncSession):
        lobbydal = LobbyPostgresRepository(session)
        await lobbydal.set_has_joined_vc(1, 123, True)
        result = await lobbydal.has_joined_vc(1, 123)
        assert result is True

    @pytest.mark.asyncio
    async def test_get_members_ready_none(self, session: AsyncSession):
        lobbydal = LobbyPostgresRepository(session)
        result = await lobbydal.get_members_ready(1)
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_get_members_ready_success(self, session: AsyncSession):
        lobbydal = LobbyPostgresRepository(session)
        await lobbydal.set_member_state(1, 123)
        result = await lobbydal.get_members_ready(1)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_members_not_ready_success(self, session: AsyncSession):
        lobbydal = LobbyPostgresRepository(session)
        result = await lobbydal.get_members_not_ready(1)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_members_not_ready_none(self, session: AsyncSession):
        lobbydal = LobbyPostgresRepository(session)
        await lobbydal.set_member_state(1, 123)
        result = await lobbydal.get_members_not_ready(1)
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_get_guild_id(self, session: AsyncSession):
        lobbydal = LobbyPostgresRepository(session)
        result = await lobbydal.get_guild_id(1)
        assert result == 1

    @pytest.mark.asyncio
    async def test_is_owner_of_lobby(self, session: AsyncSession):
        lobbydal = LobbyPostgresRepository(session)
        result = await lobbydal.is_owner_of_lobby(123)
        assert result is True

    @pytest.mark.asyncio
    async def test_is_owner_of_lobby_fail(self, session: AsyncSession):
        lobbydal = LobbyPostgresRepository(session)
        result = await lobbydal.is_owner_of_lobby(1234)
        assert result is False

    @pytest.mark.asyncio
    async def test_get_lobbies_count(self, session: AsyncSession):
        lobbydal = LobbyPostgresRepository(session)
        result = await lobbydal.get_lobbies_count()
        assert result == 1

    @pytest.mark.asyncio
    async def test_get_lobbies_count_none(self, session: AsyncSession):
        lobbydal = LobbyPostgresRepository(session)
        await lobbydal.delete_lobby(1)
        result = await lobbydal.get_lobbies_count()
        assert result == 0

    @pytest.mark.asyncio
    async def test_get_lobbies_count_two(self, session: AsyncSession):
        lobbydal = LobbyPostgresRepository(session)

        await lobbydal.create_lobby(
            control_panel_message_id=56,
            original_channel_id=12,
            lobby_channel_id=34,
            guild_id=2,
            guild_name="test",
            user_id=321,
            game_id=1,
            max_size=2,
            description="test",
        )
        result = await lobbydal.get_lobbies_count()
        assert result == 2

    @pytest.mark.asyncio
    async def test_get_lobby_by_owner_id(self, session: AsyncSession):
        lobbydal = LobbyPostgresRepository(session)
        result = await lobbydal.get_lobby_by_owner_id(123)
        assert result is not None

    @pytest.mark.asyncio
    async def test_get_lobby_by_owner_id_none(self, session: AsyncSession):
        with pytest.raises(Exception) as exc_info:
            lobbydal = LobbyPostgresRepository(session)
            await lobbydal.get_lobby_by_owner_id(1234)
        assert str(exc_info.value) == "Lobby with owner_id 1234 not found"
