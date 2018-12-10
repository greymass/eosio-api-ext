import asyncio
import concurrent.futures
import json
import requests
import os
import sys
import falcon

from functools import partial

# Load Environmental Variables
max_workers = int(os.environ['GET_ACCOUNTS_UPSTREAM_WORKERS'])
max_results = int(os.environ['GET_ACCOUNTS_LIMIT'])
upstream = os.environ['UPSTREAM_API']

async def get_accounts(accounts):
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        loop = asyncio.get_event_loop()
        futures = []
        # Create a future execution of the post request in the futures pool
        for account in accounts:
            futures.append(
                loop.run_in_executor(
                    pool,
                    partial(
                        requests.post,
                        upstream + '/v1/chain/get_account',
                        json={
                            "account_name": account
                        }
                    )
                )
            )
        results = []
        # Await for all processes to complete
        for r in await asyncio.gather(*futures):
            if r.status_code == 200:
                results.append(r.json())
            pass
        # Return results
        return results

class GetAccounts:
    def on_get(self, req, resp):
        self.on_post(req, resp);
    def on_post(self, req, resp):
        # Process the request to retrieve the account name
        request = json.loads(req.stream.read())
        # Accounts to load
        accounts = request.get('accounts')
        # Throw exception if exceeding limit
        requested_accounts = len(accounts)
        if requested_accounts > max_results:
            resp.body = json.dumps({
                "code": 500,
                "message": "Exceeded maximum number of requested accounts per request (requested {}, limit {})".format(requested_accounts, max_results)
            })
        else:
            # Establish session for retrieval
            with requests.Session() as session:
                # Launch async event loop for results
                loop = asyncio.get_event_loop()
                accounts = loop.run_until_complete(get_accounts(accounts))
                # Server the response
                resp.body = json.dumps(accounts)

# Launch falcon API
app = falcon.API()
app.add_route('/v1/chain/get_accounts', GetAccounts())
