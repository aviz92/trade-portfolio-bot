from enum import Enum


class Currency(str, Enum):
    USD = "USD"
    ILS = "ILS"


CURRENCY_SYMBOLS: dict[Currency, str] = {
    Currency.USD: "$",
    Currency.ILS: "₪",
}
