from typing import Annotated

from fastapi import APIRouter, Body, HTTPException, Path, status
from sqlmodel import Session, col, select

from app.comum import Erro, PaginacaoDep, buscar_ou_404, conflito
from app.database import SessionDep
from app.models.carteira import Carteira, CarteiraJogo
from app.models.grupo import Grupo, GrupoBase, GrupoMembro, GrupoUpdate
from app.models.jogo import Jogo
from app.models.usuario import Usuario
from app.services.grupos import MAX_MEMBROS_POR_GRUPO, adicionar_membro

router = APIRouter(prefix="/grupos", tags=["Grupos"])

# Alias reutilizável: um int com a descrição e o exemplo do parâmetro no Swagger
GrupoId = Annotated[int, Path(description="ID do grupo", examples=[1])]

NAO_ENCONTRADO = {404: {"model": Erro, "description": "Grupo não encontrado"}}


def _membros(session: Session, grupo_id: int) -> list[Usuario]:
    # col() só avisa o editor que é uma coluna do banco (para aceitar .ilike(), .desc() etc.)
    consulta = (
        select(Usuario)
        .join(GrupoMembro, col(GrupoMembro.usuario_id) == Usuario.id)
        .where(GrupoMembro.grupo_id == grupo_id)
        .order_by(col(GrupoMembro.entrou_em))
    )
    return list(session.exec(consulta).all())


@router.post(
    "",
    response_model=Grupo,
    status_code=status.HTTP_201_CREATED,
    summary="Criar grupo",
    response_description="Grupo criado, já com o dono como membro",
    responses={
        404: {"model": Erro, "description": "Dono não encontrado"},
        409: {"model": Erro, "description": "Dono desativado"},
    },
)
def criar_grupo(
    dados: Annotated[
        GrupoBase,
        Body(examples=[{"nome": "Família Souza", "descricao": "Biblioteca da família", "dono_id": 3}]),
    ],
    session: SessionDep,
) -> Grupo:
    """Cria um grupo de compartilhamento. O dono entra automaticamente como primeiro membro."""
    dono = buscar_ou_404(session, Usuario, dados.dono_id, "Dono não encontrado")
    if not dono.ativo:
        raise conflito("Usuário desativado não pode criar grupos")
    grupo = Grupo.model_validate(dados)
    session.add(grupo)
    session.flush()  # gera o id do grupo para registrar o dono como membro na mesma transação
    session.add(GrupoMembro(grupo_id=grupo.id, usuario_id=dono.id))
    session.commit()
    session.refresh(grupo)
    return grupo


@router.get("", response_model=list[Grupo], summary="Listar grupos")
def listar_grupos(session: SessionDep, pagina: PaginacaoDep) -> list[Grupo]:
    consulta = select(Grupo).order_by(col(Grupo.id)).offset(pagina.offset).limit(pagina.limit)
    return list(session.exec(consulta).all())


@router.get("/{grupo_id}", response_model=Grupo, summary="Buscar grupo", responses=NAO_ENCONTRADO)
def buscar_grupo(grupo_id: GrupoId, session: SessionDep) -> Grupo:
    return buscar_ou_404(session, Grupo, grupo_id, "Grupo não encontrado")


@router.patch(
    "/{grupo_id}",
    response_model=Grupo,
    summary="Atualizar grupo",
    responses={
        **NAO_ENCONTRADO,
        409: {"model": Erro, "description": "Novo dono não é membro do grupo"},
    },
)
def atualizar_grupo(
    grupo_id: GrupoId,
    dados: Annotated[GrupoUpdate, Body(examples=[{"nome": "Clã Souza"}, {"dono_id": 4}])],
    session: SessionDep,
) -> Grupo:
    """Atualiza nome/descrição ou transfere a posse para outro membro (`dono_id`)."""
    grupo = buscar_ou_404(session, Grupo, grupo_id, "Grupo não encontrado")
    # campos não enviados (ou enviados como null) ficam None e são ignorados: só muda o que veio
    alteracoes = dados.model_dump(exclude_none=True)
    novo_dono = alteracoes.get("dono_id")
    # o novo dono precisa já ser membro (get com a chave composta grupo_id, usuario_id)
    if novo_dono is not None and session.get(GrupoMembro, (grupo_id, novo_dono)) is None:
        raise conflito("O novo dono precisa ser membro do grupo")
    grupo.sqlmodel_update(alteracoes)
    session.add(grupo)
    session.commit()
    session.refresh(grupo)
    return grupo


