import dataclasses
import typing


def unknown_fields(obj: typing.Any, path=()) -> typing.Iterable[tuple[tuple[str, ...], dict[int, list]]]:
    if not dataclasses.is_dataclass(obj):
        return

    if unknown := getattr(obj, '_unknown', None):
        yield path, unknown

    for field in dataclasses.fields(obj):
        value = getattr(obj, field.name)
        yield from unknown_fields(value, (*path, field.name))
