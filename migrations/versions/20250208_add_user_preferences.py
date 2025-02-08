"""Add user preferences.

Revision ID: 20250208_add_user_preferences
Revises: previous_revision_id
Create Date: 2025-02-08 01:44:27.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = '20250208_add_user_preferences'
down_revision = 'previous_revision_id'  # Set this to your previous migration
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add preference columns to users table."""
    # Add job preferences
    op.add_column(
        'users',
        sa.Column(
            'job_preferences',
            JSONB,
            nullable=True,
            server_default='{}',
            comment="User's job preferences"
        )
    )
    
    # Add notification preferences
    op.add_column(
        'users',
        sa.Column(
            'notification_preferences',
            JSONB,
            nullable=True,
            server_default='{}',
            comment="User's notification preferences"
        )
    )
    
    # Add search preferences
    op.add_column(
        'users',
        sa.Column(
            'search_preferences',
            JSONB,
            nullable=True,
            server_default='{}',
            comment="User's search preferences"
        )
    )
    
    # Create indexes for JSONB columns
    op.create_index(
        'ix_users_job_preferences',
        'users',
        ['job_preferences'],
        postgresql_using='gin'
    )
    op.create_index(
        'ix_users_notification_preferences',
        'users',
        ['notification_preferences'],
        postgresql_using='gin'
    )
    op.create_index(
        'ix_users_search_preferences',
        'users',
        ['search_preferences'],
        postgresql_using='gin'
    )


def downgrade() -> None:
    """Remove preference columns from users table."""
    # Drop indexes
    op.drop_index('ix_users_job_preferences')
    op.drop_index('ix_users_notification_preferences')
    op.drop_index('ix_users_search_preferences')
    
    # Drop columns
    op.drop_column('users', 'job_preferences')
    op.drop_column('users', 'notification_preferences')
    op.drop_column('users', 'search_preferences')
