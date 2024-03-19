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

"""Datetime helper functions."""

import logging
from random import randint
from typing import Any

import arrow


def combine_date_time(a_date: str, a_time: str) -> Any:
    """Turn date string and time string into arrow object."""
    date_time_str = f"{a_date} {a_time}"

    # TODO: Should Timezone be hardcoded?
    # https://github.com/UCLH-Foundry/PIXL/issues/151
    tz = "Europe/London"

    try:
        new_date_time = arrow.get(date_time_str, tzinfo=tz)
    except arrow.parser.ParserError:
        logging.exception(
            f"Failed to parse the datetime string '{date_time_str}'"
            f"falling back to a random time in 1970"
        )
        new_date_time = arrow.get("1970-01-01T00:00:00+00:00")
        new_date_time = new_date_time.shift(seconds=randint(10**2, 10**7))

    return new_date_time


def format_date_time(a_date_time: str) -> Any:
    """Turn date-time string into arrow object."""
    if "." not in a_date_time:
        a_date_time += ".000000"

    if a_date_time[8] != " ":
        a_date_time = a_date_time[0:8] + " " + a_date_time[8:]

    if arrow.get(a_date_time, "YYYYMMDD HHmmss.SSSSSS"):
        a_date = "{s}".format(s=arrow.get(a_date_time).format("YYYYMMDD"))
        a_time = "{s}".format(s=arrow.get(a_date_time).format("HHmmss.SSSSSS"))

    return combine_date_time(a_date, a_time)
