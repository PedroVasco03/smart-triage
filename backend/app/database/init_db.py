"""Cria as tabelas (se AUTO_CREATE_TABLES) e semeia a configuração inicial e os recursos.

Uso:  python -m app.database.init_db
"""
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app import models  # noqa: F401  (regista os modelos no metadata)
from app.database.base import Base
from app.database.session import SessionLocal, engine

DEFAULT_RESOURCES = [("Médico", 3), ("Cama", 5), ("Oxigénio", 2)]


def seed(db: Session) -> None:
    from app.models.resource import Resource
    from app.services.config_service import ConfigService

    ConfigService(db).get_active()  # cria a versão 1 se não existir
    existing = {r.resource_name for r in db.query(Resource).all()}
    for name, qty in DEFAULT_RESOURCES:
        if name not in existing:
            db.add(Resource(resource_name=name, quantity_available=qty, quantity_in_use=0))
    db.commit()


def ensure_columns(eng=engine) -> list[str]:
    """create_all não altera tabelas já existentes: acrescenta colunas novas a bases criadas por versões anteriores."""
    added: list[str] = []
    insp = inspect(eng)
    if "patients" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("patients")}
        if "service_minutes" not in cols:
            with eng.begin() as conn:
                conn.execute(text("ALTER TABLE patients ADD COLUMN service_minutes FLOAT NULL"))
            added.append("patients.service_minutes")
    return added


def init_db(create_tables: bool = True) -> None:
    if create_tables:
        Base.metadata.create_all(bind=engine)
        ensure_columns(engine)
    with SessionLocal() as db:
        seed(db)


if __name__ == "__main__":
    init_db()
    print("Base de dados inicializada.")
