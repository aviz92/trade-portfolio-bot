from dataclasses import dataclass
from datetime import UTC, datetime

from trade_portfolio_bot.domain.exceptions import InvalidAmountException, InvalidCashCommandException
from trade_portfolio_bot.domain.validators import parse_positive_float


@dataclass(frozen=True)
class CashDeposit:
    amount: float
    timestamp: datetime

    def __str__(self) -> str:
        return f"DEPOSIT {self.amount:.2f} | {self.timestamp.isoformat()}"


def parse_deposit_command(args: list[str]) -> CashDeposit:
    """
    Parse /deposit command arguments into a CashDeposit.

    Expected format: AMOUNT
    Example: 1000
    """
    if len(args) != 1:
        raise InvalidCashCommandException(
            "Expected 1 argument: AMOUNT",
            diagnostic_info={"args": args},
        )

    amount = parse_positive_float(args[0], "amount", InvalidAmountException)
    return CashDeposit(amount=amount, timestamp=datetime.now(UTC))
