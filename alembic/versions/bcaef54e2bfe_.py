"""empty message

Revision ID: bcaef54e2bfe
Revises: 
Create Date: 2024-02-12 14:43:36.716242

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bcaef54e2bfe'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("create schema pipeline")
    op.create_table(
        "extract",
        sa.Column("extract_id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("extract_id"),
        schema="pipeline"
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
        sa.ForeignKeyConstraint(["extract_id"], ["pipeline.extract.extract_id"]),
        sa.PrimaryKeyConstraint("image_id"),
        schema="pipeline"
    )


def downgrade() -> None:
    op.drop_table("image")
    op.drop_table("extract")
