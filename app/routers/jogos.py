from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Body, Path, Query, status
from sqlmodel import col, select

from app.comum import Erro, PaginacaoDep, buscar_ou_404, conflito
from app.database import SessionDep
from app.models.compra import Compra
from app.models.jogo import Genero, Jogo, JogoBase, JogoUpdate
from app.models.usuario import Usuario

router = APIRouter(prefix="/jogos", tags=["Catálogo de jogos"])

# Alias reutilizável: um int com a descrição e o exemplo do parâmetro no Swagger
JogoId = Annotated[int, Path(description="ID do jogo", examples=[1])]

NAO_ENCONTRADO = {404: {"model": Erro, "description": "Jogo não encontrado"}}

EXEMPLO_JOGO = {
    "titulo": "Crônicas de Aurora",
    "descricao": "RPG de mundo aberto em um reino flutuante.",
    "genero": "rpg",
    "preco": "89.90",
    "data_lancamento": "2025-11-20",
    "classificacao_etaria": 12,
    "vendedor_id": 1,
}


@router.post(
    "",
    response_model=Jogo,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar jogo no catálogo",
    response_description="Jogo criado",
    responses={
        404: {"model": Erro, "description": "Vendedor não encontrado"},
        409: {"model": Erro, "description": "Vendedor desativado"},
    },
)
def criar_jogo(
    dados: Annotated[JogoBase, Body(examples=[EXEMPLO_JOGO])], session: SessionDep
) -> Jogo:
    """Coloca um jogo à venda. O `vendedor_id` deve ser um usuário ativo."""
    vendedor = buscar_ou_404(session, Usuario, dados.vendedor_id, "Vendedor não encontrado")
    if not vendedor.ativo:
        raise conflito("Usuário desativado não pode vender jogos")
    jogo = Jogo.model_validate(dados)
    session.add(jogo)
    session.commit()
    session.refresh(jogo)
    return jogo


@router.get("", response_model=list[Jogo], summary="Listar jogos do catálogo")
def listar_jogos(
    session: SessionDep,
    pagina: PaginacaoDep,
    busca: Annotated[
        str | None,
        Query(description="Trecho do título (ignora maiúsculas/minúsculas)", examples=["aurora"]),
    ] = None,
    genero: Annotated[Genero | None, Query(description="Filtra por gênero")] = None,
    preco_max: Annotated[
        Decimal | None, Query(ge=0, description="Preço máximo em reais", examples=["50.00"])
    ] = None,
    vendedor_id: Annotated[int | None, Query(description="Filtra pelos jogos de um vendedor")] = None,
    disponivel: Annotated[
        bool | None,
        Query(description="true = só jogos à venda; false = só jogos fora do catálogo"),
    ] = None,
) -> list[Jogo]:
    consulta = select(Jogo)
    if busca:
        # col() só avisa o editor que é uma coluna do banco (para aceitar .ilike(), .desc() etc.)
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


@router.get("/{jogo_id}", response_model=Jogo, summary="Buscar jogo", responses=NAO_ENCONTRADO)
def buscar_jogo(jogo_id: JogoId, session: SessionDep) -> Jogo:
    return buscar_ou_404(session, Jogo, jogo_id, "Jogo não encontrado")


@router.patch("/{jogo_id}", response_model=Jogo, summary="Atualizar jogo", responses=NAO_ENCONTRADO)
def atualizar_jogo(
    jogo_id: JogoId,
    dados: Annotated[JogoUpdate, Body(examples=[{"preco": "69.90"}, {"disponivel": False}])],
    session: SessionDep,
) -> Jogo:
    """Atualiza apenas os campos enviados.

    Alterar o preço não muda compras já feitas: o log guarda o valor pago na época.
    Use `disponivel: false` para tirar o jogo do catálogo sem apagá-lo.
    """
    jogo = buscar_ou_404(session, Jogo, jogo_id, "Jogo não encontrado")
    # campos não enviados (ou enviados como null) ficam None e são ignorados: só muda o que veio
    jogo.sqlmodel_update(dados.model_dump(exclude_none=True))
    session.add(jogo)
    session.commit()
    session.refresh(jogo)
    return jogo


@router.delete(
    "/{jogo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Excluir jogo",
    responses={**NAO_ENCONTRADO, 409: {"model": Erro, "description": "O jogo já foi comprado"}},
)
def excluir_jogo(jogo_id: JogoId, session: SessionDep) -> None:
    """Exclui um jogo que nunca foi vendido. Jogos já comprados só podem ficar indisponíveis."""
    jogo = buscar_ou_404(session, Jogo, jogo_id, "Jogo não encontrado")
    if session.exec(select(Compra.id).where(Compra.jogo_id == jogo_id)).first() is not None:
        raise conflito(
            "O jogo já foi comprado; use PATCH com disponivel=false para tirá-lo do catálogo"
        )
    session.delete(jogo)
    session.commit()
