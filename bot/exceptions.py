"""Custom exception hierarchy for OpenClaude."""


class OpenClaudeError(Exception):
    """Base exception for all OpenClaude errors."""


class ConfigurationError(OpenClaudeError):
    """Raised when configuration is invalid or missing."""


class SessionError(OpenClaudeError):
    """Raised when session management fails."""


class StreamingError(OpenClaudeError):
    """Raised when streaming encounters an error."""


class PermissionDeniedError(OpenClaudeError):
    """Raised when an unauthorized action is attempted."""


class MediaProcessingError(OpenClaudeError):
    """Raised when media processing fails."""


class AIProviderUnavailableError(OpenClaudeError):
    """Raised when the AI provider is unavailable."""
