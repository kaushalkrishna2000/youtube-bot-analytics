"""System-wide exceptions for the YouTube analytics tool."""


class ChannelNotFoundError(Exception):
    """Raised when a channel cannot be resolved from the input."""


class CommentsDisabledError(Exception):
    """Raised when comments are disabled on a video."""
