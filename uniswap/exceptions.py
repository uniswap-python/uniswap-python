from typing import Any


class InvalidToken(Exception):
    """Raised when an invalid token address is used."""

    def __init__(self, address: Any) -> None:
        Exception.__init__(self, f"Invalid token address: {address}")


class InsufficientBalance(Exception):
    """Raised when the account has insufficient balance for a transaction."""

    def __init__(self, had: int, needed: int) -> None:
        Exception.__init__(self, f"Insufficient balance. Had {had}, needed {needed}")
