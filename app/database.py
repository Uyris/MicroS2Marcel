"""Conexão com o PostgreSQL e sessão do ORM usada pelas rotas.

As tabelas são criadas pelo script sql/criar_tabelas.sql, não pela aplicação.
"""

from collections.abc import Generator
from typing import Annotated

from fastapi import Depends
from sqlmodel import Session, create_engine

from app.config import settings

engine = create_engine(settings.database_url, echo=settings.sql_echo, pool_pre_ping=True)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
