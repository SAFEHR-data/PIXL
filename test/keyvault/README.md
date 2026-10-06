# Lowkey Vault

Azure Key Vault test double for local tests. [Management API](https://app.swaggerhub.com/apis-docs/nagyesta/Lowkey-Vault-Management-API/v2.6.x).

`lowkey-vault` is on `pixl-net` (`test/docker-compose.yml`), port `8443`, aliases:

- `https://hasher-kv.localhost:8443`
- `https://export-kv.localhost:8443`

`*.localhost` resolves on the host; containers on `pixl-net` resolve the aliases to the vault.

`assumed-identity` mocks the Azure IMDS endpoint. It is on `imds-net` (`169.254.169.0/24`) at `169.254.169.254`, and on `pixl-net`. `test/docker-compose-test.yml` attaches `hasher-api` and `export-api` to `imds-net`. The host reaches it at `http://localhost:8080`.

Secrets load from `import/keyvault.json.hbs`. To set more:

```shell
uv run python set_secrets.py hasher-secrets.yaml --vault-url https://hasher-kv.localhost:8443
uv run python set_secrets.py export-secrets.yaml --vault-url https://export-kv.localhost:8443
```

API to download active vault data: https://localhost:8443/api/swagger-ui/swagger-ui/index.html
