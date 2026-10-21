from typing import Annotated

from fastapi import APIRouter, Body, Path, Query, status
from sqlmodel import Session, col, or_, select

from app.comum import Erro, PaginacaoDep, buscar_ou_404, conflito
from app.database import SessionDep
from app.models.carteira import Carteira
from app.models.compra import Compra
from app.models.grupo import Grupo
from app.models.jogo import Jogo
from app.models.usuario import Usuario, UsuarioBase, UsuarioUpdate

router = APIRouter(prefix="/usuarios", tags=["Usuários"])

# Alias reutilizável: um int com a descrição e o exemplo do parâmetro no Swagger
UsuarioId = Annotated[int, Path(description="ID do usuário", examples=[1])]

NAO_ENCONTRADO = {404: {"model": Erro, "description": "Usuário não encontrado"}}
EMAIL_EM_USO = {409: {"model": Erro, "description": "E-mail já cadastrado"}}


def _garantir_email_livre(session: Session, email: str) -> None:
    if session.exec(select(Usuario.id).where(Usuario.email == email)).first() is not None:
        raise conflito("Já existe um usuário com este e-mail")


@router.post(
    "",
    response_model=Usuario,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar usuário",
    response_description="Usuário criado",
    responses=EMAIL_EM_USO,
)
def criar_usuario(
    dados: Annotated[
        UsuarioBase,
        Body(examples=[{"nome": "Ana Souza", "email": "ana.souza@email.com", "data_nascimento": "2002-05-17"}]),
    ],
    session: SessionDep,
) -> Usuario:
    """Cadastra um usuário e cria a carteira dele com saldo zero.

    O mesmo usuário pode comprar jogos e também vendê-los (cadastrando jogos no catálogo).
    """
    _garantir_email_livre(session, dados.email)
    usuario = Usuario.model_validate(dados)
    session.add(usuario)
    session.flush()  # gera o id do usuário para vincular a carteira na mesma transação
    session.add(Carteira(usuario_id=usuario.id))
    session.commit()
    session.refresh(usuario)
    return usuario


@router.get("", response_model=list[Usuario], summary="Listar usuários")
def listar_usuarios(
    session: SessionDep,
    pagina: PaginacaoDep,
    busca: Annotated[
        str | None,
        Query(description="Trecho do nome (ignora maiúsculas/minúsculas)", examples=["ana"]),
    ] = None,
    ativo: Annotated[bool | None, Query(description="Filtra por usuários ativos ou desativados")] = None,
) -> list[Usuario]:
    consulta = select(Usuario)
    if busca:
        # col() só avisa o editor que é uma coluna do banco (para aceitar .ilike(), .desc() etc.)
        # ilike = LIKE sem diferenciar maiúsculas; o texto vai como parâmetro (sem SQL injection)
        consulta = consulta.where(col(Usuario.nome).ilike(f"%{busca}%"))
    if ativo is not None:
        consulta = consulta.where(Usuario.ativo == ativo)
    consulta = consulta.order_by(col(Usuario.id)).offset(pagina.offset).limit(pagina.limit)
    return list(session.exec(consulta).all())


@router.get(
    "/{usuario_id}", response_model=Usuario, summary="Buscar usuário", responses=NAO_ENCONTRADO
)
def buscar_usuario(usuario_id: UsuarioId, session: SessionDep) -> Usuario:
    return buscar_ou_404(session, Usuario, usuario_id, "Usuário não encontrado")


@router.patch(
    "/{usuario_id}",
    response_model=Usuario,
    summary="Atualizar usuário",
    responses={**NAO_ENCONTRADO, **EMAIL_EM_USO},
)
def atualizar_usuario(
    usuario_id: UsuarioId,
    dados: Annotated[UsuarioUpdate, Body(examples=[{"nome": "Ana S. Lima"}, {"ativo": False}])],
    session: SessionDep,
) -> Usuario:
    """Atualiza apenas os campos enviados. Use `ativo: false` para desativar o usuário."""
    usuario = buscar_ou_404(session, Usuario, usuario_id, "Usuário não encontrado")
    # campos não enviados (ou enviados como null) ficam None e são ignorados: só muda o que veio
    alteracoes = dados.model_dump(exclude_none=True)
    if "email" in alteracoes and alteracoes["email"] != usuario.email:
        _garantir_email_livre(session, alteracoes["email"])
    usuario.sqlmodel_update(alteracoes)
    session.add(usuario)
    session.commit()
    session.refresh(usuario)
    return usuario


@router.delete(
    "/{usuario_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Excluir usuário",
    responses={
        **NAO_ENCONTRADO,
        409: {"model": Erro, "description": "Usuário possui histórico (jogos, compras ou grupos)"},
    },
)
def excluir_usuario(usuario_id: UsuarioId, session: SessionDep) -> None:
    """Exclui o usuário, sua carteira e suas participações em grupos.

    Usuários com jogos no catálogo, compras/vendas registradas ou que são donos de grupos não
    podem ser excluídos, para preservar o histórico. Nesse caso, desative-o com `PATCH`.
    """
    usuario = buscar_ou_404(session, Usuario, usuario_id, "Usuário não encontrado")

    if session.exec(select(Jogo.id).where(Jogo.vendedor_id == usuario_id)).first() is not None:
        raise conflito("O usuário vende jogos no catálogo; desative-o em vez de excluir")
    tem_compras = select(Compra.id).where(
        or_(Compra.comprador_id == usuario_id, Compra.vendedor_id == usuario_id)
    )
    if session.exec(tem_compras).first() is not None:
        raise conflito("O usuário possui compras ou vendas registradas; desative-o em vez de excluir")
    if session.exec(select(Grupo.id).where(Grupo.dono_id == usuario_id)).first() is not None:
        raise conflito("O usuário é dono de um grupo; transfira a posse ou exclua o grupo antes")

    # A carteira e as participações em grupos são removidas pelo ON DELETE CASCADE do banco
    session.delete(usuario)
    session.commit()
