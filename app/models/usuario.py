from datetime import date, datetime

from pydantic import EmailStr
from sqlmodel import Field, SQLModel

from app.models import agora


class UsuarioBase(SQLModel):
    nome: str = Field(min_length=2, max_length=100)
    email: EmailStr
    data_nascimento: date | None = None


class Usuario(UsuarioBase, table=True):
    # None só antes de salvar: o banco gera o id no INSERT (SERIAL PRIMARY KEY, nunca nulo no banco)
    id: int | None = Field(default=None, primary_key=True)
    ativo: bool = True
    criado_em: datetime = Field(default_factory=agora)


class UsuarioUpdate(SQLModel):
    nome: str | None = Field(default=None, min_length=2, max_length=100)
    email: EmailStr | None = None
    data_nascimento: date | None = None
    ativo: bool | None = None
