from datetime import datetime

from fastapi import APIRouter, status
from sqlmodel import col, select

from app.comum import PaginacaoDep, buscar_ou_404
from app.database import SessionDep
from app.models.compra import Compra, CompraBase
from app.services.compras import realizar_compra

router = APIRouter(prefix="/compras", tags=["Compras"])


@router.post("", response_model=Compra, status_code=status.HTTP_201_CREATED)
def comprar_jogo(dados: CompraBase, session: SessionDep) -> Compra:
    return realizar_compra(session, dados)


@router.get("", response_model=list[Compra])
def listar_compras(
    session: SessionDep,
    pagina: PaginacaoDep,
    comprador_id: int | None = None,
    vendedor_id: int | None = None,
    jogo_id: int | None = None,
    desde: datetime | None = None,
    ate: datetime | None = None,
) -> list[Compra]:
    consulta = select(Compra)
    if comprador_id is not None:
        consulta = consulta.where(Compra.comprador_id == comprador_id)
    if vendedor_id is not None:
        consulta = consulta.where(Compra.vendedor_id == vendedor_id)
    if jogo_id is not None:
        consulta = consulta.where(Compra.jogo_id == jogo_id)
    if desde is not None:
        consulta = consulta.where(Compra.realizada_em >= desde)
    if ate is not None:
        consulta = consulta.where(Compra.realizada_em <= ate)
    consulta = (
        consulta.order_by(col(Compra.realizada_em).desc()).offset(pagina.offset).limit(pagina.limit)
    )
    return list(session.exec(consulta).all())


@router.get("/{compra_id}", response_model=Compra)
def buscar_compra(compra_id: int, session: SessionDep) -> Compra:
    return buscar_ou_404(session, Compra, compra_id, "Compra não encontrada")
