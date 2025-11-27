"""
Tests for the guardrails module.

Tests input validation (topic restriction, toxicity detection) and
output filtering (PII redaction, toxicity sanitization).
"""

from unittest.mock import MagicMock, patch

import pytest

from requirements_advisor_client.backend.guardrails import (
    REDIRECT_SYSTEM_MESSAGE,
    GuardrailResult,
    InputGuardrails,
    OutputGuardrails,
    get_input_guardrails,
    get_output_guardrails,
    reset_guardrails,
)


class TestGuardrailResult:
    """Test cases for GuardrailResult dataclass."""

    def test_dataclass_creation_minimal(self) -> None:
        """Test GuardrailResult can be created with minimal required fields."""
        result = GuardrailResult(
            is_valid=True,
            is_on_topic=True,
            content="Test content",
        )

        assert result.is_valid is True
        assert result.is_on_topic is True
        assert result.content == "Test content"
        assert result.validation_errors == []
        assert result.pii_detected is False
        assert result.toxicity_detected is False

    def test_dataclass_creation_full(self) -> None:
        """Test GuardrailResult can be created with all fields."""
        result = GuardrailResult(
            is_valid=False,
            is_on_topic=False,
            content="Filtered content",
            validation_errors=["Off-topic", "PII detected"],
            pii_detected=True,
            toxicity_detected=True,
        )

        assert result.is_valid is False
        assert result.is_on_topic is False
        assert result.content == "Filtered content"
        assert len(result.validation_errors) == 2
        assert result.pii_detected is True
        assert result.toxicity_detected is True


class TestInputGuardrails:
    """Test cases for InputGuardrails class."""

    @pytest.fixture(autouse=True)
    def reset_singletons(self) -> None:
        """Reset singleton instances before each test."""
        reset_guardrails()

    @pytest.fixture
    def mock_settings(self):
        """Mock settings for testing."""
        with patch("requirements_advisor_client.backend.guardrails.settings") as mock:
            mock.guardrails_valid_topics = [
                "requirements management",
                "Jama Software",
                "traceability",
            ]
            mock.guardrails_invalid_topics = ["politics", "sports"]
            mock.guardrails_llm_provider = "gpt-3.5-turbo"
            mock.guardrails_toxicity_threshold = 0.8
            yield mock

    def test_initialization_with_defaults(self, mock_settings) -> None:
        """Test InputGuardrails initializes with default settings."""
        guardrails = InputGuardrails()

        assert guardrails.valid_topics == mock_settings.guardrails_valid_topics
        assert guardrails.invalid_topics == mock_settings.guardrails_invalid_topics
        assert guardrails.llm_callable == mock_settings.guardrails_llm_provider
        assert guardrails.toxicity_threshold == mock_settings.guardrails_toxicity_threshold

    def test_initialization_with_custom_values(self) -> None:
        """Test InputGuardrails accepts custom initialization values."""
        custom_valid = ["custom topic"]
        custom_invalid = ["custom invalid"]

        guardrails = InputGuardrails(
            valid_topics=custom_valid,
            invalid_topics=custom_invalid,
            llm_callable="custom-model",
            toxicity_threshold=0.5,
        )

        assert guardrails.valid_topics == custom_valid
        assert guardrails.invalid_topics == custom_invalid
        assert guardrails.llm_callable == "custom-model"
        assert guardrails.toxicity_threshold == 0.5

    @pytest.mark.asyncio
    async def test_validate_on_topic_input_without_guards(self, mock_settings) -> None:
        """Test validation passes when guards are not initialized."""
        guardrails = InputGuardrails()
        # Don't initialize guards - they will be None

        result = await guardrails.validate("What is EARS notation?")

        assert result.is_on_topic is True
        assert result.is_valid is True
        assert result.content == "What is EARS notation?"

    @pytest.mark.asyncio
    async def test_validate_returns_guardrail_result(self, mock_settings) -> None:
        """Test validate returns a GuardrailResult object."""
        guardrails = InputGuardrails()

        result = await guardrails.validate("Test message")

        assert isinstance(result, GuardrailResult)
        assert result.content == "Test message"

    @pytest.mark.asyncio
    async def test_validate_with_mocked_topic_guard_passing(self, mock_settings) -> None:
        """Test validation with mocked topic guard that passes."""
        guardrails = InputGuardrails()

        # Mock the topic guard
        mock_result = MagicMock()
        mock_result.validation_passed = True
        guardrails._topic_guard = MagicMock()
        guardrails._topic_guard.validate.return_value = mock_result
        guardrails._toxicity_guard = MagicMock()
        guardrails._initialized = True

        result = await guardrails.validate("What is requirements traceability?")

        assert result.is_on_topic is True
        assert len(result.validation_errors) == 0

    @pytest.mark.asyncio
    async def test_validate_with_mocked_topic_guard_failing(self, mock_settings) -> None:
        """Test validation with mocked topic guard that fails (off-topic)."""
        guardrails = InputGuardrails()

        # Mock the topic guard to fail
        mock_result = MagicMock()
        mock_result.validation_passed = False
        guardrails._topic_guard = MagicMock()
        guardrails._topic_guard.validate.return_value = mock_result
        guardrails._toxicity_guard = MagicMock()
        guardrails._initialized = True

        result = await guardrails.validate("What's the best recipe for pizza?")

        assert result.is_on_topic is False
        assert len(result.validation_errors) > 0
        assert "not related to requirements management" in result.validation_errors[0]

    @pytest.mark.asyncio
    async def test_validate_toxic_content_raises_error(self, mock_settings) -> None:
        """Test validation raises ValueError for toxic content."""
        guardrails = InputGuardrails()

        # Mock the toxicity guard to raise an exception
        guardrails._topic_guard = MagicMock()
        guardrails._toxicity_guard = MagicMock()
        guardrails._toxicity_guard.validate.side_effect = Exception("Toxic content detected")
        guardrails._initialized = True

        with pytest.raises(ValueError, match="violates our usage policy"):
            await guardrails.validate("Some toxic content here")

    @pytest.mark.asyncio
    async def test_validate_topic_error_assumes_on_topic(self, mock_settings) -> None:
        """Test that topic validation errors assume on-topic (fail open)."""
        guardrails = InputGuardrails()

        # Mock the topic guard to raise a non-toxic exception
        guardrails._topic_guard = MagicMock()
        guardrails._topic_guard.validate.side_effect = RuntimeError("Network error")
        guardrails._toxicity_guard = MagicMock()
        guardrails._initialized = True

        result = await guardrails.validate("What is traceability?")

        # Should assume on-topic when topic validation fails
        assert result.is_on_topic is True


