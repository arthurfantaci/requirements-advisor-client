"""Tests for the database module."""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from requirements_advisor_client.backend.database import (
    Base,
    ChatMessage,
    Session,
    cleanup_expired_sessions,
    get_history,
    get_or_create_session,
    init_database,
    save_message,
)


class TestDatabaseModels:
    """Test cases for database models."""

    def test_session_model_defaults(self):
        """Test Session model has correct defaults."""
        session = Session()

        assert session.id is not None
        assert len(session.id) == 36  # UUID format
        assert session.created_at is None  # Set by DB
        assert session.last_activity is None  # Set by DB

    def test_chat_message_model(self):
        """Test ChatMessage model creation."""
        message = ChatMessage(
            session_id="test-session-id",
            role="user",
            content="Test message content",
        )

        assert message.session_id == "test-session-id"
        assert message.role == "user"
        assert message.content == "Test message content"


class TestDatabaseOperations:
    """Test cases for database operations."""

    @pytest.mark.asyncio
    async def test_init_database(self):
        """Test database initialization creates tables."""
        from sqlalchemy.ext.asyncio import create_async_engine

        with patch(
            "requirements_advisor_client.backend.database._get_engine"
        ) as mock_get_engine:
            engine = create_async_engine("sqlite+aiosqlite:///:memory:")
            mock_get_engine.return_value = engine

            await init_database()

            # Verify tables exist
            async with engine.begin() as conn:
                result = await conn.run_sync(
                    lambda sync_conn: sync_conn.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    ).fetchall()
                )
                table_names = [row[0] for row in result]

            assert "sessions" in table_names
            assert "chat_messages" in table_names

            await engine.dispose()

    @pytest.mark.asyncio
    async def test_get_or_create_session_new(self, test_db):
        """Test creating a new session."""
        from sqlalchemy import select

        with patch(
            "requirements_advisor_client.backend.database.get_db"
        ) as mock_get_db:
            mock_get_db.return_value.__aenter__ = lambda s: test_db
            mock_get_db.return_value.__aexit__ = lambda s, *args: None

            session_id = "new-test-session"

            # Create tables first
            async with test_db.get_bind().begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            # Should create new session
            result = await get_or_create_session(session_id)

            assert result == session_id

    @pytest.mark.asyncio
    async def test_save_message(self, test_db):
        """Test saving a chat message."""
        with patch(
            "requirements_advisor_client.backend.database.get_db"
        ) as mock_get_db:
            mock_get_db.return_value.__aenter__ = lambda s: test_db
            mock_get_db.return_value.__aexit__ = lambda s, *args: None

            # Create tables first
            async with test_db.get_bind().begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            # Create session first
            session = Session(id="test-session")
            test_db.add(session)
            await test_db.commit()

            await save_message("test-session", "user", "Hello, world!")

            # Verify message was saved
            from sqlalchemy import select

            result = await test_db.execute(
                select(ChatMessage).where(ChatMessage.session_id == "test-session")
            )
            messages = result.scalars().all()

            assert len(messages) == 1
            assert messages[0].role == "user"
            assert messages[0].content == "Hello, world!"

    @pytest.mark.asyncio
    async def test_get_history(self, test_db):
        """Test retrieving chat history."""
        with patch(
            "requirements_advisor_client.backend.database.get_db"
        ) as mock_get_db:
            mock_get_db.return_value.__aenter__ = lambda s: test_db
            mock_get_db.return_value.__aexit__ = lambda s, *args: None

            # Create tables
            async with test_db.get_bind().begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            # Create session and messages
            session = Session(id="history-session")
            test_db.add(session)
            await test_db.commit()

            msg1 = ChatMessage(
                session_id="history-session",
                role="user",
                content="First message",
                created_at=datetime.utcnow() - timedelta(minutes=2),
            )
            msg2 = ChatMessage(
                session_id="history-session",
                role="assistant",
                content="Second message",
                created_at=datetime.utcnow() - timedelta(minutes=1),
            )
            test_db.add_all([msg1, msg2])
            await test_db.commit()

            history = await get_history("history-session")

            assert len(history) == 2
            assert history[0]["role"] == "user"
            assert history[0]["content"] == "First message"
            assert history[1]["role"] == "assistant"

    @pytest.mark.asyncio
    async def test_get_history_empty(self, test_db):
        """Test retrieving history for non-existent session."""
        with patch(
            "requirements_advisor_client.backend.database.get_db"
        ) as mock_get_db:
            mock_get_db.return_value.__aenter__ = lambda s: test_db
            mock_get_db.return_value.__aexit__ = lambda s, *args: None

            # Create tables
            async with test_db.get_bind().begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            history = await get_history("nonexistent-session")

            assert history == []

    @pytest.mark.asyncio
    async def test_cleanup_expired_sessions(self, test_db):
        """Test cleanup of expired sessions."""
        with patch(
            "requirements_advisor_client.backend.database.get_db"
        ) as mock_get_db:
            mock_get_db.return_value.__aenter__ = lambda s: test_db
            mock_get_db.return_value.__aexit__ = lambda s, *args: None

            # Create tables
            async with test_db.get_bind().begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            # Create old and new sessions
            old_session = Session(
                id="old-session",
                last_activity=datetime.utcnow() - timedelta(days=45),
            )
            new_session = Session(
                id="new-session",
                last_activity=datetime.utcnow(),
            )
            test_db.add_all([old_session, new_session])
            await test_db.commit()

            count = await cleanup_expired_sessions(days=30)

            assert count == 1

            # Verify old session was deleted
            from sqlalchemy import select

            result = await test_db.execute(select(Session))
            sessions = result.scalars().all()

            assert len(sessions) == 1
            assert sessions[0].id == "new-session"
