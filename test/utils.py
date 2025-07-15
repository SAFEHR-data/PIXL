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

"""Utilities for the system test"""

from functools import partial, update_wrapper
from typing import cast

from core.db.models import Image
from core.db.queries import engine
from pytest_pixl.helpers import wait_for_condition
from sqlalchemy import not_
from sqlalchemy.orm import sessionmaker


def wait_for_images_to_be_exported(
    seconds_max: int,
    seconds_interval: int,
    seconds_condition_stays_true_for: int,
    min_studies: int = 2,
) -> None:
    """
    Query pixl DB to ensure that images have been processed and exported.
    If they haven't within the time limit, raise a TimeoutError
    """
    studies: list[Image] = []

    def at_least_n_studies_exported(n_studies: int) -> bool:
        nonlocal studies

        PixlSession = sessionmaker(engine)
        with PixlSession() as session:
            studies = cast(
                "list[Image]",
                session.query(Image).filter(not_(Image.exported_at.is_(None))).all(),
            )
        return len(studies) >= n_studies

    condition = partial(at_least_n_studies_exported, min_studies)
    update_wrapper(condition, at_least_n_studies_exported)

    def list_studies() -> str:
        return f"Expecting at least {min_studies} studies.\nexported studies: {studies}"

    wait_for_condition(
        condition,
        seconds_max=seconds_max,
        seconds_interval=seconds_interval,
        progress_string_fn=list_studies,
        seconds_condition_stays_true_for=seconds_condition_stays_true_for,
    )
