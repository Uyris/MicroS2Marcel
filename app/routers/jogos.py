from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Query, status
from sqlmodel import col, select

from app.comum import PaginacaoDep, buscar_ou_404, conflito
from app.database import SessionDep
from app.models.compra import Compra
from app.models.jogo import Genero, Jogo, JogoBase, JogoUpdate
from app.models.usuario import Usuario

router = APIRouter(prefix="/jogos", tags=["Catálogo de jogos"])


@router.post("", response_model=Jogo, status_code=status.HTTP_201_CREATED)
def criar_jogo(dados: JogoBase, session: SessionDep) -> Jogo:
    vendedor = buscar_ou_404(session, Usuario, dados.vendedor_id, "Vendedor não encontrado")
    if not vendedor.ativo:
        raise conflito("Usuário desativado não pode vender jogos")
    jogo = Jogo.model_validate(dados)
    session.add(jogo)
    session.commit()
    session.refresh(jogo)
    return jogo


@router.get("", response_model=list[Jogo])
def listar_jogos(
    session: SessionDep,
    pagina: PaginacaoDep,
    busca: str | None = None,
    genero: Genero | None = None,
    preco_max: Annotated[Decimal | None, Query(ge=0)] = None,
    vendedor_id: int | None = None,
    disponivel: bool | None = None,
) -> list[Jogo]:
    consulta = select(Jogo)
    if busca:
        # ilike = LIKE sem diferenciar maiúsculas; o texto vai como parâmetro (sem SQL injection)
        consulta = consulta.where(col(Jogo.titulo).ilike(f"%{busca}%"))
    if genero is not None:
        consulta = consulta.where(Jogo.genero == genero)
    if preco_max is not None:
        consulta = consulta.where(Jogo.preco <= preco_max)
    if vendedor_id is not None:
        consulta = consulta.where(Jogo.vendedor_id == vendedor_id)
    if disponivel is not None:
        consulta = consulta.where(Jogo.disponivel == disponivel)
    consulta = consulta.order_by(col(Jogo.id)).offset(pagina.offset).limit(pagina.limit)
    return list(session.exec(consulta).all())


@router.get("/{jogo_id}", response_model=Jogo)
def buscar_jogo(jogo_id: int, session: SessionDep) -> Jogo:
    return buscar_ou_404(session, Jogo, jogo_id, "Jogo não encontrado")


@router.patch("/{jogo_id}", response_model=Jogo)
def atualizar_jogo(jogo_id: int, dados: JogoUpdate, session: SessionDep) -> Jogo:
    jogo = buscar_ou_404(session, Jogo, jogo_id, "Jogo não encontrado")
    # campos não enviados (ou enviados como null) ficam None e são ignorados: só muda o que veio
    jogo.sqlmodel_update(dados.model_dump(exclude_none=True))
    session.add(jogo)
    session.commit()
    session.refresh(jogo)
    return jogo


@router.delete("/{jogo_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_jogo(jogo_id: int, session: SessionDep) -> None:
    jogo = buscar_ou_404(session, Jogo, jogo_id, "Jogo não encontrado")
    if session.exec(select(Compra.id).where(Compra.jogo_id == jogo_id)).first() is not None:
        raise conflito(
            "O jogo já foi comprado; use PATCH com disponivel=false para tirá-lo do catálogo"
        )
    session.delete(jogo)
    session.commit()
