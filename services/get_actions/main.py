import json
import requests
import os
import falcon

# Load Environmental Variables
full_api = os.environ['GET_ACTIONS_ENDPOINT']
limited_api = os.environ['GET_ACTIONS_LIMITED_ENDPOINT']
history_per_account = int(os.environ['HISTORY_PER_ACCOUNT'])

class GetActions:
    def on_post(self, req, resp):
        request = json.loads(req.stream.read())
        # Retrieve Variables
        account_name = request.get('account_name')
        offset = int(request.get('offset'))
        position = int(request.get('pos'))
        # Form the default endpoint path
        endpoint = full_api + '/v1/history/get_actions'
        # Determine if this query fits in the limit history dataset
        if position == -1 and -history_per_account <= offset <= -1:
            # If so, request the data from the limited node
            endpoint = limited_api + '/v1/history/get_actions'
        # Create Request
        r = requests.post(endpoint, json={
            "account_name": account_name,
            "pos": position,
            "offset": offset
        })
        # Return response
        resp.body = r.text

# Launch falcon API
app = falcon.API()
app.add_route('/v1/history/get_actions', GetActions())
