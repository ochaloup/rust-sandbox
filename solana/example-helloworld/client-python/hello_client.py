import asyncio

from argparse import ArgumentParser, Namespace
from solana.rpc.async_api import AsyncClient

def get_args() -> Namespace:
    parser= ArgumentParser(description="PySerum API testing program")
    parser.add_argument(
        "-k",
        "--keypair",
        type=str,
        help="Path to a file with a keypair",
        required=True
    )
    parser.add_argument(
        "-u",
        "--url",
        type=str,
        help="RPC connection URL (consider https://api.mainnet-beta.solana.com/ or https://mango.rpcpool.com/946ef7337da3f5b8d3e4a34e7f88)",
        default="http://127.0.0.1:8899"
    )
    return parser.parse_args()

async def main(args: Namespace):
    async with AsyncClient(args.url) as client:
        res = await client.is_connected()
    print(res)  # True

args = get_args()
asyncio.run(main())