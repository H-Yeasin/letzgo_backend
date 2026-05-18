"""Rename ride_ping fields and add current_passengers

Revision ID: 5f7c9d3e1a2b
Revises: eb3a6e3b165f
Create Date: 2026-05-17 17:07:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5f7c9d3e1a2b'
down_revision: Union[str, None] = 'eb3a6e3b165f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns
    op.add_column('ride_pings', sa.Column('pickup_label', sa.String(length=200), nullable=True))
    op.add_column('ride_pings', sa.Column('destination_label', sa.String(length=300), nullable=False, server_default=''))
    op.add_column('ride_pings', sa.Column('max_passengers', sa.Integer(), nullable=False, server_default='1'))
    op.add_column('ride_pings', sa.Column('current_passengers', sa.Integer(), nullable=False, server_default='0'))

    # Migrate data from old columns to new ones
    op.execute("UPDATE ride_pings SET pickup_label = pickup_area WHERE pickup_area IS NOT NULL")
    op.execute("UPDATE ride_pings SET destination_label = destination_text WHERE destination_text IS NOT NULL")
    op.execute("UPDATE ride_pings SET max_passengers = passenger_limit WHERE passenger_limit IS NOT NULL")

    # Drop old columns
    op.drop_column('ride_pings', 'pickup_area')
    op.drop_column('ride_pings', 'destination_text')
    op.drop_column('ride_pings', 'passenger_limit')


def downgrade() -> None:
    # Add back old columns
    op.add_column('ride_pings', sa.Column('passenger_limit', sa.Integer(), nullable=True))
    op.add_column('ride_pings', sa.Column('destination_text', sa.String(length=300), nullable=True))
    op.add_column('ride_pings', sa.Column('pickup_area', sa.String(length=200), nullable=True))

    # Migrate data back
    op.execute("UPDATE ride_pings SET pickup_area = pickup_label")
    op.execute("UPDATE ride_pings SET destination_text = destination_label")
    op.execute("UPDATE ride_pings SET passenger_limit = max_passengers")

    # Drop new columns
    op.drop_column('ride_pings', 'current_passengers')
    op.drop_column('ride_pings', 'max_passengers')
    op.drop_column('ride_pings', 'destination_label')
    op.drop_column('ride_pings', 'pickup_label')