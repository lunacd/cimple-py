def _find_index_first_of(input_str: str, chars: str, start_index: int = 0) -> int:
    """
    Find the index of the first occurrence of any one of the characters in chars.

    Return < 0 if the chars are not found.
    """

    for index in range(start_index, len(input_str)):
        if input_str[index] in chars:
            return index

    return -1


def interpolate(input_str: str, context: dict[str, str]) -> str:
    """
    Interpolate a string against a context.

    Variables are referred to as ${variable}.

    Literal $ and \\ are escaped with leading \\.
    """

    result_str = ""

    def escape_char(char: str) -> str:
        match char:
            case "\\":
                return "\\"
            case "$":
                return "$"
            case _:
                raise RuntimeError(
                    f'Invalid escape sequence "\\{char}". Do you mean to escape \\ with \\\\?'
                )

    def substitute_variable(start_index: int) -> (str, int):
        malformed_use_of_variable_error = (
            "Malformed use of variable. "
            "Variables are used as ${variable}. Do you mean to escape $ with \\$?"
        )
        if start_index >= len(input_str) or input_str[start_index] != "{":
            raise RuntimeError(malformed_use_of_variable_error)
        # Use variable
        variable_end_index = _find_index_first_of(input_str, "}", start_index=start_index)
        if variable_end_index <= start_index:
            raise RuntimeError(
                "Malformed use of variable. Cannot find matching } denoting the end of variable."
            )
        variable_name = input_str[start_index + 1 : variable_end_index]
        if variable_name not in context:
            raise RuntimeError(f"Undefined variable {variable_name}.")
        return context[variable_name], variable_end_index + 1

    def consume_plain_text(start_index: int) -> (str, int):
        special_char_index = _find_index_first_of(input_str, "\\$", start_index=start_index)
        plain_text_value = (
            input_str[start_index:]
            if special_char_index < 0
            else input_str[start_index:special_char_index]
        )
        return plain_text_value, special_char_index

    plain_text, next_index = consume_plain_text(0)
    result_str += plain_text

    while next_index >= 0:
        match input_str[next_index]:
            case "\\":
                if next_index + 1 < len(input_str):
                    result_str += escape_char(input_str[next_index + 1])
                    next_index += 2
                else:
                    raise RuntimeError(
                        "Malformed escape sequence. Do you mean to escape \\ with \\\\?"
                    )
            case "$":
                variable_value, next_index = substitute_variable(next_index + 1)
                result_str += variable_value

        plain_text, next_index = consume_plain_text(next_index)
        result_str += plain_text

    return result_str
