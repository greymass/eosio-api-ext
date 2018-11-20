import asyncio
import concurrent.futures
import json
import requests
import os
import sys
import falcon

from functools import partial

# Load Environmental Variables
max_workers = int(os.environ['GET_BLOCKS_UPSTREAM_WORKERS'])
max_results = int(os.environ['GET_BLOCKS_LIMIT'])
upstream = os.environ['UPSTREAM_API']

async def get_blocks(blocks):
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        loop = asyncio.get_event_loop()
        futures = []
        # Create a future execution of the post request in the futures pool
        for block in blocks:
            futures.append(
                loop.run_in_executor(
                    pool,
                    partial(
                        requests.post,
                        upstream + '/v1/chain/get_block',
                        json={
                            "block_num_or_id": block
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
    def on_post(self, req, resp):
        # Process the request to retrieve the block name
        request = json.loads(req.stream.read())
        # Accounts to load
        blocks = request.get('blocks')
        # Throw exception if exceeding limit
        requested_blocks = len(blocks)
        if requested_blocks > max_results:
            resp.body = json.dumps({
                "code": 500,
                "message": "Exceeded maximum number of requested blocks per request (requested {}, limit {})".format(requested_blocks, max_results)
            })
        else:
            # Establish session for retrieval
            with requests.Session() as session:
                # Launch async event loop for results
                loop = asyncio.get_event_loop()
                blocks = loop.run_until_complete(get_blocks(blocks))
                # Server the response
                resp.body = json.dumps(blocks)

# Launch falcon API
app = falcon.API()
app.add_route('/v1/chain/get_blocks', GetAccounts())
