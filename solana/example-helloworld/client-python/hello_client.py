import asyncio
import base64
import json

import layout
import os

from argparse import ArgumentParser, Namespace
from os import environ
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Processed
from solana.keypair import Keypair
from solana.publickey import PublicKey
from solana.transaction import Transaction
from solana.system_program import create_account_with_seed, CreateAccountWithSeedParams
from solana.blockhash import Blockhash

DERIVED_ADDRESS_SEED = 'HELLOWORLD'

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
        if result['value']['executable']:
            raise ValueError(f'Expected the account is an data account but it is executable, {json_data}')
        self.id: int = json_data['id']
        self.latest_slot: int = result['context']['slot']
        # print(f"we have some base64 data here: {result['value']['data'][0]}")
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

def account_exists(json_account_info:dict) -> bool:
    return (
        'result' in json_account_info and
        'value' in json_account_info['result'] and
        json_account_info['result']['value'] is not None
    )


async def main(args: Namespace):
    # keypair_file = Path(args.keypair)
    keypair:Keypair = Keypair.from_secret_key(load_file(args.keypair))
    # program_keypair_file = Path(args.program_keypair)
    program_keypair:Keypair = Keypair.from_secret_key(load_file(args.program_keypair))

    async with AsyncClient(args.url) as client:
        res = await client.is_connected()
        account_info_json = await client.get_account_info(pubkey=program_keypair.public_key)
        if not account_info_json['result']['value']['executable']:
            raise ValueError(f'Expected the account {program_keypair.public_key} is an executable program but it is not, {account_info_json}')
        
        recent_blockhash_json = await client.get_recent_blockhash()
        recent_blockhash = Blockhash(recent_blockhash_json['result']['value']['blockhash'])
        lamport_per_signature:int = recent_blockhash_json['result']['value']['feeCalculator']['lamportsPerSignature']
        
        balance_json = await client.get_balance(pubkey=keypair.public_key)
        balance:int = balance_json['result']['value']

        rent_exemption_fee_json = await client.get_minimum_balance_for_rent_exemption(layout.GREETING_ACCOUNT.sizeof())
        rent_exemption_fee = rent_exemption_fee_json['result']

        # account balance is under rent for data account and price for sending a transaction
        if balance < rent_exemption_fee + lamport_per_signature:
            requested_lamports:int = rent_exemption_fee+lamport_per_signature
            response = await client.request_airdrop(pubkey=keypair.public_key, lamports=requested_lamports)
            print(f'Requested to get airdrop for {requested_lamports}, result: {response}')

        # getting data pubkey
        program_derived_address:PublicKey = PublicKey.create_with_seed(
            from_public_key=keypair.public_key,
            seed = DERIVED_ADDRESS_SEED,
            program_id=program_keypair.public_key
        )
        pda_account_json = await client.get_account_info(pubkey=program_derived_address)
        # print(f"PDA account json: {pda_account_json}")
        if not account_exists(pda_account_json):
            print(f'Account {program_derived_address} DOES NOT exists')
            create_account_instruction = create_account_with_seed(CreateAccountWithSeedParams(
                from_pubkey=keypair.public_key,
                base_pubkey=keypair.public_key,
                new_account_pubkey=program_derived_address,
                # seed=DERIVED_ADDRESS_SEED,
                seed={"length": len(DERIVED_ADDRESS_SEED), "chars": DERIVED_ADDRESS_SEED},
                lamports=rent_exemption_fee,
                space=layout.GREETING_ACCOUNT.sizeof(),
                program_id=program_keypair.public_key
            ))
            pda_creation_txn = Transaction(
                recent_blockhash=recent_blockhash,
                nonce_info=None,
                fee_payer=keypair.public_key,
            ).add(create_account_instruction)
            # pda_creation_txn.sign(keypair)
            # await client.simulate_transaction(pda_creation_txn)
            response = await client.send_transaction(
                pda_creation_txn, keypair
            )
            print(f'Create PDA account txn response: {response}')
            pda_account_json = await client.get_account_info(pubkey=program_derived_address)

        greeting_account = GreetingAccount(pda_account_json)

    print(f'account [{program_keypair.public_key}]: {account_info_json}')
    print(f'blockhash: {recent_blockhash}, lamport per sig: {lamport_per_signature}, rent exemption: {rent_exemption_fee}')
    print(f'balance [{keypair.public_key}]: {balance_json}')
    print(f'pda account [{program_derived_address}]: {pda_account_json}')
    print(f'\nCOUNTER IS {greeting_account.counter}')

args = get_args()
asyncio.run(main(args))