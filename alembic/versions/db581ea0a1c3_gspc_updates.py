"""gspc_updates

Revision ID: db581ea0a1c3
Revises: 12049328fd0a
Create Date: 2025-02-12 09:56:53.397539

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'db581ea0a1c3'
down_revision = '12049328fd0a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns
    op.add_column('gspc_invite', sa.Column('gspc_invite_id', sa.UUID(as_uuid=True), nullable=True))
    op.add_column('gspc_invite', sa.Column('second_invite_date', sa.DateTime(timezone=True), nullable=True))
    op.add_column('gspc_invite', sa.Column('final_invite_date', sa.DateTime(timezone=True), nullable=True))
    op.add_column('gspc_invite', sa.Column('completed_date', sa.DateTime(timezone=True), nullable=True))

    # Create unique index for gspc_invite_id
    op.create_index(
        'ix_gspc_invite_gspc_invite_id',
        'gspc_invite',
        ['gspc_invite_id'],
        unique=True
    )

    # Add foreign key column to gspc_completions
    op.add_column('gspc_completions', sa.Column('gspc_invite_id', sa.UUID(as_uuid=True), nullable=True))

    # Create foreign key constraint
    op.create_foreign_key(
        'gspc_completions_x_gspc_invite',
        'gspc_completions',
        'gspc_invite',
        ['gspc_invite_id'],
        ['gspc_invite_id']
    )


def downgrade() -> None:
    # Drop foreign key constraint and column from gspc_completions
    op.drop_constraint(None, 'gspc_completions', type_='foreignkey')
    op.drop_column('gspc_completions', 'gspc_invite_id')

    # Drop index
    op.drop_index('ix_gspc_invite_gspc_invite_id', table_name='gspc_invite')

    # Drop columns
    op.drop_column('gspc_invite', 'completed_date')
    op.drop_column('gspc_invite', 'final_invite_date')
    op.drop_column('gspc_invite', 'second_invite_date')
    op.drop_column('gspc_invite', 'gspc_invite_id')
