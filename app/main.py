from fastapi import FastAPI
from fastapi.responses import RedirectResponse

app = FastAPI(title="GameHub API")


@app.get("/", include_in_schema=False)
def raiz() -> RedirectResponse:
    return RedirectResponse(url="/docs")
