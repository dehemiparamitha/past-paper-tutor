"""add_document_processing_fields

Revision ID: c3f8e91d04b2
Revises: dbade63cc853
Create Date: 2026-11-07 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3f8e91d04b2'
down_revision: Union[str, None] = 'dbade63cc853'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('documents', sa.Column('processing_status', sa.String(length=50), nullable=False, server_default='UPLOADED'))
    op.add_column('documents', sa.Column('processing_error', sa.Text(), nullable=True))
    op.add_column('documents', sa.Column('processed_at', sa.DateTime(), nullable=True))
    op.create_index(op.f('ix_documents_processing_status'), 'documents', ['processing_status'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_documents_processing_status'), table_name='documents')
    op.drop_column('documents', 'processed_at')
    op.drop_column('documents', 'processing_error')
    op.drop_column('documents', 'processing_status')

