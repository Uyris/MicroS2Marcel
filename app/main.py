from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from app.routers import carteiras, compras, jogos, usuarios

app = FastAPI(title="GameHub API")

app.include_router(usuarios.router)
app.include_router(carteiras.router)
app.include_router(jogos.router)
app.include_router(compras.router)


@app.get("/", include_in_schema=False)
def raiz() -> RedirectResponse:
    return RedirectResponse(url="/docs")
