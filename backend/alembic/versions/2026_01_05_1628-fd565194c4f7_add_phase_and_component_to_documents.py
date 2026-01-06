"""add_phase_and_component_to_documents

Revision ID: fd565194c4f7
Revises: 5a11329f4204
Create Date: 2026-01-05 16:28:06.388416

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fd565194c4f7'
down_revision = '5a11329f4204'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Agregar columnas phase y component a la tabla documents
    op.add_column('documents', sa.Column('phase', sa.String(length=100), nullable=True))
    op.add_column('documents', sa.Column('component', sa.String(length=100), nullable=True))


def downgrade() -> None:
    # Eliminar columnas phase y component de la tabla documents
    op.drop_column('documents', 'component')
    op.drop_column('documents', 'phase')
