"""Utilitários compartilhados pelas rotas e pelos serviços."""

from dataclasses import dataclass
from typing import Annotated, TypeVar

from fastapi import Depends, HTTPException, Query, status
from sqlmodel import Session, SQLModel

# Tipo genérico: buscar_ou_404(..., Usuario, ...) devolve um Usuario, com Jogo devolve um Jogo, etc.
ModeloT = TypeVar("ModeloT", bound=SQLModel)


class Erro(SQLModel):
    """Formato das respostas de erro da API (usado na documentação)."""

    detail: str


def buscar_ou_404(
    session: Session, modelo: type[ModeloT], chave: int, mensagem: str, *, travar: bool = False
) -> ModeloT:
    """Busca pela chave primária ou responde 404. Com `travar=True` usa SELECT ... FOR UPDATE."""
    objeto = session.get(modelo, chave, with_for_update=travar)
    if objeto is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, mensagem)
    return objeto


def conflito(mensagem: str) -> HTTPException:
    """Erro 409: a requisição é válida, mas viola uma regra de negócio. Uso: raise conflito("...")."""
    return HTTPException(status.HTTP_409_CONFLICT, mensagem)


@dataclass
class Paginacao:
    offset: int
    limit: int


def paginacao(
    offset: Annotated[int, Query(ge=0, description="Quantidade de registros a pular")] = 0,
    limit: Annotated[
        int, Query(ge=1, le=100, description="Quantidade máxima de registros retornados")
    ] = 20,
) -> Paginacao:
    return Paginacao(offset=offset, limit=limit)


PaginacaoDep = Annotated[Paginacao, Depends(paginacao)]
