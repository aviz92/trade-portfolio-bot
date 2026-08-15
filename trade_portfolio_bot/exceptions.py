from python_custom_exceptions import BaseCustomException


class InvalidBuyCommandException(BaseCustomException):
    """Raised when a /buy command is missing arguments or malformed."""


class InvalidTickerException(BaseCustomException):
    """Raised when the ticker symbol fails basic validation."""


class InvalidQuantityException(BaseCustomException):
    """Raised when the quantity is not a positive number."""


class InvalidPriceException(BaseCustomException):
    """Raised when the price is not a positive number."""
