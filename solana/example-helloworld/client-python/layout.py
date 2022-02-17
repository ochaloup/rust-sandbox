import construct
import typing
import datetime
from decimal import Decimal

class U32Adapter(construct.Adapter):  # u32 is unsigned 32 bit integer
    def __init__(self, size: int = 4) -> None:
        super().__init__(construct.BytesInteger(size, signed=False, swapped=True))

    def _decode(self, obj: int, context: typing.Any, path: typing.Any) -> Decimal:
        return Decimal(obj)

    def _encode(self, obj: Decimal, context: typing.Any, path: typing.Any) -> int:
        # Can only encode int values.
        return int(obj)


class TimestampAdapter(construct.Adapter):  # i64 is signed integer as timestamp is saved in Solana Clock
    def __init__(self, size: int = 8) -> None:
        super().__init__(construct.BytesInteger(size, signed=True, swapped=True))

    def _decode(self, obj: int, context: typing.Any, path: typing.Any) -> datetime.date:
        return datetime.datetime.fromtimestamp(obj)

    def _encode(self, obj: datetime.date, context: typing.Any, path: typing.Any) -> int:
        # Can only encode date values!
        return datetime.timestamp(obj)


COUNTER_ACCOUNT = construct.Struct(
    "counter" / U32Adapter(),
    "timestamp" / TimestampAdapter()
)

COUNTER_INSTRUCTION = construct.Struct(
    "instruction_type" / construct.Const(1, construct.BytesInteger(1, signed = False, swapped=True)),
)

DELETE_PDA_INSTRUCTION = construct.Struct(
    "instruction_type" / construct.Const(2, construct.BytesInteger(1, signed = False, swapped=True)),
)