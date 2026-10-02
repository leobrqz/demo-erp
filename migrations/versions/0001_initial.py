# Leonardo Briquezi
# github: https://github.com/leobrqz
# linkedin: https://www.linkedin.com/in/leonardobri
"""Create users, products and low-stock alerts.

Revision ID: 0001_initial
Revises:
Create Date: 2026-10-01
"""

from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("username", sa.String(length=80), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("username"),
    )
    op.create_table(
        "products",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("quantity_in_stock", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("price >= 0", name="ck_products_price_non_negative"),
        sa.CheckConstraint("quantity_in_stock >= 0", name="ck_products_stock_non_negative"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_products_name", "products", ["name"], unique=False)

    op.create_table(
        "low_stock_alerts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("threshold", sa.Integer(), nullable=False),
        sa.Column("observed_quantity", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("product_id"),
    )
    op.create_index("ix_low_stock_alerts_status", "low_stock_alerts", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_low_stock_alerts_status", table_name="low_stock_alerts")
    op.drop_table("low_stock_alerts")
    op.drop_index("ix_products_name", table_name="products")
    op.drop_table("products")
    op.drop_table("users")
