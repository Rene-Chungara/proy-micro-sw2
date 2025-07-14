from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from prophet import Prophet
from sqlalchemy import create_engine
from bi.bi_inventario import calcular_inventario_bi
import os
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

print(f"DEBUG: La aplicación está esperando el puerto: {os.getenv('PORT')}")
app = FastAPI()

# Permitir solicitudes desde Laravel
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Para producción cambia esto por tu dominio
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Conexión a tu base de datos PostgreSQL usando variables de entorno
DB_USER = os.getenv('DB_USER')
DB_PASS = os.getenv('DB_PASS')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_NAME = os.getenv('DB_NAME')

DB_URL = f'postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
engine = create_engine(DB_URL)

@app.get("/")
def root():
    """Endpoint raíz para verificar que la API está funcionando"""
    return {
        "message": "¡API de Veterinaria funcionando correctamente! 🚀",
        "status": "activo",
        "version": "1.0.0",
        "endpoints": {
            "prediccion": "/api/prediccion?producto_id=1",
            "inventario_bi": "/api/bi/inventario",
            "documentacion": "/docs"
        }
    }

@app.get("/health")
def health_check():
    """Endpoint de verificación de salud de la API"""
    return {
        "status": "OK",
        "message": "API funcionando correctamente",
        "database": "conectada" if engine else "desconectada"
    }

@app.get("/api/prediccion")
def obtener_prediccion(producto_id: int = 1):
    query = f"""
    SELECT nv.fecha::date AS ds, SUM(dv.cantidad) AS y
    FROM detalle_ventas dv
    JOIN nota_ventas nv ON dv.nota_venta_id = nv.id
    WHERE dv.producto_id = {producto_id}
    GROUP BY ds
    ORDER BY ds
    """
    df = pd.read_sql(query, engine)

    if df.empty:
        return {"message": "No hay datos para este producto"}

    model = Prophet()
    model.fit(df)
    future = model.make_future_dataframe(periods=30)
    forecast = model.predict(future)

    resultado = forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]].tail(30).to_dict(orient="records")
    return resultado

@app.get("/api/bi/inventario")
def obtener_bi_inventario():
    resultado = calcular_inventario_bi()
    return resultado
