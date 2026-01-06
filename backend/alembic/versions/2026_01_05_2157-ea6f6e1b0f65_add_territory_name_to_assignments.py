"""add_territory_name_to_assignments

Revision ID: ea6f6e1b0f65
Revises: fd565194c4f7
Create Date: 2026-01-05 21:57:14.255248

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ea6f6e1b0f65'
down_revision = 'fd565194c4f7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('authority_instrument_assignments', sa.Column('territory_name', sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column('authority_instrument_assignments', 'territory_name')
