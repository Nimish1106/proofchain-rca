from collections.abc import Sequence
from types import UnionType
from typing import Any, Union, get_args, get_origin

from pydantic import BaseModel


def _is_list_of(annotation: Any, item_type: type) -> bool:
    origin = get_origin(annotation)
    if origin in (list, tuple, Sequence):
        return item_type in get_args(annotation)
    if origin in (Union, UnionType):
        return any(
            _is_list_of(arg, item_type)
            for arg in get_args(annotation)
        )
    return False


def get_typed_list(model: BaseModel, item_type: type) -> list:
    """Return the unique model field containing a list of item_type."""
    matches = [
        field_name
        for field_name, field in type(model).model_fields.items()
        if _is_list_of(field.annotation, item_type)
    ]
    if len(matches) != 1:
        raise ValueError(
            f"Expected exactly one list field of {item_type.__name__} "
            f"on {type(model).__name__}; found {len(matches)}."
        )

    value = getattr(model, matches[0])
    if value is None:
        return []
    if not isinstance(value, (list, tuple)):
        raise TypeError(
            f"{type(model).__name__}.{matches[0]} must be a list."
        )
    return list(value)
