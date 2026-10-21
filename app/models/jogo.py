from datetime import date, datetime
from decimal import Decimal
from enum import Enum

from sqlmodel import Field, SQLModel

from app.models import agora


class Genero(str, Enum):
    acao = "acao"
    aventura = "aventura"
    rpg = "rpg"
    estrategia = "estrategia"
    esportes = "esportes"
    corrida = "corrida"
    simulacao = "simulacao"
    puzzle = "puzzle"
    terror = "terror"
    luta = "luta"


class JogoBase(SQLModel):
    titulo: str = Field(min_length=1, max_length=150)
    descricao: str | None = Field(default=None, max_length=2000)
    genero: Genero
    preco: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    data_lancamento: date
    classificacao_etaria: int = Field(ge=0, le=18)
    vendedor_id: int = Field(foreign_key="usuario.id")


class Jogo(JogoBase, table=True):
    # None só antes de salvar: o banco gera o id no INSERT (SERIAL PRIMARY KEY, nunca nulo no banco)
    id: int | None = Field(default=None, primary_key=True)
    disponivel: bool = True
    criado_em: datetime = Field(default_factory=agora)


class JogoUpdate(SQLModel):
    titulo: str | None = Field(default=None, min_length=1, max_length=150)
    descricao: str | None = Field(default=None, max_length=2000)
    genero: Genero | None = None
    preco: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    data_lancamento: date | None = None
    classificacao_etaria: int | None = Field(default=None, ge=0, le=18)
    disponivel: bool | None = None
