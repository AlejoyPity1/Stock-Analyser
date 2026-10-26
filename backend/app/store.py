import json
from datetime import datetime, timezone
from sqlalchemy import create_engine, String, Text, Integer, Float, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from .config import settings

def now():
    return datetime.now(timezone.utc).isoformat()

class Base(DeclarativeBase): pass

class Record(Base):
    __tablename__ = 'records'
    id: Mapped[str] = mapped_column(String, primary_key=True)
    kind: Mapped[str] = mapped_column(String, index=True)
    symbol: Mapped[str] = mapped_column(String, index=True)
    created_at: Mapped[str] = mapped_column(String, default=now)
    payload: Mapped[str] = mapped_column(Text)

class Cache(Base):
    __tablename__ = 'http_cache'
    key: Mapped[str] = mapped_column(String, primary_key=True)
    expires: Mapped[float] = mapped_column(Float)
    payload: Mapped[str] = mapped_column(Text)

class Migration(Base):
    __tablename__ = 'schema_version'
    version: Mapped[int] = mapped_column(Integer, primary_key=True)

engine = create_engine(settings.database_url, connect_args={'check_same_thread': False} if settings.database_url.startswith('sqlite') else {})
Session = sessionmaker(engine)

def initialize(recover_jobs=False):
    Base.metadata.create_all(engine)
    with Session() as s:
        if not s.get(Migration, 1):
            s.add(Migration(version=1)); s.commit()
        # A process cannot resume an in-memory coroutine. Never leave a false running state.
        for row in s.scalars(select(Record).where(Record.kind == 'research')):
            p = json.loads(row.payload)
            if recover_jobs and p.get('status') in ('queued', 'running'):
                p.update(status='interrupted', error='El servidor se reinició; vuelve a iniciar la investigación.')
                row.payload = json.dumps(p)
        s.commit()

def put(id, kind, symbol, payload):
    with Session() as s:
        row = s.get(Record, id)
        if row: row.payload = json.dumps(payload, allow_nan=False)
        else: s.add(Record(id=id, kind=kind, symbol=symbol, payload=json.dumps(payload, allow_nan=False)))
        s.commit()

def get(id):
    with Session() as s:
        r = s.get(Record, id)
        return json.loads(r.payload) if r else None

def records(kind, symbol=None, limit=100):
    with Session() as s:
        q = select(Record).where(Record.kind == kind)
        if symbol: q = q.where(Record.symbol == symbol)
        return [{'id':r.id,'symbol':r.symbol,'created_at':r.created_at,'data':json.loads(r.payload)} for r in s.scalars(q.order_by(Record.created_at.desc()).limit(limit))]

def delete(id):
    with Session() as s:
        row=s.get(Record,id)
        if row: s.delete(row); s.commit()