class TestOutputGuardrails:
    """Test cases for OutputGuardrails class."""

    @pytest.fixture(autouse=True)
    def reset_singletons(self) -> None:
        """Reset singleton instances before each test."""
        reset_guardrails()

    @pytest.fixture
    def mock_settings(self):
        """Mock settings for testing."""
        with patch("requirements_advisor_client.backend.guardrails.settings") as mock:
            mock.guardrails_pii_entities = ["EMAIL_ADDRESS", "PHONE_NUMBER"]
            mock.guardrails_toxicity_threshold = 0.8
            yield mock

    def test_initialization_with_defaults(self, mock_settings) -> None:
        """Test OutputGuardrails initializes with default settings."""
        guardrails = OutputGuardrails()

        assert guardrails.pii_entities == mock_settings.guardrails_pii_entities
        assert guardrails.toxicity_threshold == mock_settings.guardrails_toxicity_threshold

    def test_initialization_with_custom_values(self) -> None:
        """Test OutputGuardrails accepts custom initialization values."""
        custom_entities = ["CUSTOM_ENTITY"]

        guardrails = OutputGuardrails(
            pii_entities=custom_entities,
            toxicity_threshold=0.9,
        )

        assert guardrails.pii_entities == custom_entities
        assert guardrails.toxicity_threshold == 0.9

    @pytest.mark.asyncio
    async def test_validate_clean_output_passes(self, mock_settings) -> None:
        """Test clean output passes validation unchanged."""
        guardrails = OutputGuardrails()
        clean_text = "Requirements traceability is important for quality."

        result = await guardrails.validate(clean_text)

        assert result.is_valid is True
        assert result.content == clean_text
        assert result.pii_detected is False
        assert result.toxicity_detected is False

    @pytest.mark.asyncio
    async def test_validate_returns_guardrail_result(self, mock_settings) -> None:
        """Test validate returns a GuardrailResult object."""
        guardrails = OutputGuardrails()

        result = await guardrails.validate("Test output")

        assert isinstance(result, GuardrailResult)
        assert result.is_valid is True  # Output always valid after sanitization

    @pytest.mark.asyncio
    async def test_validate_with_mocked_pii_detection(self, mock_settings) -> None:
        """Test validation detects and redacts PII."""
        guardrails = OutputGuardrails()

        # Mock the PII guard to return redacted content
        mock_result = MagicMock()
        mock_result.validated_output = "Contact <EMAIL_ADDRESS> for info."
        guardrails._pii_guard = MagicMock()
        guardrails._pii_guard.validate.return_value = mock_result
        guardrails._toxicity_guard = MagicMock()
        mock_tox_result = MagicMock()
        mock_tox_result.validated_output = "Contact <EMAIL_ADDRESS> for info."
        guardrails._toxicity_guard.validate.return_value = mock_tox_result
        guardrails._initialized = True

        result = await guardrails.validate("Contact john@email.com for info.")

        assert result.pii_detected is True
        assert "<EMAIL_ADDRESS>" in result.content

    @pytest.mark.asyncio
    async def test_validate_handles_guard_errors_gracefully(self, mock_settings) -> None:
        """Test that guard errors are handled gracefully."""
        guardrails = OutputGuardrails()

        # Mock guards to raise exceptions
        guardrails._pii_guard = MagicMock()
        guardrails._pii_guard.validate.side_effect = Exception("PII error")
        guardrails._toxicity_guard = MagicMock()
        guardrails._toxicity_guard.validate.side_effect = Exception("Toxicity error")
        guardrails._initialized = True

        # Should not raise, just return original content
        result = await guardrails.validate("Test content")

        assert result.is_valid is True
        assert result.content == "Test content"


