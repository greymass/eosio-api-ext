# Prerelease

The APIs provided here are still in flux based on feedback being provided by the developer community.

For a list of API methods enabled by this project, please refer to the [API Request/Response Examples](https://github.com/greymass/eosio-api-ext/wiki/API-Request-Response-Examples) wiki.

# Configuration

A global config file exists as `./config/.env` and each API method has it's own individual config that lives in `./config/[method_name]/.env`. The global file is loaded first, followed by the individual methods file, allowing each method to also override global variables for specific use-cases. These files are loaded as environmental variables and set on the specific containers for each method.

These files are not part of the git repository - but an example of each file with all possible variables exists in each folder as `.env.example`.

Since these files are required to exist for the containers to operate, a simple bash script has been created to automate the creation process. This file can be run from the root directory of this project.

```
sh ./init_config.sh
```

This script will initialize (or reinitialize) all of the various files within `./config` with their default values and override any existing configuration.

# Running

This entire repository is designed to be run easily under Docker using docker-compose. With both Docker and docker-compose installed, clone this repository, enter the folder and run:

```
docker network create -d bridge --subnet 192.168.0.0/24 --gateway 192.168.0.1 eosio_api_network
docker-compose build
docker-compose up -d
```

The processes specified in the `docker-compose.yaml` file will be automatically configured and started.

From within the same project folder, you can tail the logs via:

```
docker-compose logs -f --tail="200"
```

# Ports

Each API service will bind to a different IP address on the localhost, which can then be used via a proxy to redirect specific API requests to these new services.

- `/v1/api/get_available_endpoints` runs on port 8900
- `/v1/chain/get_currency_balances` runs on port 8901
- `/v1/chain/get_accounts` runs on port 8902
- `/v1/chain/get_blocks` runs on port 8903
- `/v1/node/get_supported_apis` runs on port 8905

### nginx configuration

Within an nginx server block, simply add a new entry that redirects to the new local API service.

For example, to run the new `get_currency_balances` API, add a new `location` entry to the `server` block of your host:

```
location /v1/api/get_available_endpoints$ {
    proxy_pass http://127.0.0.1:8900;
}

location /v1/chain/get_currency_balances$ {
    proxy_pass http://127.0.0.1:8901;
}

location /v1/chain/get_accounts$ {
    proxy_pass http://127.0.0.1:8902;
}

location /v1/chain/get_blocks$ {
    proxy_pass http://127.0.0.1:8903;
}

location /v1/node/get_supported_apis$ {
    proxy_pass http://127.0.0.1:8905;
}
```
