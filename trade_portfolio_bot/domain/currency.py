from enum import StrEnum


class Currency(StrEnum):
    USD = "USD"
    ILS = "ILS"


CURRENCY_SYMBOLS: dict[Currency, str] = {
    Currency.USD: "$",
    Currency.ILS: "₪",
}
