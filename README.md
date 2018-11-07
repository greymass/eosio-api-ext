# Prerelease

The APIs provided here are still in flux based on feedback being provided by the developer community.

# Configuration

Each `.env.example` file within the `./configs` folder and subfolders must be copied and potentially modified as an `.env` in the same folder.

```
cp config/.env.example config/.env
cp config/get_currency_balances/.env.example config/get_currency_balances/.env
```

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

- `/v1/chain/get_currency_balances` runs on port 8901

### nginx configuration

Within an nginx server block, simply add a new entry that redirects to the new local API service.

For example, to run the new `get_currency_balances` API, add a new `location` entry to the `server` block of your host:

```
location /v1/chain/get_currency_balances$ {
    proxy_pass http://127.0.0.1:8901;
}
```
