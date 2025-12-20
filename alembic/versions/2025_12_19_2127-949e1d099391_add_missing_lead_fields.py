"""Alembic migration script template."""

"""add_missing_lead_fields

Revision ID: 949e1d099391
Revises: fc3b9350c72f
Create Date: 2025-12-19 21:27:13.514075+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '949e1d099391'
down_revision: Union[str, None] = 'fc3b9350c72f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema."""
    # Add missing fields to leads table
    op.add_column('leads', sa.Column('title', sa.String(255), nullable=True))
    op.add_column('leads', sa.Column('linkedin_url', sa.String(512), nullable=True))
    op.add_column('leads', sa.Column('generated_email', sa.Text(), nullable=True))
    op.add_column('leads', sa.Column('email_subject', sa.String(512), nullable=True))
    op.add_column('leads', sa.Column('final_email', sa.Text(), nullable=True))
    op.add_column('leads', sa.Column('punchline1', sa.Text(), nullable=True))
    op.add_column('leads', sa.Column('punchline2', sa.Text(), nullable=True))
    op.add_column('leads', sa.Column('punchline3', sa.Text(), nullable=True))
    op.add_column('leads', sa.Column('ghl_contact_id', sa.String(255), nullable=True))


def downgrade() -> None:
    """Downgrade database schema."""
    # Remove added fields
    op.drop_column('leads', 'ghl_contact_id')
    op.drop_column('leads', 'punchline3')
    op.drop_column('leads', 'punchline2')
    op.drop_column('leads', 'punchline1')
    op.drop_column('leads', 'final_email')
    op.drop_column('leads', 'email_subject')
    op.drop_column('leads', 'generated_email')
    op.drop_column('leads', 'linkedin_url')
    op.drop_column('leads', 'title')