@router.delete(
    "/{grupo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Excluir grupo",
    responses=NAO_ENCONTRADO,
)
def excluir_grupo(grupo_id: GrupoId, session: SessionDep) -> None:
    """Exclui o grupo. Os membros continuam com os jogos das próprias carteiras."""
    grupo = buscar_ou_404(session, Grupo, grupo_id, "Grupo não encontrado")
    session.delete(grupo)  # as participações são removidas pelo ON DELETE CASCADE do banco
    session.commit()


@router.get(
    "/{grupo_id}/membros",
    response_model=list[Usuario],
    summary="Listar membros",
    responses=NAO_ENCONTRADO,
)
def listar_membros(grupo_id: GrupoId, session: SessionDep) -> list[Usuario]:
    """Lista os membros do grupo, na ordem em que entraram."""
    buscar_ou_404(session, Grupo, grupo_id, "Grupo não encontrado")
    return _membros(session, grupo_id)


@router.post(
    "/{grupo_id}/membros",
    response_model=list[Usuario],
    status_code=status.HTTP_201_CREATED,
    summary="Adicionar membro",
    description=f"Adiciona um usuário ao grupo. Cada grupo tem no máximo "
    f"{MAX_MEMBROS_POR_GRUPO} membros, contando o dono.",
    response_description="Lista de membros atualizada",
    responses={
        404: {"model": Erro, "description": "Grupo ou usuário não encontrado"},
        409: {
            "model": Erro,
            "description": f"Grupo cheio ({MAX_MEMBROS_POR_GRUPO} membros), "
            "usuário já é membro ou usuário desativado",
        },
    },
)
def entrar_no_grupo(
    grupo_id: GrupoId,
    # embed=True: o corpo é {"usuario_id": 4}, e não só o número solto
    usuario_id: Annotated[int, Body(embed=True, description="ID do usuário a adicionar", examples=[4])],
    session: SessionDep,
) -> list[Usuario]:
    adicionar_membro(session, grupo_id, usuario_id)
    return _membros(session, grupo_id)


@router.delete(
    "/{grupo_id}/membros/{usuario_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remover membro",
    responses={
        404: {"model": Erro, "description": "Grupo não encontrado ou usuário não é membro"},
        409: {"model": Erro, "description": "O dono não pode sair do grupo"},
    },
)
def sair_do_grupo(
    grupo_id: GrupoId,
    usuario_id: Annotated[int, Path(description="ID do membro a remover", examples=[4])],
    session: SessionDep,
) -> None:
    """Remove um membro. O dono não pode sair: transfira a posse antes ou exclua o grupo."""
    grupo = buscar_ou_404(session, Grupo, grupo_id, "Grupo não encontrado")
    # chave composta (grupo_id, usuario_id): get direto, pois buscar_ou_404 recebe um id só
    membro = session.get(GrupoMembro, (grupo_id, usuario_id))
    if membro is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "O usuário não é membro deste grupo")
    if grupo.dono_id == usuario_id:
        raise conflito("O dono não pode sair do grupo; transfira a posse ou exclua o grupo")
    session.delete(membro)
    session.commit()


@router.get(
    "/{grupo_id}/jogos",
    response_model=list[Jogo],
    summary="Biblioteca compartilhada do grupo",
    responses=NAO_ENCONTRADO,
)
def biblioteca_do_grupo(grupo_id: GrupoId, session: SessionDep) -> list[Jogo]:
    """Lista todos os jogos que os membros podem jogar: a união das carteiras de todos eles."""
    buscar_ou_404(session, Grupo, grupo_id, "Grupo não encontrado")
    consulta = (
        select(Jogo)
        .join(CarteiraJogo, col(CarteiraJogo.jogo_id) == Jogo.id)
        .join(Carteira, col(Carteira.id) == CarteiraJogo.carteira_id)
        .join(GrupoMembro, col(GrupoMembro.usuario_id) == Carteira.usuario_id)
        .where(GrupoMembro.grupo_id == grupo_id)
        # distinct: se dois membros têm o mesmo jogo, ele aparece uma vez só
        .distinct()
        .order_by(col(Jogo.titulo))
    )
    return list(session.exec(consulta).all())
