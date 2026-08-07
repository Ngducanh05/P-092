"""Category catalog and priority ceiling."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from src.database.base import Base
from src.models.enums import Category, Priority

if TYPE_CHECKING:
    from src.database.models.ticket import Ticket


def enum_values(enum_class):
    return [member.value for member in enum_class]


class CategoryCatalog(Base):
    __tablename__ = "categories"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    code: Mapped[Category] = mapped_column(
        SQLEnum(
            Category,
            name="category_code_enum",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            values_callable=enum_values,
        ),
        nullable=False,
        unique=True,
    )
    display_name: Mapped[str] = mapped_column(String(150), nullable=False)
    priority_ceiling: Mapped[Priority | None] = mapped_column(
        SQLEnum(Priority, name="priority_level_enum", native_enum=True, values_callable=enum_values),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")

    tickets: Mapped[list[Ticket]] = relationship(back_populates="category")
