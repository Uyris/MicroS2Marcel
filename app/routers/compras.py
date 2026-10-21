from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Body, Path, Query, status
from sqlmodel import col, select

from app.comum import Erro, PaginacaoDep, buscar_ou_404
from app.database import SessionDep
from app.models.compra import Compra, CompraBase
from app.services.compras import realizar_compra

router = APIRouter(prefix="/compras", tags=["Compras"])


@router.post(
    "",
    response_model=Compra,
    status_code=status.HTTP_201_CREATED,
    summary="Comprar um jogo",
    response_description="Registro da compra no log",
    responses={
        404: {"model": Erro, "description": "Comprador ou jogo não encontrado"},
        409: {
            "model": Erro,
            "description": "Saldo insuficiente, jogo já possuído, jogo indisponível, "
            "comprador desativado ou vendedor comprando o próprio jogo",
        },
    },
)
def comprar_jogo(
    dados: Annotated[CompraBase, Body(examples=[{"comprador_id": 3, "jogo_id": 1}])],
    session: SessionDep,
) -> Compra:
    """Compra um jogo do catálogo em uma única transação:

    1. debita o preço da carteira do comprador;
    2. credita o mesmo valor na carteira do vendedor;
    3. adiciona o jogo à carteira do comprador;
    4. registra a compra no log.
    """
    return realizar_compra(session, dados)


@router.get("", response_model=list[Compra], summary="Consultar log de compras")
def listar_compras(
    session: SessionDep,
    pagina: PaginacaoDep,
    comprador_id: Annotated[int | None, Query(description="Compras feitas por este usuário")] = None,
    vendedor_id: Annotated[int | None, Query(description="Vendas feitas por este usuário")] = None,
    jogo_id: Annotated[int | None, Query(description="Compras deste jogo")] = None,
    desde: Annotated[
        datetime | None,
        Query(description="Compras a partir deste instante", examples=["2026-01-01T00:00:00Z"]),
    ] = None,
    ate: Annotated[
        datetime | None,
        Query(description="Compras até este instante", examples=["2026-12-31T23:59:59Z"]),
    ] = None,
) -> list[Compra]:
    """Lista o histórico de compras, da mais recente para a mais antiga.

    O log é somente leitura: compras não podem ser alteradas nem apagadas.
    """
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
    # col() só avisa o editor que é uma coluna do banco (para aceitar .ilike(), .desc() etc.)
    consulta = (
        consulta.order_by(col(Compra.realizada_em).desc()).offset(pagina.offset).limit(pagina.limit)
    )
    return list(session.exec(consulta).all())


@router.get(
    "/{compra_id}",
    response_model=Compra,
    summary="Buscar compra",
    responses={404: {"model": Erro, "description": "Compra não encontrada"}},
)
def buscar_compra(
    compra_id: Annotated[int, Path(description="ID da compra", examples=[1])], session: SessionDep
) -> Compra:
    return buscar_ou_404(session, Compra, compra_id, "Compra não encontrada")
