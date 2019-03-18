import asyncio
import concurrent.futures
import json
import requests
import os
import sys
import falcon

from apscheduler.schedulers.background import BackgroundScheduler
from functools import partial

endpoints = {
    'apis': []
}
head_block = False

known_endpoints = [
    # Additional APIs provided by eosio-api-ext
    ('/v1/chain/get_accounts', { 'accounts': ['developjesta', 'solveforanyx'] }, [
        ('.', 'len')
    ]),
    ('/v1/chain/get_blocks', { 'blocks': [1, 2] }, [
        ('.', 'len')
    ]),
    ('/v1/chain/get_currency_balances', { 'account': 'developjesta' }, [
        ('.', 'len')
    ]),
]

upstream = os.environ['UPSTREAM_API']

def refresh_endpoints():
    global endpoints
    r = requests.post(upstream + '/v1/node/get_supported_apis')
    if r.status_code == 200:
        endpoints = r.json()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(check_endpoints())
    pprint(endpoints)

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
                        endpoints['apis'].append(path)
                    # Check a property arrays length
                    elif check == 'len' and field in data and len(data[field]) > 0:
                        endpoints['apis'].append(path)
                    # Check existence of field
                    elif check == 'exists' and field in data:
                        endpoints['apis'].append(path)
                    else:
                        endpoints['apis'].append(path)
            pass

class GetSupportedApis:
    def on_get(self, req, resp):
        self.on_post(req, resp);
    def on_post(self, req, resp):
        resp.body = json.dumps(dict(sorted(endpoints.items())))

# Load the initial endpoints on startup
refresh_endpoints()

# Schedule tokens to be refreshed from smart contract every minute
scheduler = BackgroundScheduler()
scheduler.add_job(check_endpoints, 'interval', minutes=int(os.environ['DEFAULT_GET_SUPPORTED_APIS_REFRESH']), id='check_endpoints')
scheduler.start()

# Launch falcon API
app = falcon.API()
app.add_route('/v1/api/get_supported_apis', GetSupportedApis())
