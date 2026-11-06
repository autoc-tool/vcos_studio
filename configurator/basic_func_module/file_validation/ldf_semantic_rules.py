import inspect
from typing import Dict, Callable


class LdfSemanticError(Exception):

    def __init__(self, message: str) -> None:
        super().__init__(message)


def is_ldf_semantic_rule(object):
    return inspect.isfunction(object) and object.__name__.startswith("ldf_semantic_rule")


def ldf_semantic_rule_demo(ldf_dict: Dict, error_log: Callable) -> bool:
    # Semantic check scentences here
    validation_pass = True

    # If cannot pass the semantic check, raise exception
    if not validation_pass:
        message = "Error message of the validation"
        error_log(message)

    return validation_pass
