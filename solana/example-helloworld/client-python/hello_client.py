import asyncio
import base64
import json
import layout
import os

from argparse import ArgumentParser, Namespace
from os import environ
from solana.rpc import types
from pathlib import Path
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Processed
from solana.keypair import Keypair

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
        "--program-keypair",
        type=str,
        help="Path to file with program keypair",
        default=f"{environ['PROGRAM_KEYPAIR'] if 'PROGRAM_KEYPAIR' in environ else None}"
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

def load_file(filename: str) -> bytes:
    if not os.path.isfile(filename):
        raise ValueError(f"File with key '{filename}' does not exist")
    else:
        with open(filename) as key_file:
            data = json.load(key_file)
            return bytes(bytearray(data))


async def main(args: Namespace):
    # keypair_file = Path(args.keypair)
    keypair:Keypair = Keypair.from_secret_key(load_file(args.keypair))
    # program_keypair_file = Path(args.program_keypair)
    program_keypair:Keypair = Keypair.from_secret_key(load_file(args.program_keypair))

    async with AsyncClient(args.url) as client:
        res = await client.is_connected()
        account_info_json = await client.get_account_info(pubkey=program_keypair.public_key)
        
        recent_blockhash_json = await client.get_recent_blockhash()
        recent_blockhash:str = recent_blockhash_json['result']['value']['blockhash']
        lamport_per_signature:int = recent_blockhash_json['result']['value']['feeCalculator']['lamportsPerSignature']
        
        balance_json = await client.get_balance(pubkey=keypair.public_key)
        balance:int = balance_json['result']['value']

        min_balance_json = await client.get_minimum_balance_for_rent_exemption(layout.GREETING_ACCOUNT.sizeof())
        min_balance = min_balance_json['result']

        # account balance is under rent for data account and price for sending a transaction
        if balance < min_balance + lamport_per_signature:
            await client.request_airdrop()
    # greeting = GreetingAccount(account_info_json)

    print(f'account [{program_keypair.public_key}]: {account_info_json}')
    print(f'blockhash: {recent_blockhash}/{lamport_per_signature}')
    print(f'balance [{keypair.public_key}]: {balance_json}')
    print(f'min balance: {min_balance}')

args = get_args()
asyncio.run(main(args))