# Leonardo Briquezi
# github: https://github.com/leobrqz
# linkedin: https://www.linkedin.com/in/leonardobri
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    price: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    quantity_in_stock: int = Field(default=0, ge=0, le=2_147_483_647)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("O nome do produto não pode ficar vazio.")
        if value.isnumeric():
            raise ValueError("O nome do produto não pode ser apenas numérico.")
        return value


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    price: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    quantity_in_stock: int | None = Field(default=None, ge=0, le=2_147_483_647)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value or value.isnumeric():
            raise ValueError("Informe um nome não vazio e não numérico.")
        return value

    @model_validator(mode="after")
    def reject_null_updates(self) -> "ProductUpdate":
        if not self.model_fields_set:
            raise ValueError("Informe pelo menos um campo para atualizar.")
        for field_name in self.model_fields_set:
            if getattr(self, field_name) is None:
                raise ValueError(f"O campo {field_name} não pode ser nulo.")
        return self


class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    price: Decimal
    quantity_in_stock: int
    created_at: datetime
    updated_at: datetime


class ProductPage(BaseModel):
    items: list[ProductRead]
    page: int
    page_size: int
    total: int
    pages: int


class LowStockAlertRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_id: UUID
    threshold: int
    observed_quantity: int
    status: str
    created_at: datetime
    updated_at: datetime

