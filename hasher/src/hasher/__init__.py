#  Copyright (c) 2022 University College London Hospitals NHS Foundation Trust
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
Implements the secure hashing component as a FastAPI application, to be consumed by
the DICOM, EHR & report de-identification components.

The app has a /hash endpoint which expects a message. It uses the Blake2 algorithm to
generate a 64-charcter digest in keyed hashing mode from the message.
The key is stored as a secret in an Azure Key Vault.
The Azure infrastructure (Key Vault, ServicePrincipal & permissions) must be persistent
and instructions are provided for creating these with the az CLI tool.
"""

import importlib.metadata

__version__ = importlib.metadata.version("hasher")

icon = "🪢"
