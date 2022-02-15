import construct
import typing
from decimal import Decimal

class U32Adapter(construct.Adapter):  # u32 is unsigned 32 bit integer
    def __init__(self, size: int = 4) -> None:
        super().__init__(construct.BytesInteger(size, signed=False, swapped=True))

    def _decode(self, obj: int, context: typing.Any, path: typing.Any) -> Decimal:
        return Decimal(obj)

    def _encode(self, obj: Decimal, context: typing.Any, path: typing.Any) -> int:
        # Can only encode int values.
        return int(obj)

GREETING_ACCOUNT = construct.Struct(
    "counter" / U32Adapter()
)