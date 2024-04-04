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

"""Project-specific configuration for Pixl."""

#
# Avoid breaking older imports
from core.project_config.pixl_config_model import PixlConfig, load_project_config
from core.project_config.tag_operations import TagOperations, load_tag_operations

__all__ = ["PixlConfig", "load_project_config", "TagOperations", "load_tag_operations"]
