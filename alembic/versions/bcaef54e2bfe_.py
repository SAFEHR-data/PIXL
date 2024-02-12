"""empty message

Revision ID: bcaef54e2bfe
Revises: 
Create Date: 2024-02-12 14:43:36.716242

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql.ddl import CreateSchema


# revision identifiers, used by Alembic.
revision: str = 'bcaef54e2bfe'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    sa.execute(CreateSchema("pipeline", if_not_exists=True))


def downgrade() -> None:
    pass
