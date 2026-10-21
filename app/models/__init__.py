from datetime import datetime, timezone


def agora() -> datetime:
    """Instante atual em UTC, valor padrão das colunas de data/hora."""
    return datetime.now(timezone.utc)
