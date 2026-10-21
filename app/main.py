from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from app.routers import carteiras, compras, grupos, jogos, usuarios

DESCRICAO = """
API de uma **plataforma de venda de jogos digitais**.

* **Usuários** compram e vendem jogos. Ao se cadastrar, cada usuário recebe uma **carteira**.
* A **carteira** guarda o saldo (em reais) e os jogos que o usuário possui.
* O **catálogo** reúne os jogos à venda, cada um cadastrado por um usuário vendedor.
* Uma **compra** debita o comprador, credita o vendedor e coloca o jogo na carteira,
  tudo em uma única transação. Cada compra fica registrada em um **log** imutável.
* **Grupos** de até 5 usuários compartilham os jogos das carteiras de todos os membros.

Valores em reais são enviados e retornados como texto decimal (ex.: `"59.90"`) para não perder
precisão. Datas e horas seguem o formato ISO 8601, em UTC.
"""

TAGS = [
    {"name": "Usuários", "description": "Cadastro de compradores e vendedores."},
    {"name": "Carteira", "description": "Saldo e jogos de cada usuário."},
    {"name": "Catálogo de jogos", "description": "Jogos cadastrados pelos vendedores."},
    {"name": "Compras", "description": "Compra de jogos e log de compras."},
    {"name": "Grupos", "description": "Grupos de até 5 usuários que compartilham jogos."},
]


app = FastAPI(
    title="GameHub API",
    summary="Plataforma de compra, venda e compartilhamento de jogos",
    description=DESCRICAO,
    version="1.0.0",
    openapi_tags=TAGS,
)

app.include_router(usuarios.router)
app.include_router(carteiras.router)
app.include_router(jogos.router)
app.include_router(compras.router)
app.include_router(grupos.router)


@app.get("/", include_in_schema=False)
def raiz() -> RedirectResponse:
    return RedirectResponse(url="/docs")
