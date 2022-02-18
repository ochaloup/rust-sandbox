import asyncio
import base64
import json
import datetime
import aiohttp

from tomlkit import date

import layout
import os

from argparse import ArgumentParser, Namespace
from os import environ
from solana.rpc.async_api import AsyncClient
from solana.rpc.types import TxOpts
from solana.rpc.commitment import Processed, Finalized, Confirmed
from solana.keypair import Keypair
from solana.publickey import PublicKey
from solana.transaction import Transaction, TransactionInstruction, AccountMeta
from solana.system_program import create_account_with_seed, transfer, CreateAccountWithSeedParams, TransferParams
from solana.blockhash import Blockhash
from datetime import datetime, timedelta

DERIVED_ADDRESS_SEED = 'HELLOWORLD'

def get_args() -> Namespace:
    parser= ArgumentParser(description="Solana contract testing program")
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
        "-w",
        "--ws",
        type=str,
        help="RPC WS connection (consider wss://api.mainnet-beta.solana.com/ or wss://mango.rpcpool.com/946ef7337da3f5b8d3e4a34e7f88)",
        default="ws://localhost:8900"
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
        self.id: int = json_data['id'] if 'id' in json_data else json_data['subscription']
        self.latest_slot: int = result['context']['slot']
        # print(f"we have some base64 data here: {result['value']['data'][0]}")
        self.data: bytes = base64.b64decode(result['value']['data'][0])  # expected to be base64
        self.lamports: int = result['value']['lamports']
        self.executable: bool = result['value']['executable']

class CounterAccount(ProgramAccount):
    def __init__(self, json_data: dict) -> None:
        super().__init__(json_data)
        if len(self.data) != layout.COUNTER_ACCOUNT.sizeof():
            raise Exception('Cannot process data from program as it is not compatible with counter account')
        counter_layout = layout.COUNTER_ACCOUNT.parse(self.data)
        self.counter = counter_layout.counter
        self.timestamp = counter_layout.timestamp
        self.client_timestamp = counter_layout.client_timestamp

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

def get_data_account_pubkey(public_key: PublicKey, program_key: PublicKey) -> PublicKey:
    # getting data pubkey
    return PublicKey.create_with_seed(
        from_public_key=public_key,
        seed = DERIVED_ADDRESS_SEED,
        program_id=program_key
    )

def get_counter_txn(
    public_key: PublicKey,
    program_key: PublicKey,
    client_time: date = datetime.utcnow(),
    recent_blockhash:Blockhash = None
) -> Transaction:
    program_data_key = get_data_account_pubkey(public_key, program_key)
    counter_instruction = TransactionInstruction(
        keys=[
            AccountMeta(pubkey=program_data_key, is_signer=False, is_writable=True),
            AccountMeta(pubkey=program_key, is_signer=True, is_writable=False)
        ],
        program_id=program_key,
        data=layout.COUNTER_INSTRUCTION.build({"client_timestamp": client_time})
    )
    return Transaction(
        recent_blockhash=recent_blockhash,
        nonce_info=None,
        fee_payer=public_key,
    ).add(counter_instruction)

def get_delete_pda_txn(public_key: PublicKey, program_key: PublicKey, recent_blockhash:Blockhash = None) -> Transaction:
    program_data_key = get_data_account_pubkey(public_key, program_key)
    delete_pda_instruction = TransactionInstruction(
        keys=[
            AccountMeta(pubkey=program_data_key, is_signer=False, is_writable=True),
            AccountMeta(pubkey=program_key, is_signer=True, is_writable=False),
            AccountMeta(pubkey=public_key, is_signer=True, is_writable=True),
        ],
        program_id=program_key,
        data=layout.DELETE_PDA_INSTRUCTION.build({})
    )
    return Transaction(
        recent_blockhash=recent_blockhash,
        nonce_info=None,
        fee_payer=public_key,
    ).add(delete_pda_instruction)

def delta_time(time_start_at: datetime) -> float:
    time_delta: timedelta = datetime.now() - time_start_at
    return time_delta.seconds + time_delta.microseconds / 1000000

async def get_rent_exemption_fee(client: AsyncClient) -> int:
    rent_exemption_fee_json = await client.get_minimum_balance_for_rent_exemption(layout.COUNTER_ACCOUNT.sizeof())
    return rent_exemption_fee_json['result']

