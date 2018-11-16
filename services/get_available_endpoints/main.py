import asyncio
import concurrent.futures
import json
import requests
import os
import sys
import falcon

from apscheduler.schedulers.background import BackgroundScheduler
from functools import partial

endpoints = {}
head_block = False

known_endpoints = [
    ('/v1/chain/get_info', {}, [
        ('chain_id', 'exists')
    ]),
    ('/v1/chain/get_block', { 'block_num_or_id': 1000 }, [
        ('block_num', 'exists')
    ]),
    ('/v1/chain/get_block_header_state', { 'block_num_or_id': 1000 }, [
        ('block_num', 'exists')
    ]),
    ('/v1/chain/get_account', { 'account_name': 'eosio' }, [
        ('account_name', 'exists')
    ]),
    ('/v1/chain/get_abi', { 'account_name': 'eosio' }, [
        ('abi', 'exists')
    ]),
    ('/v1/chain/get_code', { 'account_name': 'eosio' }, [
        ('code_hash', 'exists')
    ]),
    ('/v1/chain/get_raw_code_and_abi', { 'account_name': 'eosio' }, [
        ('wasm', 'exists')
    ]),
    ('/v1/chain/get_table_rows', {
        'code': 'eosio',
        'scope': 'eosio',
        'table': 'producers',
        'json': True
    }, [
        ('rows', 'len')
    ]),
    ('/v1/chain/get_currency_balance', {
        'account': 'eosio',
        'code': 'eosio.token',
        'symbol': 'EOS'
    }, [
        ('.', 'len')
    ]),
    ('/v1/chain/abi_json_to_bin', {
        'code': 'eosio.token',
        'action': 'transfer',
        'args': {
            'from': 'eosio',
            'to': 'eosio',
            'quantity': '1000.000 EOS',
            'memo': 'test'
        }
    }, [
        ('binargs', 'exists')
    ]),
    ('/v1/chain/abi_bin_to_json', {
        'code': 'eosio.token',
        'action': 'transfer',
        'binargs': '000000008090b1ca000000000091b1ca40420f000000000003454f53000000000474657374'
    }, [
        ('args', 'exists')
    ]),
    ('/v1/chain/get_required_keys', {
        "available_keys": [
            "EOS7gPg8xBD8aX3rDBfxET35AXzai4hMmLi5sCw89FHF5zNEkemCm",
            "EOS7UgFowoVJ7ZAnkndjGeZBuiN1KgqsDFWuYgAxAazoFRzqzYJ1i"
        ],
        "transaction": {
            "actions": [
                {
                    "account": "eosio.token",
                    "authorization": [
                        {
                            "actor": "customtokens",
                            "permission": "active"
                        }
                    ],
                    "data": "000000008090b1ca000000000091b1ca40420f000000000003454f53000000000474657374",
                    "name": "transfer"
                }
            ],
            "context_free_actions": [],
            "context_free_data": [],
            "delay_sec": 0,
            "expiration": "2018-05-24T15:20:30.500",
            "max_kcpu_usage": 0,
            "max_net_usage_words": 0,
            "ref_block_num": 245107,
            "ref_block_prefix": 801303063,
            "signatures": [
            ]
        }
    }, [
        ('required_keys', 'exists')
    ]),
    ('/v1/chain/get_currency_stats', {
        'code': 'eosio.token',
        'symbol': 'EOS'
    }, [
        ('EOS', 'exists')
    ]),
    ('/v1/chain/get_producers', {}, [
        ('rows', 'len')
    ]),
    ('/v1/history/get_actions', {
        'account_name': 'teamgreymass',
        'pos': -1,
        'offset': -20
    }, [
        ('actions', 'len')
    ]),
    ('/v1/history/get_transaction', {
        'id': '1bc395276f4bdde15a7992e50e61938457673e861d9480b51762b6e4457e5b79'
    }, [
        ('trx', 'exists')
    ]),
    ('/v1/history/get_key_accounts', { 'public_key': 'EOS7UgFowoVJ7ZAnkndjGeZBuiN1KgqsDFWuYgAxAazoFRzqzYJ1i' }, [
        ('account_names', 'exists')
    ]),
    ('/v1/history/get_controlled_accounts', {
        'controlling_account': 'eosio'
    }, [
        ('controlled_accounts', 'exists')
    ]),
]

upstream = os.environ['UPSTREAM_API']

def refresh_endpoints():
    loop = asyncio.get_event_loop()
    balances = loop.run_until_complete(check_endpoints())

def update_head_block():
    global head_block
    r = requests.post(upstream + '/v1/chain/get_info')
    if r.status_code == 200:
        head_block = r.json().get('head_block_num')

async def check_endpoints():
    global endpoints
    update_head_block()
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        loop = asyncio.get_event_loop()
        futures = []
        paths = {}
        validations = {}
        # Create a future execution of the post request in the futures pool
        for (path, data, validation) in known_endpoints:
            paths[upstream + path] = path
            validations[upstream + path] = validation
            # Set the block to check as the most recent found
            if 'block_num_or_id' in data:
                data.update({ 'block_num_or_id': head_block })
            futures.append(
                loop.run_in_executor(
                    pool,
                    partial(
                        requests.post,
                        upstream + path,
                        json=data
                    )
                )
            )
        # Await for all processes to complete
        for r in await asyncio.gather(*futures):
            validation = validations[r.url]
            path = paths[r.url]
            data = r.json()
            if validation:
                for (field, check) in validation:
                    # Checks a root arrays length
                    if check == 'len' and field == '.' and len(data) > 0:
                        endpoints[path] = True;
                    # Check a property arrays length
                    elif check == 'len' and field in data and len(data[field]) > 0:
                        endpoints[path] = True;
                    # Check existence of field
                    elif check == 'exists' and field in data:
                        endpoints[path] = True;
                    else:
                        endpoints[path] = False;
            pass

class GetAvailableEndpoints:
    def on_post(self, req, resp):
        resp.body = json.dumps(endpoints)

# Load the initial endpoints on startup
refresh_endpoints()

# Schedule tokens to be refreshed from smart contract every minute
scheduler = BackgroundScheduler()
scheduler.add_job(check_endpoints, 'interval', minutes=int(os.environ['DEFAULT_ENDPOINT_REFRESH']), id='check_endpoints')
scheduler.start()

# Launch falcon API
app = falcon.API()
app.add_route('/v1/api/get_available_endpoints', GetAvailableEndpoints())
