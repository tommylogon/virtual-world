"""Shared exception types for the item action mixins."""


class AmbiguousItemError(ValueError):
    """Raised when multiple items match a name and user must pick one."""

    def __init__(self, message, options):
        self.options = options
        super().__init__(message)
