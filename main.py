from fastapi import FastAPI, Query
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from prophet import Prophet
from sqlalchemy import create_engine
from bi.bi_inventario import calcular_inventario_bi
import os
from dotenv import load_dotenv
from typing import Dict, List, Any
from routers import rotacion, proveedores
from tqdm import tqdm  # opcional para debug
import warnings
warnings.filterwarnings("ignore")

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

# Conexión base de datos PostgreSQL usando variables de entorno
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
def obtener_predicciones(producto_id: int = Query(..., description="ID del producto")) -> Dict[str, Any]:
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
        return {"message": "No hay datos de ventas para este producto"}

    # Asegurar formato adecuado
    df['ds'] = pd.to_datetime(df['ds'])
    df['y'] = df['y'].astype(float)

    # Entrenar modelo
    model = Prophet()
    model.fit(df)

    # Horizontes a predecir
    periodos = {
        "mensual": 30,
        "trimestral": 90,
        "semestral": 180,
        "anual": 365
    }

    resultado = {}

    for nombre, dias in periodos.items():
        future = model.make_future_dataframe(periods=dias)
        forecast = model.predict(future)

        # Solo nos interesa el futuro
        pred = forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]].tail(dias).copy()
        pred["ds"] = pred["ds"].dt.strftime('%Y-%m-%d')
        resultado[nombre] = pred.to_dict(orient="records")

    return JSONResponse(content=resultado)

@app.get("/api/bi/inventario")
def obtener_bi_inventario():
    resultado = calcular_inventario_bi()
    return resultado

@app.get("/api/recomendaciones/compras")
def recomendar_compra_por_producto(producto_id: int):
    # Obtener inventario
    inventario = calcular_inventario_bi()
    producto_data = next((p for p in inventario if p["producto_id"] == producto_id), None)

    if not producto_data:
        raise HTTPException(status_code=404, detail="Producto no encontrado en el inventario")

    stock_actual = producto_data.get("stock", 0)

    # Obtener ventas históricas
    query = f"""
    SELECT nv.fecha::date AS ds, SUM(dv.cantidad) AS y
    FROM detalle_ventas dv
    JOIN nota_ventas nv ON dv.nota_venta_id = nv.id
    WHERE dv.producto_id = {producto_id}
    GROUP BY ds
    ORDER BY ds
    """
    df = pd.read_sql(query, engine)

    if df.empty or df["y"].sum() < 10:
        return {"message": "No hay suficiente historial para generar recomendaciones"}

    # Predecir demanda
    model = Prophet()
    model.fit(df)
    future = model.make_future_dataframe(periods=30)
    forecast = model.predict(future)
    demanda_30 = forecast[["ds", "yhat"]].tail(30)["yhat"].sum()

    compra_sugerida = max(0, round(demanda_30 - stock_actual))

    return {
        "producto_id": producto_id,
        "stock_actual": stock_actual,
        "demanda_30_dias": round(demanda_30),
        "compra_sugerida": compra_sugerida
    }

@app.get("/api/pricing/sugerencias")
def sugerencias_precio():
    # Productos con stock
    productos = pd.read_sql('SELECT id, nombre, stock FROM productos', engine)

    ventas = pd.read_sql("""
        SELECT producto_id, cantidad, precio_venta, created_at
        FROM detalle_ventas
    """, engine)

    if ventas.empty:
        raise HTTPException(status_code=404, detail="No hay datos de ventas disponibles")
    
    precio_promedio = ventas.groupby('producto_id')['precio_venta'].mean()
    ventas_sorted = ventas.sort_values(by=['producto_id', 'created_at'])
    precio_actual = ventas_sorted.groupby('producto_id').last()['precio_venta']

    total_vendido = ventas.groupby('producto_id')['cantidad'].sum()

    productos = productos.merge(precio_promedio.rename('precio_promedio_venta'), left_on='id', right_index=True, how='left')
    productos = productos.merge(precio_actual.rename('precio_actual'), left_on='id', right_index=True, how='left')
    productos = productos.merge(total_vendido.rename('total_vendido'), left_on='id', right_index=True, how='left')
    productos = productos.fillna({'precio_promedio_venta': 0, 'precio_actual': 0, 'total_vendido': 0})

    sugerencias = []

    for _, row in productos.iterrows():
        vendidos = row['total_vendido']
        stock = row['stock']
        actual = row['precio_actual']
        promedio = row['precio_promedio_venta']
        sugerido = actual
        razon = None

        if vendidos >= 50 and stock < 10:
            sugerido = round(actual * 1.10, 2)
            razon = "Subir precio por alta rotación y bajo stock"

        if stock > 30 and vendidos < 10:
            sugerido = round(actual * 0.90, 2)
            razon = "Bajar precio por sobrestock y baja venta"

        if abs(actual - promedio) > 2:
            sugerido = round(promedio, 2)
            razon = "Ajustar al promedio de ventas"

        if razon is None:
            razon = "Precio actual es razonable"
            sugerido = round(actual, 2)

        sugerencias.append({
            "producto_id": int(row["id"]),
            "nombre": row["nombre"],
            "stock": int(stock),
            "vendidos": int(vendidos),
            "precio_actual": round(actual, 2),
            "precio_promedio_venta": round(promedio, 2),
            "precio_sugerido": round(sugerido, 2),
            "sugerencia": razon
        })

    return {
        "total": len(sugerencias),
        "sugerencias": sugerencias
    }

app.include_router(rotacion.router)

app.include_router(proveedores.router)