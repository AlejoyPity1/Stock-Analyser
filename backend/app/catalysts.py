"""User-reviewed catalyst evidence and immutable revisions. No arbitrary URL fetching."""
from datetime import date
from typing import Literal
from uuid import uuid4
from threading import Lock

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

from .store import get, put, records, now

_write_lock = Lock()  # One backend worker; revisions from concurrent tabs serialize.


class CatalystRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    symbol: str = Field(pattern=r'^[A-Z][A-Z0-9.\-]{0,14}$')
    title: str = Field(min_length=5, max_length=200)
    category: Literal['earnings', 'guidance', 'product', 'regulatory', 'macro', 'other'] = 'other'
    event_date: date | None = None
    date_status: Literal['reported', 'estimated', 'unknown'] = 'unknown'
    status: Literal['planned', 'occurred', 'cancelled'] = 'planned'
    hypothesis: str = Field(min_length=30, max_length=4000)
    invalidation: str = Field(min_length=20, max_length=2000)
    source_url: HttpUrl | None = None
    evidence_quote: str = Field(default='', max_length=2000)
    research_id: str | None = Field(default=None, max_length=100)
    source_id: str | None = Field(default=None, max_length=200)
    previous_id: str | None = Field(default=None, max_length=100)

    @model_validator(mode='after')
    def evidence(self):
        if (self.event_date is None) != (self.date_status == 'unknown'):
            raise ValueError('Una fecha desconocida no lleva día; una fecha reportada o estimada sí')
        if self.date_status == 'reported' and len(self.evidence_quote) < 10:
            raise ValueError('Añade una cita que respalde la fecha reportada')
        if not self.source_url and not self.source_id:
            raise ValueError('Añade una referencia a la fuente')
        if self.source_url and (self.source_url.scheme != 'https' or self.source_url.username or self.source_url.password):
            raise ValueError('La referencia debe ser HTTPS y no incluir credenciales')
        if self.source_id and not self.research_id:
            raise ValueError('La fuente leída necesita su expediente de investigación')
        return self


def save_catalyst(request):
    with _write_lock:
        return _save_catalyst(request)


def _save_catalyst(request):
    source = None
    if request.research_id:
        job = get(request.research_id)
        if not job or job.get('symbol') != request.symbol:
            raise ValueError('Investigación no encontrada para esta empresa')
        if request.source_id:
            source = next((s for s in job.get('sources', []) if s['id'] == request.source_id), None)
            if not source or source.get('read_status') not in ('read', 'abstract_only'):
                raise ValueError('Fuente ajena al expediente o sin contenido accesible')
            content = source.get('text') or source.get('summary', '')
            if not request.evidence_quote or request.evidence_quote not in content:
                raise ValueError('La cita debe coincidir literalmente con el contenido recuperado')
            if request.source_url and str(request.source_url) != source['url']:
                raise ValueError('El enlace no coincide con la fuente del expediente')
    previous = get(request.previous_id) if request.previous_id else None
    if request.previous_id and (not previous or previous.get('record_type') != 'catalyst' or previous['symbol'] != request.symbol):
        raise ValueError('Versión previa de catalizador no encontrada para esta empresa')
    if previous:
        current=next((event for event in latest_catalysts(request.symbol) if event['event_id']==previous['event_id']),None)
        if current and current['id']!=previous['id']:
            raise ValueError('Hay una versión más reciente del catalizador; abre esa versión antes de editar')
    payload = request.model_dump(mode='json')
    payload.update(
        id=str(uuid4()), event_id=previous['event_id'] if previous else str(uuid4()),
        record_type='catalyst', created_at=now(),
        source_url=source['url'] if source else str(request.source_url),
        verification='literal_quote_matched' if source else 'external_reference_unverified',
        source_snapshot={key:source.get(key) for key in ('id','title','url','published_at','retrieved_at','read_status','content_hash')} if source else None,
        interpretation='Fecha y materialidad introducidas por el usuario. Una cita literal coincidente no verifica por sí sola su interpretación ni confirma un evento futuro.',
    )
    put(payload['id'], 'catalyst', request.symbol, payload)
    return payload


def latest_catalysts(symbol):
    found = {}
    for row in records('catalyst', symbol, limit=1000):
        value = row['data']
        found.setdefault(value['event_id'], value)
    return list(found.values())


def event_position(event, horizon):
    if event['status'] == 'cancelled':
        return 'cancelled'
    day = event.get('event_date')
    if not day:
        return 'undated'
    if day < horizon['as_of']:
        return 'past'
    if day <= horizon['window_end_date']:
        return 'within_horizon'
    return 'beyond_horizon'
