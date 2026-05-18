"""Add GIST indexes for ride_pings geometry columns

Revision ID: a1b2c3d4e5f6
Revises: 5f7c9d3e1a2b
Create Date: 2026-05-17 17:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geography


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '5f7c9d3e1a2b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add GIST indexes for spatial queries on ride_pings
    op.create_index('idx_ride_pickup', 'ride_pings', ['pickup_geom'], postgresql_using='gist')
    op.create_index('idx_ride_destination', 'ride_pings', ['destination_geom'], postgresql_using='gist')


def downgrade() -> None:
    op.drop_index('idx_ride_pickup', table_name='ride_pings')
    op.drop_index('idx_ride_destination', table_name='ride_pings')