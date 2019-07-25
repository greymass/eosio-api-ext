import asyncio
import concurrent.futures
import json
import requests
import os
import sys
import falcon

from functools import partial

# Load Environmental Variables
max_workers = int(os.environ['GET_KEYS_ACCOUNTS_UPSTREAM_WORKERS'])
max_results = int(os.environ['GET_KEYS_ACCOUNTS_LIMIT'])
upstream = os.environ['UPSTREAM_API']

async def get_keys_accounts(public_keys):
    account_cache = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        loop = asyncio.get_event_loop()
        futures = []
        # Create a future execution of the post request in the futures pool
        for public_key in public_keys:
            futures.append(
                loop.run_in_executor(
                    pool,
                    partial(
                        requests.post,
                        upstream + '/v1/history/get_key_accounts',
                        json={
                            "public_key": public_key
                        }
                    )
                )
            )
        results = {
            'account_names': [],
            'map': {}
        }
        # Await for all processes to complete
        for r in await asyncio.gather(*futures):
            if r.status_code == 200:
                body = json.loads(r.request.body)
                for account_name in r.json()['account_names']:
                    if account_name not in account_cache:
                        sys.stdout.flush()
                        r = requests.post(upstream + '/v1/chain/get_account', json={
                            "account_name": account_name
                        })
                        if r.status_code == 200:
                            account_cache[account_name] = r.json()
                    permissions = account_cache[account_name].get('permissions')
                    for permission in permissions:
                        for key in permission['required_auth']['keys']:
                            if key['key'] == body['public_key']:
                                account_authority = account_name + '@' + permission['perm_name']
                                results['account_names'].append(account_authority)
                                if body['public_key'] in results['map']:
                                    results['map'][body['public_key']].append(account_authority)
                                else:
                                    results['map'][body['public_key']] = [account_authority]
            pass
        # Return results
        return results

class GetKeysAccounts:
    def on_get(self, req, resp):
        self.on_post(req, resp);
    def on_post(self, req, resp):
        # Process the request to retrieve the account name
        request = json.loads(req.stream.read())
        # Accounts to load
        public_keys = request.get('public_keys')
        # Throw exception if exceeding limit
        requested_public_keys = len(public_keys)
        if requested_public_keys > max_results:
            resp.body = json.dumps({
                "code": 500,
                "message": "Exceeded maximum number of requested accounts per request (requested {}, limit {})".format(requested_accounts, max_results)
            })
        else:
            # Establish session for retrieval
            with requests.Session() as session:
                # Launch async event loop for results
                loop = asyncio.get_event_loop()
                results = loop.run_until_complete(get_keys_accounts(public_keys))
                # Server the response
                resp.body = json.dumps(results)

# Launch falcon API
app = falcon.API()
app.add_route('/v1/history/get_keys_accounts', GetKeysAccounts())
