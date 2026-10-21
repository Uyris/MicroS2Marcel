from fastapi import APIRouter, status
from sqlmodel import Session, col, or_, select

from app.comum import PaginacaoDep, buscar_ou_404, conflito
from app.database import SessionDep
from app.models.carteira import Carteira
from app.models.compra import Compra
from app.models.grupo import Grupo
from app.models.jogo import Jogo
from app.models.usuario import Usuario, UsuarioBase, UsuarioUpdate

router = APIRouter(prefix="/usuarios", tags=["Usuários"])


def _garantir_email_livre(session: Session, email: str) -> None:
    if session.exec(select(Usuario.id).where(Usuario.email == email)).first() is not None:
        raise conflito("Já existe um usuário com este e-mail")


@router.post("", response_model=Usuario, status_code=status.HTTP_201_CREATED)
def criar_usuario(dados: UsuarioBase, session: SessionDep) -> Usuario:
    _garantir_email_livre(session, dados.email)
    usuario = Usuario.model_validate(dados)
    session.add(usuario)
    session.flush()  # gera o id do usuário para vincular a carteira na mesma transação
    session.add(Carteira(usuario_id=usuario.id))
    session.commit()
    session.refresh(usuario)
    return usuario


@router.get("", response_model=list[Usuario])
def listar_usuarios(
    session: SessionDep,
    pagina: PaginacaoDep,
    busca: str | None = None,
    ativo: bool | None = None,
) -> list[Usuario]:
    consulta = select(Usuario)
    if busca:
        # ilike = LIKE sem diferenciar maiúsculas; o texto vai como parâmetro (sem SQL injection)
        consulta = consulta.where(col(Usuario.nome).ilike(f"%{busca}%"))
    if ativo is not None:
        consulta = consulta.where(Usuario.ativo == ativo)
    consulta = consulta.order_by(col(Usuario.id)).offset(pagina.offset).limit(pagina.limit)
    return list(session.exec(consulta).all())


@router.get("/{usuario_id}", response_model=Usuario)
def buscar_usuario(usuario_id: int, session: SessionDep) -> Usuario:
    return buscar_ou_404(session, Usuario, usuario_id, "Usuário não encontrado")


@router.patch("/{usuario_id}", response_model=Usuario)
def atualizar_usuario(usuario_id: int, dados: UsuarioUpdate, session: SessionDep) -> Usuario:
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


@router.delete("/{usuario_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_usuario(usuario_id: int, session: SessionDep) -> None:
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
