"""
Guardrails AI integration for input/output validation.

Provides topic restriction, content safety (toxicity filtering),
and PII detection/redaction for the Requirements Advisor.

This module implements:
- Input guardrails: Topic validation and toxicity detection for user prompts
- Output guardrails: PII redaction and toxicity filtering for LLM responses
"""

from dataclasses import dataclass, field
from typing import Any

from requirements_advisor_client.backend.config import settings
from requirements_advisor_client.backend.logging import get_logger

logger = get_logger("guardrails")


@dataclass
class GuardrailResult:
    """Result from guardrail validation.

    Attributes:
        is_valid: Whether the input/output passed validation.
        is_on_topic: Whether the content is on-topic (for input guardrails).
        content: The validated/transformed content.
        validation_errors: List of validation error messages.
        pii_detected: Whether PII was detected (for output guardrails).
        toxicity_detected: Whether toxic content was detected.
    """

    is_valid: bool
    is_on_topic: bool
    content: str
    validation_errors: list[str] = field(default_factory=list)
    pii_detected: bool = False
    toxicity_detected: bool = False


class InputGuardrails:
    """Input validation guardrails for user prompts.

    Validates that user input is:
    1. On-topic (requirements management, Jama Software, traceability)
    2. Free of toxic language

    Off-topic inputs are flagged but not blocked - they receive a polite redirect.
    Toxic inputs are hard-blocked with an exception.

    Attributes:
        valid_topics: List of valid topic keywords/phrases.
        invalid_topics: List of explicitly invalid topics.
        llm_callable: LLM model for topic classification fallback.
        toxicity_threshold: Threshold for toxic language detection (0-1).

    Example:
        >>> guardrails = InputGuardrails()
        >>> result = await guardrails.validate("What is EARS notation?")
        >>> print(result.is_on_topic)  # True
    """

    def __init__(
        self,
        valid_topics: list[str] | None = None,
        invalid_topics: list[str] | None = None,
        llm_callable: str | None = None,
        toxicity_threshold: float | None = None,
    ) -> None:
        """Initialize input guardrails.

        Args:
            valid_topics: List of valid topic keywords/phrases.
                Defaults to settings.guardrails_valid_topics.
            invalid_topics: List of explicitly invalid topics.
                Defaults to settings.guardrails_invalid_topics.
            llm_callable: LLM model for topic classification fallback.
                Defaults to settings.guardrails_llm_provider.
            toxicity_threshold: Threshold for toxic language detection (0-1).
                Defaults to settings.guardrails_toxicity_threshold.
        """
        self.valid_topics = valid_topics or settings.guardrails_valid_topics
        self.invalid_topics = invalid_topics or settings.guardrails_invalid_topics
        self.llm_callable = llm_callable or settings.guardrails_llm_provider
        self.toxicity_threshold = (
            toxicity_threshold
            if toxicity_threshold is not None
            else settings.guardrails_toxicity_threshold
        )

        self._topic_guard: Any = None
        self._toxicity_guard: Any = None
        self._initialized = False

        logger.info(
            "Input guardrails configured",
            valid_topics_count=len(self.valid_topics),
            invalid_topics_count=len(self.invalid_topics),
        )

    def _initialize_guards(self) -> None:
        """Lazy initialization of guardrails to avoid import issues at startup."""
        if self._initialized:
            return

        try:
            import guardrails as gd
            from guardrails.hub import (  # type: ignore[import-untyped]
                RestrictToTopic,
                ToxicLanguage,
            )

            # Initialize topic validation guard (soft validation - noop on fail)
            self._topic_guard = gd.Guard().use(
                RestrictToTopic(
                    valid_topics=self.valid_topics,
                    invalid_topics=self.invalid_topics,
                    llm_callable=self.llm_callable,
                    disable_classifier=False,
                    disable_llm=False,
                    on_fail="noop",  # Don't modify, just flag
                )
            )

            # Initialize toxicity guard (hard validation - exception on fail)
            self._toxicity_guard = gd.Guard().use(
                ToxicLanguage(
                    threshold=self.toxicity_threshold,
                    on_fail="exception",
                )
            )

            self._initialized = True
            logger.info("Input guardrails initialized successfully")

        except ImportError as e:
            logger.warning(
                "Guardrails hub validators not installed. "
                "Run: guardrails hub install hub://tryolabs/restricttotopic "
                "and guardrails hub install hub://guardrails/toxic_language",
                error=str(e),
            )
            self._initialized = True  # Mark as initialized to avoid retry

    async def validate(self, user_input: str) -> GuardrailResult:
        """Validate user input against guardrails.

        Args:
            user_input: The user's message to validate.

        Returns:
            GuardrailResult with validation status and details.

        Raises:
            ValueError: If toxic content is detected (hard block).
        """
        self._initialize_guards()

        validation_errors: list[str] = []
        is_on_topic = True
        toxicity_detected = False

        logger.debug("Validating user input", input_length=len(user_input))

        # Check for toxic language first (hard block)
        if self._toxicity_guard is not None:
            try:
                self._toxicity_guard.validate(user_input)
            except Exception as e:
                error_str = str(e).lower()
                if "toxic" in error_str or "validation" in error_str:
                    logger.warning("Toxic content detected in user input", error=str(e))
                    toxicity_detected = True
                    raise ValueError(
                        "Your message contains content that violates our usage policy. "
                        "Please rephrase your question."
                    ) from e
                # Re-raise if it's a different type of error
                raise

        # Check topic relevance (soft validation)
        if self._topic_guard is not None:
            try:
                result = self._topic_guard.validate(user_input)
                # Check if validation passed
                if hasattr(result, "validation_passed") and not result.validation_passed:
                    is_on_topic = False
                    validation_errors.append("Content is not related to requirements management")
                    logger.info("Off-topic input detected", input_preview=user_input[:100])
            except Exception as e:
                # If topic validation fails for technical reasons, assume on-topic
                logger.warning("Topic validation error, assuming on-topic", error=str(e))
                is_on_topic = True

        return GuardrailResult(
            is_valid=is_on_topic and not toxicity_detected,
            is_on_topic=is_on_topic,
            content=user_input,
            validation_errors=validation_errors,
            toxicity_detected=toxicity_detected,
        )


