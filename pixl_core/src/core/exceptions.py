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

"""Custom exceptions for PIXL."""


class PixlDiscardError(RuntimeError):
    """
    Expected application error.

    Exception that will be caught and whose message will be displayed
    (without a stack trace).
    """


class PixlSkipInstanceError(RuntimeError):
    """Study instance should be ignored."""


class PixlRequeueMessageError(RuntimeError):
    """Requeue PIXL message."""


class PixlOutOfHoursError(Exception):
    """Nack and requeue PIXL message."""


class PixlStudyNotInPrimaryArchiveError(Exception):
    """Study not in primary archive."""
