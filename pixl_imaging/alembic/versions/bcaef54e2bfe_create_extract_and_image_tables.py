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
Create extract and image tables
Revision ID: bcaef54e2bfe
Revises:
Create Date: 2024-02-12 14:43:36.716242

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "bcaef54e2bfe"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "extract",
        sa.Column("extract_id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("extract_id"),
        schema="pixl_pipeline",
    )
    op.create_table(
        "image",
        sa.Column("image_id", sa.Integer(), nullable=False),
        sa.Column("accession_number", sa.String(), nullable=False),
        sa.Column("study_date", sa.Date(), nullable=False),
        sa.Column("mrn", sa.String(), nullable=False),
        sa.Column("hashed_identifier", sa.String(), nullable=True),
        sa.Column("exported_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("extract_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["extract_id"],
            ["pixl_pipeline.extract.extract_id"],
        ),
        sa.PrimaryKeyConstraint("image_id"),
        schema="pixl_pipeline",
    )


def downgrade() -> None:
    op.drop_table("image", schema="pixl_pipeline")
    op.drop_table("extract", schema="pixl_pipeline")
