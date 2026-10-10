"""add_email_verification_and_subscriptions

Revision ID: a19f82d3e4b1
Revises: 62c6a57ec0d4
Create Date: 2026-10-11 01:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a19f82d3e4b1'
down_revision: Union[str, Sequence[str], None] = '62c6a57ec0d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add email verification columns to users
    op.add_column(
        'users',
        sa.Column('is_email_verified', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    )
    op.add_column(
        'users',
        sa.Column('verification_token', sa.String(length=255), nullable=True),
    )
    op.add_column(
        'users',
        sa.Column('verification_token_expires_at', sa.DateTime(timezone=True), nullable=True),
    )

    # Automatically set existing test accounts to verified
    op.execute("UPDATE users SET is_email_verified = true")

    # 2. Create user_subscriptions table
    op.create_table(
        'user_subscriptions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('tier', sa.String(length=50), server_default='free', nullable=False),
        sa.Column('status', sa.String(length=50), server_default='active', nullable=False),
        sa.Column('current_period_start', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('current_period_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('free_lifetime_minutes_used', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_user_subscriptions_user_id_users'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_user_subscriptions')),
        sa.UniqueConstraint('user_id', name='uq_user_subscription_user_id'),
    )
    op.create_index(op.f('ix_user_subscriptions_user_id'), 'user_subscriptions', ['user_id'], unique=True)

    # 3. Create user_daily_usages table
    op.create_table(
        'user_daily_usages',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('usage_date', sa.Date(), nullable=False),
        sa.Column('minutes_used', sa.Integer(), server_default='0', nullable=False),
        sa.Column('sessions_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_user_daily_usages_user_id_users'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_user_daily_usages')),
        sa.UniqueConstraint('user_id', 'usage_date', name='uq_user_daily_usage_date'),
    )
    op.create_index(op.f('ix_user_daily_usages_user_id'), 'user_daily_usages', ['user_id'], unique=False)
    op.create_index(op.f('ix_user_daily_usages_usage_date'), 'user_daily_usages', ['usage_date'], unique=False)

    # 4. Seed default Free tier subscription for all existing users
    op.execute(
        """
        INSERT INTO user_subscriptions (id, user_id, tier, status, current_period_start, free_lifetime_minutes_used, created_at, updated_at)
        SELECT gen_random_uuid(), id, 'free', 'active', now(), 0, now(), now()
        FROM users
        ON CONFLICT (user_id) DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_table('user_daily_usages')
    op.drop_table('user_subscriptions')
    op.drop_column('users', 'verification_token_expires_at')
    op.drop_column('users', 'verification_token')
    op.drop_column('users', 'is_email_verified')
