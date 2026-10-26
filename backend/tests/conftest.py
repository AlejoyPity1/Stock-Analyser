import os
import tempfile
test_database_path = tempfile.mktemp(prefix='stock-test-',suffix='.db')
os.environ['DATABASE_URL']='sqlite:///'+test_database_path
os.environ['APP_ENVIRONMENT']='development'
os.environ['APP_TOKEN']=''
import pytest
from fastapi.testclient import TestClient
from app.main import app, _hits
from app.config import settings
from app.store import Session, Record, Cache, engine

@pytest.fixture
def client(monkeypatch):
    assert engine.url.database == test_database_path, 'Refuse to initialize or clear any non-test database'
    _hits.clear()
    monkeypatch.setattr(settings,'ai_provider','disabled')
    monkeypatch.setattr(settings,'paid_ai_enabled',False)
    monkeypatch.setattr(settings,'local_ai_api_key','')
    monkeypatch.setattr(settings,'sec_user_agent','')
    monkeypatch.setattr(settings,'finnhub_api_key','')
    monkeypatch.setattr(settings,'research_api_key','')
    monkeypatch.setattr(settings,'alphavantage_api_key','')
    with TestClient(app) as c:
        # Every test owns its controlled data; test ordering must not affect results.
        # DATABASE_URL above points only at this temporary test database.
        with Session() as session:
            session.query(Record).delete()
            session.query(Cache).delete()
            session.commit()
        yield c
