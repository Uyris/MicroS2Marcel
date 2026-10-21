from datetime import datetime
from decimal import Decimal

from sqlmodel import Field, SQLModel

from app.models import agora


class CompraBase(SQLModel):
    comprador_id: int = Field(foreign_key="usuario.id")
    jogo_id: int = Field(foreign_key="jogo.id")


class Compra(CompraBase, table=True):
    # None só antes de salvar: o banco gera o id no INSERT (SERIAL PRIMARY KEY, nunca nulo no banco)
    id: int | None = Field(default=None, primary_key=True)
    vendedor_id: int = Field(foreign_key="usuario.id")
    valor_pago: Decimal = Field(max_digits=10, decimal_places=2)
    realizada_em: datetime = Field(default_factory=agora)
