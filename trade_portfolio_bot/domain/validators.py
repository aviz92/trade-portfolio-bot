from python_custom_exceptions import BaseCustomException


def parse_positive_float(raw_value: str, field_name: str, exception_cls: type[BaseCustomException]) -> float:
    try:
        value = float(raw_value)
    except ValueError as e:
        raise exception_cls(
            f"'{raw_value}' is not a valid number",
            diagnostic_info={field_name: raw_value},
        ) from e
    if value <= 0:
        raise exception_cls(
            f"{field_name.capitalize()} must be greater than 0",
            diagnostic_info={field_name: value},
        )
    return value
