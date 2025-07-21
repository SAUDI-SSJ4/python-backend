from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20240716_add_is_ai_generated_to_questions'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('questions', sa.Column('is_ai_generated', sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade():
    op.drop_column('questions', 'is_ai_generated') 