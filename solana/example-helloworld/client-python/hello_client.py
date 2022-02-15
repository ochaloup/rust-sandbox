import asyncio
import layout
import base64

from os import environ
from argparse import ArgumentParser, Namespace
from solana.rpc import types
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Processed

def get_args() -> Namespace:
    parser= ArgumentParser(description="PySerum API testing program")
    parser.add_argument(
        "-k",
        "--keypair",
        type=str,
        help="Path to a file with a keypair",
        default=f"{environ['HOME']}/.config/solana/id.json"
    )
    parser.add_argument(
        "-u",
        "--url",
        type=str,
        help="RPC connection URL (consider https://api.mainnet-beta.solana.com/ or https://mango.rpcpool.com/946ef7337da3f5b8d3e4a34e7f88)",
        default="http://127.0.0.1:8899"
    )
    parser.add_argument(
        "-p",
        "--program",
        type=str,
        help="Program id where solana example helloworld resides",
        default="2LdmqPNkd5sRa2ZeNJ6sXWYsytoce29dm3QXSuer3W9j"
    )
    return parser.parse_args()

def get_json_http_account_info(account_address: str, commitment: str = str(Processed)) -> dict:
  return {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "getAccountInfo",
    "params": [ str(account_address), {"encoding": "base64", "commitment": str(commitment)}]
  }

class ProgramAccount:
    # Expected content
    # { 'jsonrpc': '2.0', 
    #   'result': {
    #     'context': {'slot': 52287},
    #     'value': {
    #       'data': ['AgAAAPQrNfDLt/AOLnM37ght50EN1n1sX3GaLrzC7iOVgz25', 'base64'],
    #       'executable': True,
    #       'lamports': 1141440,
    #       'owner': 'BPFLoaderUpgradeab1e11111111111111111111111',
    #       'rentEpoch': 0
    #     }
    #   },
    #   id': 1
    # }
    def __init__(self, json_data: dict) -> None:
        if not 'result' in json_data:
            raise ValueError(f'Expected json data does not contain result field but are {json_data}')
        result = json_data['result']
        if not result['value']['executable']:
            raise ValueError(f'Expected the account data is an executable program but it is not, {json_data}')
        self.id: int = json_data['id']
        self.latest_slot: int = result['context']['slot']
        print(f"data data: {result['value']['data'][0]}")
        self.data: bytes = base64.b64decode(result['value']['data'][0])  # expected to be base64
        self.lamports: int = result['value']['lamports']
        self.executable: bool = result['value']['executable']

class GreetingAccount(ProgramAccount):
    def __init__(self, json_data: dict) -> None:
        super().__init__(json_data)
        print(f'DEBUG: {len(self.data)} -> {layout.GREETING_ACCOUNT.sizeof()}')
        if len(self.data) != layout.GREETING_ACCOUNT.sizeof():
            raise Exception('Cannot process data from program as it is not compatible with greeting account')
        greeting_layout = layout.GREETING_ACCOUNT.parse(self.data)
        self.counter = greeting_layout.counter



# def parse_from_layout(account_info: AccountInfo, name: str, instrument_lookup: InstrumentLookup, market_lookup: MarketLookup) -> "Group":
#     data = account_info.data
#     if len(data) != layouts.GROUP.sizeof():
#         raise Exception(
#             f"Group data length ({len(data)}) does not match expected size ({layouts.GROUP.sizeof()})")

#     layout = layouts.GROUP.parse(data)
#     return Group.from_layout(layout, name, account_info, Version.V3, instrument_lookup, market_lookup)

async def main(args: Namespace):
    async with AsyncClient(args.url) as client:
        res = await client.is_connected()
        account_info = await client.get_account_info(pubkey=args.program)
    greeting = GreetingAccount(account_info)
    print(f'account: {greeting}')

args = get_args()
asyncio.run(main(args))