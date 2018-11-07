import json
import requests
import os
import sys
import falcon

from apscheduler.schedulers.background import BackgroundScheduler

tokens = []

def get_tokens():
    global tokens
    # Request all tokens from the customtokens smart contract
    r = requests.post(os.environ['UPSTREAM_API'] + '/v1/chain/get_table_rows', json={
        'code': 'customtokens',
        'json': True,
        'limit': 1000,
        'scope': 'customtokens',
        'table': 'tokens'
    })
    if r.status_code == 200:
        temp = []
        # Iterate over rows and build the tuple
        for token in r.json().get('rows'):
            symbol = token.get('customasset').split(' ')[1]
            temp.append((symbol, token.get('customtoken')))
        # Set the global cache
        tokens = temp

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
            # Iterate and request each tokens balance
            for (symbol, code) in targetTokens:
                # Request balance from upstream API
                r = requests.post(os.environ['UPSTREAM_API'] + '/v1/chain/get_currency_balance', json={
                    'account': request.get('account'),
                    'code': code,
                    'symbol': symbol
                })
                # On success, append to balances
                if r.status_code == 200:
                    for token in r.json():
                        amount, symbol = token.split(' ')
                        balances.append({
                            'amount': float(amount),
                            'code': code,
                            'symbol': symbol,
                        })
                    # Response with list
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
