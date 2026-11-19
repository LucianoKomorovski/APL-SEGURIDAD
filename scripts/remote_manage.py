"""Administración remota explícita, sin reemplazar backend/.env ni SQLite."""
import os
from pathlib import Path
import sys

from dotenv import load_dotenv

root = Path(__file__).resolve().parent.parent
config = root / 'backend' / '.env.remote'
if not config.is_file():
    sys.exit('Creá backend/.env.remote con las variables de Render; no lo subas a Git.')
load_dotenv(config, override=True)
if os.getenv('DJANGO_DEBUG', '').lower() != 'false' or not os.getenv('DATABASE_URL', '').startswith(('postgres://', 'postgresql://')):
    sys.exit('El archivo remoto debe indicar DJANGO_DEBUG=false y DATABASE_URL PostgreSQL.')
sys.path.insert(0, str(root / 'backend'))
os.environ['DJANGO_SETTINGS_MODULE'] = 'sgca_backend.settings'
from django.core.management import execute_from_command_line
execute_from_command_line(sys.argv)
