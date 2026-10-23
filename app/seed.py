"""Popula o banco com dados de exemplo. Uso: python -m app.seed

As tabelas precisam existir (sql/criar_tabelas.sql). Só insere dados com o banco vazio.
"""

from datetime import date
from decimal import Decimal

from sqlmodel import Session, select

from app.database import engine
from app.models.carteira import Carteira
from app.models.compra import CompraBase
from app.models.grupo import Grupo, GrupoMembro
from app.models.jogo import Genero, Jogo
from app.models.usuario import Usuario
from app.services.compras import realizar_compra
from app.services.grupos import adicionar_membro

USUARIOS = [
    # (nome, e-mail, saldo inicial)
    ("Pixel Forge Studios", "contato@pixelforge.dev", "0"),
    ("Lua Games", "contato@luagames.com.br", "0"),
    ("Ana Souza", "ana.souza@email.com", "200.00"),
    ("Bruno Lima", "bruno.lima@email.com", "150.00"),
    ("Carla Mendes", "carla.mendes@email.com", "100.00"),
    ("Diego Rocha", "diego.rocha@email.com", "80.00"),
    ("Eva Martins", "eva.martins@email.com", "50.00"),
    ("Felipe Costa", "felipe.costa@email.com", "120.00"),
]

JOGOS = [
    # (título, gênero, preço, lançamento, classificação, e-mail do vendedor)
    ("Crônicas de Aurora", Genero.rpg, "89.90", date(2025, 11, 20), 12, "contato@pixelforge.dev"),
    ("Neon Drift", Genero.corrida, "49.90", date(2024, 3, 8), 0, "contato@pixelforge.dev"),
    ("Abismo Silencioso", Genero.terror, "39.90", date(2023, 10, 31), 16, "contato@luagames.com.br"),
    ("Reinos em Guerra", Genero.estrategia, "69.90", date(2025, 6, 2), 12, "contato@luagames.com.br"),
    ("Cubos Quânticos", Genero.puzzle, "19.90", date(2022, 1, 15), 0, "contato@luagames.com.br"),
    ("Arena Lendária", Genero.luta, "59.90", date(2026, 2, 10), 14, "contato@pixelforge.dev"),
]

COMPRAS = [
    # (e-mail do comprador, título do jogo)
    ("ana.souza@email.com", "Crônicas de Aurora"),
    ("ana.souza@email.com", "Neon Drift"),
    ("bruno.lima@email.com", "Reinos em Guerra"),
    ("bruno.lima@email.com", "Cubos Quânticos"),
    ("carla.mendes@email.com", "Abismo Silencioso"),
    ("diego.rocha@email.com", "Arena Lendária"),
    ("felipe.costa@email.com", "Crônicas de Aurora"),
]


def popular(session: Session) -> None:
    usuarios: dict[str, Usuario] = {}
    for nome, email, saldo in USUARIOS:
        usuario = Usuario(nome=nome, email=email)
        session.add(usuario)
        session.flush()  # gera o id do usuário para criar a carteira dele
        session.add(Carteira(usuario_id=usuario.id, saldo=Decimal(saldo)))
        usuarios[email] = usuario

    jogos: dict[str, Jogo] = {}
    for titulo, genero, preco, lancamento, classificacao, vendedor in JOGOS:
        jogo = Jogo(
            titulo=titulo,
            genero=genero,
            preco=Decimal(preco),
            data_lancamento=lancamento,
            classificacao_etaria=classificacao,
            vendedor_id=usuarios[vendedor].id,
        )
        session.add(jogo)
        jogos[titulo] = jogo
    session.commit()

    # As compras passam pela mesma regra da API: debitam, creditam e entram no log
    for comprador, titulo in COMPRAS:
        realizar_compra(
            session, CompraBase(comprador_id=usuarios[comprador].id, jogo_id=jogos[titulo].id)
        )

    # Grupo cheio (5 membros): bom para demonstrar o limite tentando adicionar o Felipe
    familia = Grupo(nome="Família Souza", descricao="Biblioteca compartilhada da família",
                    dono_id=usuarios["ana.souza@email.com"].id)
    session.add(familia)
    session.flush()  # gera o id do grupo para registrar o dono como membro
    session.add(GrupoMembro(grupo_id=familia.id, usuario_id=familia.dono_id))
    session.commit()
    # Os outros membros entram pela mesma regra da API (que respeita o limite de 5)
    for email in ("bruno.lima@email.com", "carla.mendes@email.com",
                  "diego.rocha@email.com", "eva.martins@email.com"):
        adicionar_membro(session, familia.id, usuarios[email].id)


def main() -> None:
    with Session(engine) as session:
        if session.exec(select(Usuario.id)).first() is not None:
            print("O banco já possui dados; nada foi inserido.")
            return
        popular(session)
    print(f"Dados de exemplo inseridos: {len(USUARIOS)} usuários, {len(JOGOS)} jogos, "
          f"{len(COMPRAS)} compras e 1 grupo com 5 membros.")


if __name__ == "__main__":
    main()
