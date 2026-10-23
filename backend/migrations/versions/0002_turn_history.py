"""Persist source commands and ordering for session-history recovery."""
from alembic import op
import sqlalchemy as sa
revision='0002'
down_revision='0001'
branch_labels=None
depends_on=None

def upgrade():
    # 0001 originally reflected current metadata. Detect columns so both original
    # databases and fresh installs migrate safely; future migrations stay explicit.
    columns={c['name'] for c in sa.inspect(op.get_bind()).get_columns('turns')}
    if 'request_json' not in columns:op.add_column('turns',sa.Column('request_json',sa.Text(),nullable=False,server_default='{}'))
    if 'created_at' not in columns:op.add_column('turns',sa.Column('created_at',sa.Float(),nullable=False,server_default='0'))

def downgrade():
    with op.batch_alter_table('turns') as batch:
        batch.drop_column('created_at');batch.drop_column('request_json')
