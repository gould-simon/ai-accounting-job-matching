"""Add vector search capabilities.

Revision ID: 20250208_add_vector_search
Revises: 20250208_add_user_preferences
Create Date: 2025-02-08 01:46:46.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, FLOAT

# revision identifiers, used by Alembic.
revision = '20250208_add_vector_search'
down_revision = '20250208_add_user_preferences'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Enable vector extensions and add vector columns."""
    # Enable vector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    
    # Add vector column to jobs table
    op.add_column(
        'jobs',
        sa.Column(
            'embedding',
            ARRAY(FLOAT),
            nullable=True,
            comment="Job description embedding vector"
        )
    )
    
    # Add vector column to cvs table
    op.add_column(
        'cvs',
        sa.Column(
            'embedding',
            ARRAY(FLOAT),
            nullable=True,
            comment="CV text embedding vector"
        )
    )
    
    # Create vector similarity search index for jobs
    op.execute(
        """
        CREATE INDEX ix_jobs_embedding ON jobs 
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
        """
    )
    
    # Create vector similarity search index for CVs
    op.execute(
        """
        CREATE INDEX ix_cvs_embedding ON cvs 
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
        """
    )
    
    # Add embedding_updated_at columns
    op.add_column(
        'jobs',
        sa.Column(
            'embedding_updated_at',
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When the job embedding was last updated"
        )
    )
    
    op.add_column(
        'cvs',
        sa.Column(
            'embedding_updated_at',
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When the CV embedding was last updated"
        )
    )


def downgrade() -> None:
    """Remove vector capabilities."""
    # Drop indexes
    op.execute('DROP INDEX IF EXISTS ix_jobs_embedding')
    op.execute('DROP INDEX IF EXISTS ix_cvs_embedding')
    
    # Drop columns
    op.drop_column('jobs', 'embedding_updated_at')
    op.drop_column('cvs', 'embedding_updated_at')
    op.drop_column('jobs', 'embedding')
    op.drop_column('cvs', 'embedding')
    
    # Disable vector extension
    op.execute('DROP EXTENSION IF EXISTS vector')