class OutputGuardrails:
    """Output validation guardrails for LLM responses.

    Validates and sanitizes LLM output for:
    1. PII detection and redaction
    2. Toxic language filtering

    Uses "fix" action to sanitize content rather than blocking.

    Attributes:
        pii_entities: List of PII entity types to detect.
        toxicity_threshold: Threshold for toxic language detection (0-1).

    Example:
        >>> guardrails = OutputGuardrails()
        >>> result = await guardrails.validate("Contact john@email.com for info.")
        >>> print(result.pii_detected)  # True
        >>> print(result.content)  # "Contact <EMAIL_ADDRESS> for info."
    """

    def __init__(
        self,
        pii_entities: list[str] | None = None,
        toxicity_threshold: float | None = None,
    ) -> None:
        """Initialize output guardrails.

        Args:
            pii_entities: List of PII entity types to detect.
                Defaults to settings.guardrails_pii_entities.
            toxicity_threshold: Threshold for toxic language detection (0-1).
                Defaults to settings.guardrails_toxicity_threshold.
        """
        self.pii_entities = pii_entities or settings.guardrails_pii_entities
        self.toxicity_threshold = (
            toxicity_threshold
            if toxicity_threshold is not None
            else settings.guardrails_toxicity_threshold
        )

        self._pii_guard: Any = None
        self._toxicity_guard: Any = None
        self._initialized = False

        logger.info(
            "Output guardrails configured",
            pii_entities_count=len(self.pii_entities),
        )

    def _initialize_guards(self) -> None:
        """Lazy initialization of guardrails to avoid import issues at startup."""
        if self._initialized:
            return

        try:
            import guardrails as gd
            from guardrails.hub import DetectPII, ToxicLanguage  # type: ignore[import-untyped]

            # Initialize PII detection guard (fix on fail - redact PII)
            self._pii_guard = gd.Guard().use(
                DetectPII(
                    pii_entities=self.pii_entities,
                    on_fail="fix",
                )
            )

            # Initialize toxicity guard (fix on fail - sanitize)
            self._toxicity_guard = gd.Guard().use(
                ToxicLanguage(
                    threshold=self.toxicity_threshold,
                    on_fail="fix",
                )
            )

            self._initialized = True
            logger.info("Output guardrails initialized successfully")

        except ImportError as e:
            logger.warning(
                "Guardrails hub validators not installed. "
                "Run: guardrails hub install hub://guardrails/detect_pii "
                "and guardrails hub install hub://guardrails/toxic_language",
                error=str(e),
            )
            self._initialized = True  # Mark as initialized to avoid retry

    async def validate(self, llm_output: str) -> GuardrailResult:
        """Validate and sanitize LLM output.

        Args:
            llm_output: The LLM's response to validate.

        Returns:
            GuardrailResult with sanitized content and detection flags.
        """
        self._initialize_guards()

        validation_errors: list[str] = []
        pii_detected = False
        toxicity_detected = False
        sanitized_content = llm_output

        logger.debug("Validating LLM output", output_length=len(llm_output))

        # Check and redact PII
        if self._pii_guard is not None:
            try:
                result = self._pii_guard.validate(sanitized_content)
                # Extract validated output - handle different return types
                if hasattr(result, "validated_output") and result.validated_output:
                    validated = result.validated_output
                elif isinstance(result, tuple) and len(result) >= 2:
                    validated = result[1]
                else:
                    validated = sanitized_content

                if validated and validated != sanitized_content:
                    pii_detected = True
                    sanitized_content = validated
                    validation_errors.append("PII detected and redacted")
                    logger.info("PII detected and redacted from output")
            except Exception as e:
                logger.warning("PII validation error", error=str(e))

        # Check and sanitize toxic content
        if self._toxicity_guard is not None:
            try:
                result = self._toxicity_guard.validate(sanitized_content)
                # Extract validated output - handle different return types
                if hasattr(result, "validated_output") and result.validated_output:
                    validated = result.validated_output
                elif isinstance(result, tuple) and len(result) >= 2:
                    validated = result[1]
                else:
                    validated = sanitized_content

                if validated and validated != sanitized_content:
                    toxicity_detected = True
                    sanitized_content = validated
                    validation_errors.append("Toxic content detected and sanitized")
                    logger.info("Toxic content sanitized from output")
            except Exception as e:
                logger.warning("Toxicity validation error", error=str(e))

        return GuardrailResult(
            is_valid=True,  # Output is always valid after sanitization
            is_on_topic=True,
            content=sanitized_content,
            validation_errors=validation_errors,
            pii_detected=pii_detected,
            toxicity_detected=toxicity_detected,
        )


