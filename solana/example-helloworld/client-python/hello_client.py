from __future__ import annotations

import asyncio
import base64
import json
import datetime
import aiohttp
import sys

from numpy import record
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
from datetime import datetime, timedelta, date

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


class TransactionProcessingData:
    def __init__(self, client_time, provider,
            started_at = None,
            finished_at = None,
            txn_id = None,
            ws_time = None,
            blockchain_time = None,
            blockchain_counter = None):
        self.processing_data_updated: date = datetime.utcnow()
        # identity definition
        self.client_time: date = client_time
        self.provider: str = provider
        # transfer data
        self.started_at: date = started_at
        self.finished_at: date = finished_at
        self.txn_id: str = txn_id
        self.blockchain_time = blockchain_time
        self.blockchain_counter = blockchain_counter
        self.ws_time = ws_time

    def id(self) -> str:
        return str(self.client_time.timestamp()) + self.provider

    def merge(self, new_data: TransactionProcessingData) -> None:
        if new_data != self:
            print(f'Cannot merge {new_data} with {self} as they are not identical to provider and client_time')
        self.processing_data_updated = datetime.utcnow()
        if new_data.started_at:
            self.started_at = new_data.started_at
        if new_data.finished_at:
            self.started_at = new_data.finished_at
        if new_data.txn_id:
            self.started_at = new_data.txn_id
        if new_data.blockchain_time:
            self.blockchain_time = new_data.blockchain_time
        if new_data.blockchain_counter:
            self.blockchain_counter = new_data.blockchain_counter
        if new_data.ws_time:
            self.ws_time = new_data.ws_time

    # we define the equality based on the client_time which serves as a client_id
    # plus provider which is different to different subscriptions
    def __eq__(self, other: TransactionProcessingData):
        return self.client_time == other.client_time and self.provider == other.provider

    def __str__ (self):
        return (f'TransactionProcessingData(processing_data_update={self.processing_data_updated},'
            f' client_time={self.client_time}, provider={self.provider}, '
            f'started_at={self.started_at}, finished_at={self.finished_at}, txn_id={self.txn_id}, '
            f'blockchain_time={self.blockchain_time}, blockchain_counter={self.blockchain_counter}'
        )


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

def delta_time(time_start_at: datetime, time_finished_at = datetime.utcnow()) -> float:
    time_delta: timedelta = time_finished_at - time_start_at
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


async def increase_counter_and_wait(rpc_url: str, keypair:Keypair, program_keypair:Keypair) -> TransactionProcessingData:
    async with AsyncClient(endpoint = rpc_url, commitment=Confirmed) as client:
        # program_data_address = get_data_account_pubkey(keypair.public_key, program_keypair.public_key)
        provider: str = "onering"
        start_at: date = datetime.utcnow()
        txn = get_counter_txn(
            public_key = keypair.public_key,
            program_key = program_keypair.public_key,
            client_time = start_at
        )
        response = await client.send_transaction(txn, keypair, program_keypair)
        print(f'Counter txn response on send: {response}')  # TODO: delete me
        if 'result' not in response:
            print(f'ERROR: cannot get information about sent transaction: {response}')
            return None
        txn_id = response['result']
        finished_at: date = datetime.max
        while True:
            response_txn = await client.get_transaction(txn_id)
            if 'result' in response_txn and response_txn['result']:
                finished_at = datetime.utcnow()
                print(f"DEBUG: {response_txn['result']}")  # TODO: delete me
                break  # the transaction was found
            if delta_time(start_at) > 30:  # TODO: parametrize me
                print(f'Waiting for 30 seconds to get information about txn response["result"] to be written, BUT not yet!')
                break
        print(f'Transaction {response["result"]} takes {delta_time(start_at, finished_at)} seconds to be written to blockchain')
        return TransactionProcessingData(
            client_id=start_at,  # we use the client time as client id
            provider=provider,
            txn_id=txn_id,
            started_at=start_at,
            finished_at=finished_at
        )
        
    # pda_account_json = await client.get_account_info(pubkey=program_data_address, commitment=Finalized)
    # counter_account = CounterAccount(pda_account_json)
    # print(f'\nCOUNTER TXN {counter_account.counter}/{counter_account.timestamp}/{counter_account.client_timestamp}')


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
    provider: str = "onering"

    async with aiohttp.ClientSession().ws_connect(args.ws) as ws:
        program_data_address = get_data_account_pubkey(keypair.public_key, program_keypair.public_key)
        await ws.send_json(
            solana_account_ws_subscription(program_data_address)
        )
        response = await ws.receive(timeout=30)
        print(f'ws subscription: {response}')
        async for msg in ws:
            data = msg.json()
            print(f"---->  {data['params']}")
            counter_account = CounterAccount(data['params'])
            # print(f'>>> {counter_account.client_timestamp}')
            txn_data = TransactionProcessingData(
                client_time=counter_account.client_timestamp,
                provider=provider,
                blockchain_time=counter_account.timestamp,
                blockchain_counter=counter_account.counter,
                ws_time = datetime.utcnow()
            )
            update_in_shared_dict(shared_processing_data, txn_data)

def update_in_shared_dict(shared_processing_data: dict, record: TransactionProcessingData):
    saved_record: TransactionProcessingData = shared_processing_data[record.id()]
    if saved_record:
        saved_record.merge(record)
        shared_processing_data[record.id()] = saved_record
    else:
        shared_processing_data[record.id()] = record


async def work_with_counter(args: Namespace, shared_processing_data: dict):
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
        txn_data = await increase_counter_and_wait(args.url, keypair, program_keypair)
        update_in_shared_dict(shared_processing_data, txn_data)
        asyncio.sleep(30)
    # await get_all_program_accounts(args.url, program_keypair)
    # await delete_program_data_account_2(args.url, keypair, program_keypair)

async def update_db(args: Namespace, shared_processing_data: dict):
    while True:
        record: TransactionProcessingData
        for id, record in shared_processing_data.items():
            if record.started_at and record.blockchain_counter:
                print(f'Transaction "{record.txn_id}" got to blockchain after {delta_time(record.started_at, record.blockchain_time)}, '
                    f'txn was processed by validators after {delta_time(record.started_at, record.finished_at)}, '
                    f'received by WS after {delta_time(record.started_at, record.ws_time)}'
                )
            if delta_time(record.processing_data_updated) > 60:
                print(f'ERROR: removing record {record} from the list as timeouted after 60 second')
                shared_processing_data.pop(record)
        asyncio.sleep(10)



args = get_args()

# asyncio.run(main(args))
shared_processing_data: dict = {}  # key(provider+client_id) -> TransactionProcessingData
loop = asyncio.get_event_loop()
loop.create_task(work_with_counter(args, shared_processing_data))
loop.create_task(work_with_ws(args, shared_processing_data))
loop.create_task(update_db(args, shared_processing_data))
loop.run_forever()