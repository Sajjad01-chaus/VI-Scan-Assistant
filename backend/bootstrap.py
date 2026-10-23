"""Migrate and seed fixtures; upgrade only unchanged, archived demo reports."""
from alembic import command
from alembic.config import Config
from backend.app.config import ROOT
from backend.app.db import seed

if __name__=='__main__':
    cfg=Config(str(ROOT/'alembic.ini'))
    command.upgrade(cfg,'head')
    seed()
    print('Database migrated and synthetic dataset seeded.')