# Singleton instances for reuse
_input_guardrails: InputGuardrails | None = None
_output_guardrails: OutputGuardrails | None = None


def get_input_guardrails() -> InputGuardrails:
    """Get or create the singleton InputGuardrails instance.

    Returns:
        Configured InputGuardrails instance.

    Example:
        >>> input_guard = get_input_guardrails()
        >>> result = await input_guard.validate("What is traceability?")
    """
    global _input_guardrails
    if _input_guardrails is None:
        _input_guardrails = InputGuardrails()
    return _input_guardrails


def get_output_guardrails() -> OutputGuardrails:
    """Get or create the singleton OutputGuardrails instance.

    Returns:
        Configured OutputGuardrails instance.

    Example:
        >>> output_guard = get_output_guardrails()
        >>> result = await output_guard.validate(llm_response)
    """
    global _output_guardrails
    if _output_guardrails is None:
        _output_guardrails = OutputGuardrails()
    return _output_guardrails


def reset_guardrails() -> None:
    """Reset singleton guardrail instances.

    Useful for testing or reconfiguration.
    """
    global _input_guardrails, _output_guardrails
    _input_guardrails = None
    _output_guardrails = None
    logger.debug("Guardrail instances reset")


# Polite redirect system message for off-topic queries
REDIRECT_SYSTEM_MESSAGE = """You are a helpful assistant specializing in requirements management.
The user has asked a question that appears to be outside your area of expertise.

Your role is to:
1. Acknowledge their question politely
2. Explain that you specialize in requirements management topics
3. Gently redirect them back to topics you can help with
4. Offer specific suggestions related to requirements management

Topics you can help with include:
- Requirements management best practices
- Jama Software and Jama Connect
- Requirements traceability
- INCOSE guidelines
- EARS notation
- Verification and validation
- Requirements analysis and specification
- Change management and impact analysis

Be warm, helpful, and encouraging while steering the conversation back to your expertise."""
