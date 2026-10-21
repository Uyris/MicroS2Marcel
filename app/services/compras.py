"""Regra de negócio da compra de um jogo."""

from sqlmodel import Session, col, select

from app.comum import buscar_ou_404, conflito
from app.models import agora
from app.models.carteira import Carteira, CarteiraJogo
from app.models.compra import Compra, CompraBase
from app.models.jogo import Jogo
from app.models.usuario import Usuario


def realizar_compra(session: Session, dados: CompraBase) -> Compra:
    """Debita o comprador, credita o vendedor, coloca o jogo na carteira e registra o log.

    Tudo acontece em uma única transação: ou todas as alterações são gravadas, ou nenhuma.
    """
    comprador = buscar_ou_404(session, Usuario, dados.comprador_id, "Comprador não encontrado")
    jogo = buscar_ou_404(session, Jogo, dados.jogo_id, "Jogo não encontrado")

    if not comprador.ativo:
        raise conflito("Usuário desativado não pode comprar jogos")
    if not jogo.disponivel:
        raise conflito("Este jogo não está disponível para venda")
    if jogo.vendedor_id == comprador.id:
        raise conflito("O vendedor não pode comprar o próprio jogo")

    # Trava as duas carteiras até o commit, sempre na mesma ordem (por id) para evitar deadlock.
    # Assim duas compras simultâneas do mesmo usuário não gastam o mesmo saldo duas vezes.
    # (col() é só um helper do SQLModel para o editor reconhecer a coluna e aceitar .in_())
    carteiras = session.exec(
        select(Carteira)
        .where(col(Carteira.usuario_id).in_([comprador.id, jogo.vendedor_id]))
        .order_by(col(Carteira.id))
        .with_for_update()
    ).all()
    por_usuario = {carteira.usuario_id: carteira for carteira in carteiras}
    carteira_comprador = por_usuario[comprador.id]
    carteira_vendedor = por_usuario[jogo.vendedor_id]

    # CarteiraJogo tem chave composta, por isso o get recebe a tupla (carteira_id, jogo_id)
    if session.get(CarteiraJogo, (carteira_comprador.id, jogo.id)) is not None:
        raise conflito("O usuário já possui este jogo")
    if carteira_comprador.saldo < jogo.preco:
        raise conflito(
            f"Saldo insuficiente: saldo R$ {carteira_comprador.saldo}, preço R$ {jogo.preco}"
        )

    instante = agora()
    carteira_comprador.saldo -= jogo.preco
    carteira_vendedor.saldo += jogo.preco
    carteira_comprador.atualizada_em = carteira_vendedor.atualizada_em = instante

    compra = Compra(
        comprador_id=comprador.id,
        vendedor_id=jogo.vendedor_id,
        jogo_id=jogo.id,
        valor_pago=jogo.preco,
        realizada_em=instante,
    )
    session.add_all(
        [
            carteira_comprador,
            carteira_vendedor,
            CarteiraJogo(carteira_id=carteira_comprador.id, jogo_id=jogo.id, adquirido_em=instante),
            compra,
        ]
    )
    session.commit()
    session.refresh(compra)
    return compra