async def prepare(rpc_url: str, keypair:Keypair, program_keypair:Keypair) -> CounterAccount:
    async with AsyncClient(rpc_url) as client:
        account_info_json = await client.get_account_info(pubkey=program_keypair.public_key)
        if not account_info_json['result']['value']['executable']:
            raise ValueError(f'Expected the account {program_keypair.public_key} is an executable program but it is not, {account_info_json}')
        
        recent_blockhash_json = await client.get_recent_blockhash()
        recent_blockhash = Blockhash(recent_blockhash_json['result']['value']['blockhash'])
        lamport_per_signature:int = recent_blockhash_json['result']['value']['feeCalculator']['lamportsPerSignature']
        
        balance_json = await client.get_balance(pubkey=keypair.public_key)
        balance:int = balance_json['result']['value']

        # account balance is under rent for data account and price for sending a transaction
        rent_exemption_fee = await get_rent_exemption_fee(client)
        if balance < rent_exemption_fee + lamport_per_signature:
            requested_lamports:int = rent_exemption_fee+lamport_per_signature
            response = await client.request_airdrop(pubkey=keypair.public_key, lamports=requested_lamports)
            print(f'Requested to get airdrop for {requested_lamports}, result: {response}')

        program_data_address = get_data_account_pubkey(keypair.public_key, program_keypair.public_key)
        pda_account_json = await client.get_account_info(pubkey=program_data_address, commitment=Processed)
        # print(f"PDA account json: {pda_account_json}")
        if not account_exists(pda_account_json):
            print(f'Account {program_data_address} DOES NOT exists')
            create_account_instruction = create_account_with_seed(CreateAccountWithSeedParams(
                from_pubkey=keypair.public_key,
                base_pubkey=keypair.public_key,
                new_account_pubkey=program_data_address,
                # seed=DERIVED_ADDRESS_SEED,
                seed={"length": len(DERIVED_ADDRESS_SEED), "chars": DERIVED_ADDRESS_SEED},
                lamports=rent_exemption_fee,
                space=layout.COUNTER_ACCOUNT.sizeof(),
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
            while not account_exists(pda_account_json):
                pda_account_json = await client.get_account_info(pubkey=program_data_address, commitment=Finalized)

    print(f'account [{program_keypair.public_key}]: {account_info_json}')
    print(f'blockhash: {recent_blockhash}, lamport per sig: {lamport_per_signature}, rent exemption: {rent_exemption_fee}')
    print(f'balance [{keypair.public_key}]: {balance_json}')
    print(f'pda account [{program_data_address}]: {pda_account_json}')
    counter_account = CounterAccount(pda_account_json)
    print(f'COUNTER PREPARE {counter_account.counter}/{counter_account.timestamp}')
    return counter_account


async def increase_counter_and_wait(rpc_url: str, keypair:Keypair, program_keypair:Keypair) -> CounterAccount:
    async with AsyncClient(endpoint = rpc_url, commitment=Confirmed) as client:
        program_data_address = get_data_account_pubkey(keypair.public_key, program_keypair.public_key)
        txn = get_counter_txn(keypair.public_key, program_keypair.public_key)
        time_start_at = datetime.now()
        response = await client.send_transaction(txn, keypair, program_keypair)
        print(f'Counter txn response on send: {response}')
        while True:
            response_txn = await client.get_transaction(response['result'])
            # print(f'DEBUG: {response_txn}')
            if 'result' in response_txn and response_txn['result']:
                break  # the transaction was found
            if delta_time(time_start_at) > 15:
                print(f'Waiting for 15 seconds to get information about txn response["result"] to be written, BUT not yet!')
                break
        print(f'Transaction {response["result"]} takes {delta_time(time_start_at)} seconds to be written to blockchain')
        pda_account_json = await client.get_account_info(pubkey=program_data_address, commitment=Finalized)

    counter_account = CounterAccount(pda_account_json)
    print(f'\nCOUNTER TXN {counter_account.counter}/{counter_account.timestamp}/{counter_account.client_timestamp}')


async def get_all_program_accounts(rpc_url: str, program_keypair:Keypair) -> None:
    async with AsyncClient(endpoint = rpc_url, commitment=Confirmed) as client:
        program_accounts = await client.get_program_accounts(program_keypair.public_key)
        program_accounts_info = []
        if 'result' in program_accounts:
            for program_account in program_accounts['result']:
                program_account_pubkey = program_account['pubkey']
                program_account_info = await client.get_account_info(pubkey=program_account_pubkey)
                program_accounts_info.append(program_account_info)
        print(f'Program accounts:\n{program_accounts}\nInfos: {program_accounts_info}')


# removing the account means to take off out all the Solana balance, the account will be purged by validator
## 
# Error when sending from user wallet to a executable account
# solana.rpc.core.RPCException: {'code': -32002, 'message': 'Transaction simulation failed: Transaction loads a writable account that cannot be written', 'data': {'accounts': None, 'err': 'InvalidWritableAccount', 'logs': [], 'unitsConsumed': 0}}
# ---
# Error when sending from PDA to wallet
# solana.rpc.core.RPCException: {'code': -32602, 'message': 'invalid transaction: Transaction failed to sanitize accounts offsets correctly'}
# ---
# Transfering from program to a wallet can be done only in smart contract, the data program is owned by program and not by system 11111111111111 program
# thus the solana_system::transfer cannot work. We need own smart contract that works with values.
# !!!!! 1THIS DOES NOT WORK !!!!!!
async def delete_program_data_account_1(rpc_url: str, keypair:Keypair, program_keypair:Keypair) -> None:
    async with AsyncClient(endpoint = rpc_url, commitment=Confirmed) as client:
        program_data_address = get_data_account_pubkey(keypair.public_key, program_keypair.public_key)
        program_data_info = await client.get_account_info(pubkey=program_data_address)
        print(f'Transfering from: {program_data_address}, to: {keypair.public_key}; owner of data: {program_data_info["result"]["value"]["owner"]}')
        print(f'Signing with: {keypair.public_key} + {program_keypair.public_key}')
        transfer_instruction = transfer(TransferParams(
            from_pubkey = program_data_address,
            to_pubkey = keypair.public_key,
            lamports=1
        ))
        transfer_txn = Transaction(
            fee_payer=keypair.public_key
        ).add(transfer_instruction)
        response = await client.send_transaction(transfer_txn, keypair, program_keypair)
        print(f'>>delete_wrong> {response}')


async def delete_program_data_account_2(rpc_url: str, keypair:Keypair, program_keypair:Keypair) -> None:
    async with AsyncClient(endpoint = rpc_url, commitment=Confirmed) as client:
        program_data_address = get_data_account_pubkey(keypair.public_key, program_keypair.public_key)
        print(f'PDA pubkey: {program_data_address}')
        delete_pda_txn = get_delete_pda_txn(keypair.public_key, program_keypair.public_key)
        response = await client.send_transaction(delete_pda_txn, keypair, program_keypair)
        print(f'>>delete_program> {response}')

def solana_account_ws_subscription(address: str, commitment: str = str(Processed)) -> dict:
    subscription_id: int = datetime.now().timestamp()
    return {
        "jsonrpc": "2.0",
        "id": str(subscription_id),
        "method": "accountSubscribe",
        "params": [str(address), {"encoding": "base64", "commitment": str(commitment)}],
    }

async def work_with_ws(args: Namespace):
    keypair:Keypair = Keypair.from_secret_key(load_file(args.keypair))
    program_keypair:Keypair = Keypair.from_secret_key(load_file(args.program_keypair))

    async with aiohttp.ClientSession().ws_connect(args.ws) as ws:
        program_data_address = get_data_account_pubkey(keypair.public_key, program_keypair.public_key)
        await ws.send_json(
            solana_account_ws_subscription(program_data_address)
        )
        response = await ws.receive(timeout=15)
        print(f'ws subscription: {response}')
        async for msg in ws:
            data = msg.json()
            print(f"---->  {data['params']}")
            counter_account = CounterAccount(data['params'])
            print(f'>>> {counter_account.client_timestamp}')

async def work_with_counter(args: Namespace):
    # keypair_file = Path(args.keypair)
    keypair:Keypair = Keypair.from_secret_key(load_file(args.keypair))
    # program_keypair_file = Path(args.program_keypair)
    program_keypair:Keypair = Keypair.from_secret_key(load_file(args.program_keypair))
    print('-' * 120)
    print(f'User pubkey: "{keypair.public_key}, program key: {program_keypair.public_key}')
    print('-' * 120 + '\n\n')

    # await prepare(args.url, keypair, program_keypair)
    for i in range(1,20):
        print(f'LOOP {i}')
        await increase_counter_and_wait(args.url, keypair, program_keypair)
        asyncio.sleep(15)
    # await get_all_program_accounts(args.url, program_keypair)
    # await delete_program_data_account_2(args.url, keypair, program_keypair)

args = get_args()

# asyncio.run(main(args))
loop = asyncio.get_event_loop()
loop.create_task(work_with_counter(args))
loop.create_task(work_with_ws(args))
loop.run_forever()