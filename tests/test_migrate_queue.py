from enum import Enum


def test_batch_message_kind_is_enum():
    from src.cli.scripts.migrate_csv_to_db import BatchMessage, MessageKind  # noqa: PLC0415

    assert issubclass(MessageKind, Enum)
    assert BatchMessage.__annotations__["kind"] is MessageKind
