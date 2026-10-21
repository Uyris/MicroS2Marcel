from datetime import datetime
from decimal import Decimal

from sqlmodel import Field, SQLModel

from app.models import agora


class Carteira(SQLModel, table=True):
    # None só antes de salvar: o banco gera o id no INSERT (SERIAL PRIMARY KEY, nunca nulo no banco)
    id: int | None = Field(default=None, primary_key=True)
    usuario_id: int = Field(foreign_key="usuario.id")
    saldo: Decimal = Field(default=Decimal("0"), max_digits=12, decimal_places=2)
    atualizada_em: datetime = Field(default_factory=agora)


class CarteiraJogo(SQLModel, table=True):
    __tablename__ = "carteira_jogo"

    carteira_id: int = Field(foreign_key="carteira.id", primary_key=True)
    jogo_id: int = Field(foreign_key="jogo.id", primary_key=True)
    adquirido_em: datetime = Field(default_factory=agora)
