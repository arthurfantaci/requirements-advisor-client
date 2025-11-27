"""
Database models and session management using SQLAlchemy async.

Provides the ORM models for session and message persistence,
along with helper functions for database operations.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, relationship

from requirements_advisor_client.backend.config import settings
from requirements_advisor_client.backend.logging import get_logger

logger = get_logger("database")


def _utc_now() -> datetime:
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(UTC)


class Base(DeclarativeBase):
    """SQLAlchemy declarative base class."""

    pass


class Session(Base):
    """Database model for chat sessions.

    Tracks user sessions with timestamps for activity monitoring
    and automatic cleanup of expired sessions.

    Attributes:
        id: Unique session identifier (UUID).
        created_at: Timestamp when the session was created.
        last_activity: Timestamp of the most recent activity.
        messages: Related chat messages in this session.
    """

    __tablename__ = "sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    created_at = Column(DateTime(timezone=True), default=_utc_now)
    last_activity = Column(DateTime(timezone=True), default=_utc_now, onupdate=_utc_now)
    messages = relationship(
        "ChatMessage",
        back_populates="session",
        cascade="all, delete-orphan",
    )


class ChatMessage(Base):
    """Database model for individual chat messages.

    Stores each message in a conversation with role and timestamp.

    Attributes:
        id: Auto-incrementing message ID.
        session_id: Foreign key to the parent session.
        role: Message role ('user' or 'assistant').
        content: The message text content.
        created_at: Timestamp when the message was created.
        session: Relationship to the parent Session.
    """

    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(
        String(36),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        index=True,
    )
    role = Column(String(20))
    content = Column(Text)
    created_at = Column(DateTime(timezone=True), default=_utc_now)
    session = relationship("Session", back_populates="messages")


# Database engine and session factory (lazy initialization)
_engine = None
_async_session_factory = None


def _get_engine():
    """Get or create the database engine.

    Returns:
        AsyncEngine instance.
    """
    global _engine
    if _engine is None:
        logger.debug("Creating database engine", url=settings.async_database_url[:30] + "...")
        _engine = create_async_engine(settings.async_database_url, echo=False)
    return _engine


def _get_session_factory():
    """Get or create the async session factory.

    Returns:
        Async session maker instance.
    """
    global _async_session_factory
    if _async_session_factory is None:
        _async_session_factory = async_sessionmaker(
            _get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _async_session_factory


async def init_database() -> None:
    """Initialize the database, creating all tables.

    Should be called during application startup.
    """
    engine = _get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized")


@asynccontextmanager
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get an async database session.

    Yields:
        AsyncSession for database operations.

    Example:
        >>> async with get_db() as db:
        ...     result = await db.execute(select(Session))
    """
    session_factory = _get_session_factory()
    async with session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_or_create_session(session_id: str) -> str:
    """Get an existing session or create a new one.

    Args:
        session_id: The session ID to look up or create.

    Returns:
        The session ID (same as input if found, or newly created).
    """
    async with get_db() as db:
        result = await db.execute(select(Session).where(Session.id == session_id))
        session = result.scalar_one_or_none()

        if not session:
            logger.debug("Creating new session", session_id=session_id)
            session = Session(id=session_id)
            db.add(session)
            await db.commit()

        return session_id


async def save_message(session_id: str, role: str, content: str) -> None:
    """Save a chat message to the database.

    Args:
        session_id: The session ID to associate the message with.
        role: The message role ('user' or 'assistant').
        content: The message text content.
    """
    async with get_db() as db:
        message = ChatMessage(session_id=session_id, role=role, content=content)
        db.add(message)
        await db.commit()
    logger.debug("Saved message", session_id=session_id, role=role)


async def get_history(session_id: str) -> list[dict]:
    """Get chat history for a session.

    Args:
        session_id: The session ID to retrieve history for.

    Returns:
        List of message dictionaries with role, content, and created_at.
    """
    async with get_db() as db:
        result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at)
        )
        messages = result.scalars().all()

    return [
        {
            "role": msg.role,
            "content": msg.content,
            "created_at": msg.created_at.isoformat(),
        }
        for msg in messages
    ]


async def cleanup_expired_sessions(days: int = 30) -> int:
    """Delete sessions that haven't been active in the specified number of days.

    Args:
        days: Number of days of inactivity before a session is considered expired.

    Returns:
        Number of sessions deleted.
    """
    from datetime import timedelta

    cutoff = _utc_now() - timedelta(days=days)

    async with get_db() as db:
        result = await db.execute(
            delete(Session).where(Session.last_activity < cutoff)
        )
        await db.commit()
        count = result.rowcount

    if count > 0:
        logger.info("Cleaned up expired sessions", count=count)

    return count
