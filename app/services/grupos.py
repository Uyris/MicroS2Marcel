"""Regras de negócio dos grupos de compartilhamento."""

from sqlmodel import Session, func, select

from app.comum import buscar_ou_404, conflito
from app.models.grupo import Grupo, GrupoMembro
from app.models.usuario import Usuario

MAX_MEMBROS_POR_GRUPO = 5


def adicionar_membro(session: Session, grupo_id: int, usuario_id: int) -> GrupoMembro:
    """Adiciona um usuário ao grupo, respeitando o limite de membros."""
    # Trava a linha do grupo até o commit: duas entradas simultâneas não estouram o limite
    buscar_ou_404(session, Grupo, grupo_id, "Grupo não encontrado", travar=True)
    usuario = buscar_ou_404(session, Usuario, usuario_id, "Usuário não encontrado")

    if not usuario.ativo:
        raise conflito("Usuário desativado não pode entrar em grupos")
    # GrupoMembro tem chave composta, por isso o get recebe a tupla (grupo_id, usuario_id)
    if session.get(GrupoMembro, (grupo_id, usuario_id)) is not None:
        raise conflito("O usuário já é membro deste grupo")
    # equivale a SELECT COUNT(*) FROM grupo_membro WHERE grupo_id = ...
    total_membros = session.exec(
        select(func.count()).select_from(GrupoMembro).where(GrupoMembro.grupo_id == grupo_id)
    ).one()
    if total_membros >= MAX_MEMBROS_POR_GRUPO:
        raise conflito(f"O grupo já atingiu o limite de {MAX_MEMBROS_POR_GRUPO} membros")

    membro = GrupoMembro(grupo_id=grupo_id, usuario_id=usuario_id)
    session.add(membro)
    session.commit()
    return membro
