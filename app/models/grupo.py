from datetime import datetime

from sqlmodel import Field, SQLModel

from app.models import agora


class GrupoBase(SQLModel):
    nome: str = Field(min_length=3, max_length=60)
    descricao: str | None = Field(default=None, max_length=500)
    dono_id: int = Field(foreign_key="usuario.id")


class Grupo(GrupoBase, table=True):
    # None só antes de salvar: o banco gera o id no INSERT (SERIAL PRIMARY KEY, nunca nulo no banco)
    id: int | None = Field(default=None, primary_key=True)
    criado_em: datetime = Field(default_factory=agora)


class GrupoUpdate(SQLModel):
    nome: str | None = Field(default=None, min_length=3, max_length=60)
    descricao: str | None = Field(default=None, max_length=500)
    dono_id: int | None = None


class GrupoMembro(SQLModel, table=True):
    __tablename__ = "grupo_membro"

    grupo_id: int = Field(foreign_key="grupo.id", primary_key=True)
    usuario_id: int = Field(foreign_key="usuario.id", primary_key=True)
    entrou_em: datetime = Field(default_factory=agora)
