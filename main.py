from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from prophet import Prophet
from sqlalchemy import create_engine
from bi_inventario import calcular_inventario_bi

app = FastAPI()

# Permitir solicitudes desde Laravel
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Para producción cambia esto por tu dominio Laravel
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Conexión a tu base de datos PostgreSQL
DB_URL = "postgresql://postgres:password@localhost:5432/veterinaria"
engine = create_engine(DB_URL)

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
