"""Tests for the database module."""

from datetime import UTC, datetime, timedelta

import pytest


class TestDatabaseModels:
    """Test cases for database models."""

    def test_session_model_defaults(self):
        """Test Session model has correct defaults."""
        from requirements_advisor_client.backend.database import Session

        session = Session(id="test-id")

        assert session.id == "test-id"
        # created_at and last_activity will be None until inserted into DB

    def test_chat_message_model(self):
        """Test ChatMessage model creation."""
        from requirements_advisor_client.backend.database import ChatMessage

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
        from sqlalchemy import text
        from sqlalchemy.ext.asyncio import create_async_engine

        from requirements_advisor_client.backend.database import Base

        engine = create_async_engine("sqlite+aiosqlite:///:memory:")

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Verify tables exist
        async with engine.connect() as conn:
            result = await conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            )
            tables = [row[0] for row in result.fetchall()]

        assert "sessions" in tables
        assert "chat_messages" in tables

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_session_crud(self):
        """Test session create and retrieve operations."""
        from sqlalchemy import select
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

        from requirements_advisor_client.backend.database import Base, Session

        engine = create_async_engine("sqlite+aiosqlite:///:memory:")

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        # Create session
        async with async_session() as db:
            session = Session(id="test-session-123")
            db.add(session)
            await db.commit()

        # Retrieve session
        async with async_session() as db:
            result = await db.execute(
                select(Session).where(Session.id == "test-session-123")
            )
            retrieved = result.scalar_one_or_none()

            assert retrieved is not None
            assert retrieved.id == "test-session-123"

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_message_crud(self):
        """Test message create and retrieve operations."""
        from sqlalchemy import select
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

        from requirements_advisor_client.backend.database import Base, ChatMessage, Session

        engine = create_async_engine("sqlite+aiosqlite:///:memory:")

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        # Create session and message
        async with async_session() as db:
            session = Session(id="test-session")
            db.add(session)
            await db.commit()

            message = ChatMessage(
                session_id="test-session",
                role="user",
                content="Hello, world!",
            )
            db.add(message)
            await db.commit()

        # Retrieve messages
        async with async_session() as db:
            result = await db.execute(
                select(ChatMessage).where(ChatMessage.session_id == "test-session")
            )
            messages = result.scalars().all()

            assert len(messages) == 1
            assert messages[0].role == "user"
            assert messages[0].content == "Hello, world!"

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_message_ordering(self):
        """Test that messages are ordered by created_at."""
        from sqlalchemy import select
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

        from requirements_advisor_client.backend.database import Base, ChatMessage, Session

        engine = create_async_engine("sqlite+aiosqlite:///:memory:")

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with async_session() as db:
            session = Session(id="test-session")
            db.add(session)
            await db.commit()

            # Add messages with explicit timestamps
            msg1 = ChatMessage(
                session_id="test-session",
                role="user",
                content="First",
                created_at=datetime.now(UTC) - timedelta(minutes=2),
            )
            msg2 = ChatMessage(
                session_id="test-session",
                role="assistant",
                content="Second",
                created_at=datetime.now(UTC) - timedelta(minutes=1),
            )
            db.add_all([msg1, msg2])
            await db.commit()

        async with async_session() as db:
            result = await db.execute(
                select(ChatMessage)
                .where(ChatMessage.session_id == "test-session")
                .order_by(ChatMessage.created_at)
            )
            messages = result.scalars().all()

            assert len(messages) == 2
            assert messages[0].content == "First"
            assert messages[1].content == "Second"

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_session_cleanup(self):
        """Test cleanup of expired sessions."""
        from sqlalchemy import delete, select
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

        from requirements_advisor_client.backend.database import Base, Session

        engine = create_async_engine("sqlite+aiosqlite:///:memory:")

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        # Create old and new sessions
        async with async_session() as db:
            old_session = Session(
                id="old-session",
                last_activity=datetime.now(UTC) - timedelta(days=45),
            )
            new_session = Session(
                id="new-session",
                last_activity=datetime.now(UTC),
            )
            db.add_all([old_session, new_session])
            await db.commit()

        # Clean up expired sessions
        cutoff = datetime.now(UTC) - timedelta(days=30)
        async with async_session() as db:
            await db.execute(delete(Session).where(Session.last_activity < cutoff))
            await db.commit()

        # Verify old session was deleted
        async with async_session() as db:
            result = await db.execute(select(Session))
            sessions = result.scalars().all()

            assert len(sessions) == 1
            assert sessions[0].id == "new-session"

        await engine.dispose()
