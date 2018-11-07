import asyncio
import concurrent.futures
import json
import requests
import os
import sys
import falcon

from apscheduler.schedulers.background import BackgroundScheduler
from functools import partial

tokens = []

# Load Environmental Variables
default_tokens_code = os.environ['DEFAULT_CONTRACT_CODE']
default_tokens_scope = os.environ['DEFAULT_CONTRACT_SCOPE']
default_tokens_table = os.environ['DEFAULT_CONTRACT_TABLE']
max_workers = int(os.environ['GET_UPSTREAM_BALANCES_WORKERS'])
upstream = os.environ['UPSTREAM_API']

def get_tokens():
    global tokens
    # Request all tokens from the customtokens smart contract
    r = requests.post(upstream + '/v1/chain/get_table_rows', json={
        'code': default_tokens_code,
        'json': True,
        'limit': 1000,
        'scope': default_tokens_scope,
        'table': default_tokens_table
    })
    if r.status_code == 200:
        temp = []
        # Iterate over rows and build the tuple
        for token in r.json().get('rows'):
            symbol = token.get('customasset').split(' ')[1]
            temp.append((symbol, token.get('customtoken')))
        # Set the global cache
        tokens = temp

async def get_balances(account, targetTokens):
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        loop = asyncio.get_event_loop()
        futures = []
        # Create a future execution of the post request in the futures pool
        for (symbol, code) in targetTokens:
            futures.append(
                loop.run_in_executor(
                    pool,
                    partial(
                        requests.post,
                        upstream + '/v1/chain/get_currency_balance',
                        json={
                            "account": account,
                            "code": code,
                            "symbol": symbol
                        }
                    )
                )
            )
        balances = []
        # Await for all processes to complete
        for r in await asyncio.gather(*futures):
            if r.status_code == 200:
                for token in r.json():
                    amount, symbol = token.split(' ')
                    balances.append({
                        'amount': float(amount),
                        'code': code,
                        'symbol': symbol,
                    })
            pass
        # Return balances
        return balances

class GetCurrencyBalances:
    def on_post(self, req, resp):
        # Process the request to retrieve the account name
        request = json.loads(req.stream.read())
        # Establish session for retrieval of all balances
        with requests.Session() as session:
            balances = []
            # Determine which tokens to load
            targetTokens = tokens
            # If a tokens array is specified in the request, use it
            if 'tokens' in request:
                targetTokens = []
                for token in request.get('tokens'):
                    contract, symbol = token.split(':')
                    targetTokens.append((symbol, contract))
            # Launch async event loop to gather balances
            loop = asyncio.get_event_loop()
            balances = loop.run_until_complete(get_balances(request.get('account'), targetTokens))
            # Server the response
            resp.body = json.dumps(balances)

# Load the initial tokens on startup
get_tokens()

# Schedule tokens to be refreshed from smart contract every minute
scheduler = BackgroundScheduler()
scheduler.add_job(get_tokens, 'interval', minutes=1, id='get_tokens')
scheduler.start()

# Launch falcon API
app = falcon.API()
app.add_route('/v1/chain/get_currency_balances', GetCurrencyBalances())