class TestSingletonGetters:
    """Test cases for singleton getter functions."""

    @pytest.fixture(autouse=True)
    def reset_singletons(self) -> None:
        """Reset singleton instances before each test."""
        reset_guardrails()

    def test_get_input_guardrails_returns_instance(self) -> None:
        """Test that get_input_guardrails returns an InputGuardrails instance."""
        result = get_input_guardrails()

        assert isinstance(result, InputGuardrails)

    def test_get_input_guardrails_returns_same_instance(self) -> None:
        """Test that get_input_guardrails returns the same singleton instance."""
        result1 = get_input_guardrails()
        result2 = get_input_guardrails()

        assert result1 is result2

    def test_get_output_guardrails_returns_instance(self) -> None:
        """Test that get_output_guardrails returns an OutputGuardrails instance."""
        result = get_output_guardrails()

        assert isinstance(result, OutputGuardrails)

    def test_get_output_guardrails_returns_same_instance(self) -> None:
        """Test that get_output_guardrails returns the same singleton instance."""
        result1 = get_output_guardrails()
        result2 = get_output_guardrails()

        assert result1 is result2

    def test_reset_guardrails_clears_singletons(self) -> None:
        """Test that reset_guardrails clears singleton instances."""
        input_guard1 = get_input_guardrails()
        output_guard1 = get_output_guardrails()

        reset_guardrails()

        input_guard2 = get_input_guardrails()
        output_guard2 = get_output_guardrails()

        assert input_guard1 is not input_guard2
        assert output_guard1 is not output_guard2


class TestRedirectSystemMessage:
    """Test cases for the redirect system message."""

    def test_redirect_message_exists(self) -> None:
        """Test that REDIRECT_SYSTEM_MESSAGE is defined."""
        assert REDIRECT_SYSTEM_MESSAGE is not None
        assert len(REDIRECT_SYSTEM_MESSAGE) > 0

    def test_redirect_message_mentions_requirements(self) -> None:
        """Test that redirect message mentions requirements management."""
        assert "requirements management" in REDIRECT_SYSTEM_MESSAGE.lower()

    def test_redirect_message_mentions_jama(self) -> None:
        """Test that redirect message mentions Jama Software."""
        assert "jama" in REDIRECT_SYSTEM_MESSAGE.lower()

    def test_redirect_message_mentions_traceability(self) -> None:
        """Test that redirect message mentions traceability."""
        assert "traceability" in REDIRECT_SYSTEM_MESSAGE.lower()

    def test_redirect_message_is_polite(self) -> None:
        """Test that redirect message has polite language."""
        message_lower = REDIRECT_SYSTEM_MESSAGE.lower()
        polite_indicators = ["politely", "gently", "helpful", "warm", "encouraging"]
        assert any(indicator in message_lower for indicator in polite_indicators)
