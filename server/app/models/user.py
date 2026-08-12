import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    phone_hash: Mapped[str] = mapped_column(
        String(128), unique=True, nullable=False, index=True
    )
    encrypted_phone: Mapped[str | None] = mapped_column(Text, nullable=True)
    nickname: Mapped[str | None] = mapped_column(String(64), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    display_level: Mapped[str] = mapped_column(
        Enum("pseudonym_only", "pseudonym_with_group", name="display_level"),
        default="pseudonym_only",
        nullable=False,
    )
    allow_appear_in_network: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    allow_contacts_visible: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    auth_methods = relationship("AuthMethod", back_populates="user")
    contacts = relationship("Contact", back_populates="owner", foreign_keys="Contact.owner_id")
