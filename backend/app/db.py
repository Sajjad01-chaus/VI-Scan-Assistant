import json
import time
from pathlib import Path
from sqlalchemy import create_engine, event, String, Text, Integer, Float, ForeignKey, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from .config import ROOT, settings

(ROOT / 'data').mkdir(exist_ok=True)
class Base(DeclarativeBase):
    pass

class Patient(Base):
    __tablename__ = 'patients'
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, index=True)
    reference: Mapped[str] = mapped_column(String)

class Report(Base):
    __tablename__ = 'reports'
    id: Mapped[str] = mapped_column(String, primary_key=True)
    patient_id: Mapped[str] = mapped_column(ForeignKey('patients.id'), index=True)
    modality: Mapped[str] = mapped_column(String)
    performed_at: Mapped[str] = mapped_column(String)
    version: Mapped[int] = mapped_column(Integer, default=1)
    content: Mapped[str] = mapped_column(Text)

class Conversation(Base):
    __tablename__ = 'sessions'
    id: Mapped[str] = mapped_column(String, primary_key=True)
    owner_hash: Mapped[str] = mapped_column(String)
    selected_patient_id: Mapped[str | None] = mapped_column(ForeignKey('patients.id'), nullable=True)
    selected_report_id: Mapped[str | None] = mapped_column(ForeignKey('reports.id'), nullable=True)
    context_version: Mapped[int] = mapped_column(Integer, default=0)
    pending_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[float] = mapped_column(Float, default=lambda: time.time()+86400)

class Turn(Base):
    __tablename__ = 'turns'
    __table_args__ = (UniqueConstraint('session_id', 'utterance_id'),)
    id: Mapped[str] = mapped_column(String, primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey('sessions.id'))
    utterance_id: Mapped[str] = mapped_column(String)
    request_json: Mapped[str] = mapped_column(Text, default='{}')
    created_at: Mapped[float] = mapped_column(Float, default=time.time)
    response_json: Mapped[str | None] = mapped_column(Text, nullable=True)

class Draft(Base):
    __tablename__ = 'drafts'
    id: Mapped[str] = mapped_column(String, primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey('sessions.id'))
    patient_id: Mapped[str | None] = mapped_column(ForeignKey('patients.id'), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String, default='preview')
    body_json: Mapped[str] = mapped_column(Text)

class DraftRevision(Base):
    __tablename__ = 'draft_revisions'
    __table_args__ = (UniqueConstraint('draft_id', 'version'),)
    id: Mapped[str] = mapped_column(String, primary_key=True)
    draft_id: Mapped[str] = mapped_column(ForeignKey('drafts.id'))
    version: Mapped[int] = mapped_column(Integer)
    body_json: Mapped[str] = mapped_column(Text)

class AuditEvent(Base):
    __tablename__ = 'audit_events'
    id: Mapped[str] = mapped_column(String, primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey('sessions.id'))
    event_type: Mapped[str] = mapped_column(String)
    created_at: Mapped[float] = mapped_column(Float, default=time.time)
    metadata_json: Mapped[str] = mapped_column(Text, default='{}')

def make_engine(url):
    engine = create_engine(url, connect_args={'check_same_thread': False, 'timeout': 10} if url.startswith('sqlite') else {})
    if url.startswith('sqlite'):
        @event.listens_for(engine, 'connect')
        def configure(connection, _):
            connection.execute('PRAGMA foreign_keys=ON')
            connection.execute('PRAGMA busy_timeout=10000')
            connection.execute('PRAGMA journal_mode=WAL')
    return engine

engine = make_engine(settings.database_url)
Session = sessionmaker(engine, expire_on_commit=False)

def seed(engine_override=None):
    target = engine_override or engine
    factory = sessionmaker(target)
    data = json.loads((ROOT / 'data' / 'synthetic.json').read_text())
    legacy_path = ROOT / 'data' / 'synthetic-v1.json'
    legacy = {r['id']: r for r in json.loads(legacy_path.read_text())['reports']} if legacy_path.exists() else {}
    with factory.begin() as db:
        for p in data['patients']:
            if not db.get(Patient, p['id']):
                db.add(Patient(**p))
        db.flush()
        for r in data['reports']:
            existing = db.get(Report, r['id'])
            if not existing:
                db.add(Report(**r))
            elif existing.version < r['version'] and existing.content == legacy.get(r['id'], {}).get('content'):
                existing.content = r['content']
                existing.version = r['version']
