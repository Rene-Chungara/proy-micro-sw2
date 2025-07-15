# services/database.py
import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

# Cargar variables del archivo .env
load_dotenv()

DB_USER = os.getenv('DB_USER')
DB_PASS = os.getenv('DB_PASS')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_NAME = os.getenv('DB_NAME')

DB_URL = f'postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}?client_encoding=utf8'
engine = create_engine(DB_URL)
