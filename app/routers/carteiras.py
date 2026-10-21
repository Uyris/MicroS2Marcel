from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Body, Path
from sqlmodel import Session, col, select

from app.comum import Erro, buscar_ou_404
from app.database import SessionDep
from app.models import agora
from app.models.carteira import Carteira, CarteiraJogo
from app.models.jogo import Jogo
from app.models.usuario import Usuario

router = APIRouter(prefix="/usuarios/{usuario_id}/carteira", tags=["Carteira"])

# Alias reutilizável: um int com a descrição e o exemplo do parâmetro no Swagger
UsuarioId = Annotated[int, Path(description="ID do dono da carteira", examples=[3])]

NAO_ENCONTRADO = {404: {"model": Erro, "description": "Usuário não encontrado"}}


def _carteira_do_usuario(session: Session, usuario_id: int, *, travar: bool = False) -> Carteira:
    buscar_ou_404(session, Usuario, usuario_id, "Usuário não encontrado")
    consulta = select(Carteira).where(Carteira.usuario_id == usuario_id)
    if travar:
        consulta = consulta.with_for_update()
    # .one() não falha: todo usuário tem carteira, criada junto com ele no cadastro
    return session.exec(consulta).one()


@router.get("", response_model=Carteira, summary="Consultar saldo", responses=NAO_ENCONTRADO)
def consultar_carteira(usuario_id: UsuarioId, session: SessionDep) -> Carteira:
    """Retorna a carteira do usuário com o saldo disponível em reais."""
    return _carteira_do_usuario(session, usuario_id)


@router.get(
    "/jogos", response_model=list[Jogo], summary="Jogos da carteira", responses=NAO_ENCONTRADO
)
def listar_jogos_da_carteira(usuario_id: UsuarioId, session: SessionDep) -> list[Jogo]:
    """Lista os jogos que o usuário possui, do mais recente para o mais antigo."""
    carteira = _carteira_do_usuario(session, usuario_id)
    # col() só avisa o editor que é uma coluna do banco (para aceitar .ilike(), .desc() etc.)
    consulta = (
        select(Jogo)
        .join(CarteiraJogo, col(CarteiraJogo.jogo_id) == Jogo.id)
        .where(CarteiraJogo.carteira_id == carteira.id)
        .order_by(col(CarteiraJogo.adquirido_em).desc())
    )
    return list(session.exec(consulta).all())


@router.post(
    "/deposito",
    response_model=Carteira,
    summary="Depositar saldo",
    response_description="Carteira com o saldo atualizado",
    responses=NAO_ENCONTRADO,
)
def depositar(
    usuario_id: UsuarioId,
    # embed=True: o corpo é {"valor": "150.00"}, e não só o número solto
    valor: Annotated[
        Decimal,
        Body(
            embed=True,
            gt=0,
            le=10_000,
            max_digits=10,
            decimal_places=2,
            description="Valor a creditar, em reais (até R$ 10.000,00 por depósito)",
            examples=["150.00"],
        ),
    ],
    session: SessionDep,
) -> Carteira:
    """Credita um valor em reais na carteira do usuário, para ser usado em compras."""
    # travar=True (SELECT ... FOR UPDATE): dois depósitos simultâneos não sobrescrevem o saldo
    carteira = _carteira_do_usuario(session, usuario_id, travar=True)
    carteira.saldo += valor
    carteira.atualizada_em = agora()
    session.add(carteira)
    session.commit()
    session.refresh(carteira)
    return carteira
