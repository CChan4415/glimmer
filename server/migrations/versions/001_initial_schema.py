"""Initial schema: users, auth_methods, contacts, contact_tags, tag_presets

Revision ID: 001
Revises:
Create Date: 2026-08-12
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("phone_hash", sa.String(128), unique=True, nullable=False, index=True),
        sa.Column("encrypted_phone", sa.Text(), nullable=True),
        sa.Column("nickname", sa.String(64), nullable=True),
        sa.Column("avatar_url", sa.Text(), nullable=True),
        sa.Column("display_level", sa.String(32), nullable=False, server_default="pseudonym_only"),
        sa.Column("allow_appear_in_network", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("allow_contacts_visible", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True, index=True),
    )

    op.create_table(
        "auth_methods",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("method", sa.String(16), nullable=False),
        sa.Column("identifier", sa.String(256), nullable=False),
        sa.Column("wechat_union_id", sa.String(256), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_unique_constraint("uq_auth_methods_method_identifier", "auth_methods", ["method", "identifier"])

    op.create_table(
        "contacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("phone_hash", sa.String(128), nullable=True, index=True),
        sa.Column("group", sa.String(16), nullable=False, server_default="ungrouped"),
        sa.Column("is_manual", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("last_contacted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "contact_tags",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("contact_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("tag", sa.String(64), nullable=False),
    )
    op.create_unique_constraint("uq_contact_tags_contact_tag", "contact_tags", ["contact_id", "tag"])

    op.create_table(
        "tag_presets",
        sa.Column("tag", sa.String(64), primary_key=True),
        sa.Column("category", sa.String(32), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_table("tag_presets")
    op.drop_table("contact_tags")
    op.drop_table("contacts")
    op.drop_table("auth_methods")
    op.drop_table("users")
