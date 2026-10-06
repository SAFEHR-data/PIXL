#  Copyright (c) University College London Hospitals NHS Foundation Trust
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
"""
Populate a local Lowkey Vault instance with secrets from a YAML file.

Dev-only tool: talks to Lowkey Vault (a Key Vault test double), not real
Azure Key Vault. TLS and challenge-resource verification are disabled
below on purpose, which would be inappropriate against a real vault.
"""

import os
from pathlib import Path
from typing import Annotated

import typer
import yaml

# Must be set before DefaultAzureCredential is constructed
os.environ["AZURE_POD_IDENTITY_AUTHORITY_HOST"] = "http://localhost:8080"

from azure.core.pipeline.transport import RequestsTransport
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient


def main(
    secrets_file: Annotated[
        Path,
        typer.Argument(
            exists=True,
            dir_okay=False,
            readable=True,
            help="Path to the YAML file containing secrets for the fake keyvault.",
        ),
    ],
    vault_url: Annotated[
        str,
        typer.Option(help="Base URL of the Lowkey Vault instance."),
    ] = "https://export-kv.localhost:8443",
) -> None:
    """Read NAME: value pairs from a YAML file and set them as Lowkey Vault secrets."""
    with secrets_file.open() as handle:
        secrets = yaml.safe_load(handle)

    if not secrets:
        msg = f"No secrets found in {secrets_file}. Check the path and its contents."
        raise typer.BadParameter(msg)

    client = SecretClient(
        vault_url=vault_url,
        credential=DefaultAzureCredential(),
        transport=RequestsTransport(connection_verify=False),
        verify_challenge_resource=False,
    )

    for name, value in secrets.items():
        if value is None:
            typer.echo(f"Skipping {name!r}: no value set")
            continue

        client.set_secret(name, str(value))
        typer.echo(f"Set secret: {name}")


if __name__ == "__main__":
    typer.run(main)
