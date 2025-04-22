"""update churn trend model

Revision ID: update_churn_trend_model
Revises: 
Create Date: 2024-03-20 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'update_churn_trend_model'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Drop existing columns
    op.drop_column('churn_trend', 'segment_trends')
    op.drop_column('churn_trend', 'location_trends')
    op.drop_column('churn_trend', 'age_group_trends')
    op.drop_column('churn_trend', 'gender_trends')
    op.drop_column('churn_trend', 'subscription_length_trends')
    
    # Add new columns
    op.add_column('churn_trend', sa.Column('segment_analysis', sa.JSON(), nullable=True))
    op.add_column('churn_trend', sa.Column('location_analysis', sa.JSON(), nullable=True))
    op.add_column('churn_trend', sa.Column('future_predictions', sa.JSON(), nullable=True))
    op.add_column('churn_trend', sa.Column('factor_importance', sa.JSON(), nullable=True))
    op.add_column('churn_trend', sa.Column('factor_changes', sa.JSON(), nullable=True))
    
    # Update existing columns
    op.alter_column('churn_trend', 'date',
               existing_type=sa.Date(),
               type_=sa.DateTime(),
               existing_nullable=True,
               nullable=False)
    op.alter_column('churn_trend', 'user_id',
               existing_type=sa.INTEGER(),
               nullable=False)
    op.alter_column('churn_trend', 'churn_rate',
               existing_type=sa.FLOAT(),
               nullable=False)
    op.alter_column('churn_trend', 'high_risk_customers',
               existing_type=sa.INTEGER(),
               nullable=False)
    op.alter_column('churn_trend', 'avg_churn_score',
               existing_type=sa.FLOAT(),
               nullable=False)


def downgrade():
    # Revert column changes
    op.alter_column('churn_trend', 'avg_churn_score',
               existing_type=sa.FLOAT(),
               nullable=True)
    op.alter_column('churn_trend', 'high_risk_customers',
               existing_type=sa.INTEGER(),
               nullable=True)
    op.alter_column('churn_trend', 'churn_rate',
               existing_type=sa.FLOAT(),
               nullable=True)
    op.alter_column('churn_trend', 'user_id',
               existing_type=sa.INTEGER(),
               nullable=True)
    op.alter_column('churn_trend', 'date',
               existing_type=sa.DateTime(),
               type_=sa.Date(),
               existing_nullable=False,
               nullable=True)
    
    # Drop new columns
    op.drop_column('churn_trend', 'factor_changes')
    op.drop_column('churn_trend', 'factor_importance')
    op.drop_column('churn_trend', 'future_predictions')
    op.drop_column('churn_trend', 'location_analysis')
    op.drop_column('churn_trend', 'segment_analysis')
    
    # Re-add old columns
    op.add_column('churn_trend', sa.Column('subscription_length_trends', sa.JSON(), nullable=True))
    op.add_column('churn_trend', sa.Column('gender_trends', sa.JSON(), nullable=True))
    op.add_column('churn_trend', sa.Column('age_group_trends', sa.JSON(), nullable=True))
    op.add_column('churn_trend', sa.Column('location_trends', sa.JSON(), nullable=True))
    op.add_column('churn_trend', sa.Column('segment_trends', sa.JSON(), nullable=True)) 