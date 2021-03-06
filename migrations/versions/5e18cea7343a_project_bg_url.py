"""project bg url

Revision ID: 5e18cea7343a
Revises: 96d7d9cdea24
Create Date: 2020-10-01 21:26:37.433036

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5e18cea7343a'
down_revision = '96d7d9cdea24'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('project', sa.Column('background_url', sa.String(length=200), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('project', 'background_url')
    # ### end Alembic commands ###
