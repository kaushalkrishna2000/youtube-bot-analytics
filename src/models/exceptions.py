"""Domain exceptions raised by services and handled in logic/report and logic/batch."""


class ChannelNotFoundError(Exception):
    """Raised when a channel cannot be resolved from the input."""


class CommentsDisabledError(Exception):
    """Raised when comments are disabled on a video."""
