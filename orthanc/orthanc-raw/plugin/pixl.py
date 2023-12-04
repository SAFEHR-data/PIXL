"""

Facilitates routing of stable studies from orthanc-raw to orthanc-anon

This module provides:
-OnChange: route stable studies and if auto-routing enabled
-ShouldAutoRoute: checks whether auto-routing is enabled
-OnHeartBeat: extends the REST API

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
import os

import orthanc


def OnChange(changeType, level, resourceId):  # noqa: ARG001
    """
    # Taken from:
    # https://book.orthanc-server.com/plugins/python.html#auto-routing-studies
    This routes any stable study to a modality named PIXL-Anon if
    ShouldAutoRoute returns true
    """
    if changeType == orthanc.ChangeType.STABLE_STUDY and ShouldAutoRoute():
        print("Stable study: %s" % resourceId)  # noqa: T201
        orthanc.RestApiPost("/modalities/PIXL-Anon/store", resourceId)


def OnHeartBeat(output, uri, **request):  # noqa: ARG001
    """Extends the REST API by registering a new route in the REST API"""
    orthanc.LogWarning("OK")
    output.AnswerBuffer("OK\n", "text/plain")


def ShouldAutoRoute():
    """
    Checks whether ORTHANC_AUTOROUTE_RAW_TO_ANON environment variable is
    set to true or false
    """
    return os.environ.get("ORTHANC_AUTOROUTE_RAW_TO_ANON", "false").lower() == "true"


orthanc.RegisterOnChangeCallback(OnChange)
orthanc.RegisterRestCallback("/heart-beat", OnHeartBeat)
