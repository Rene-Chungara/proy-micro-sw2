# bi/forecast_demanda.py
import pandas as pd
from prophet import Prophet
from sqlalchemy import create_engine
# Configura tu conexión
DB_USER = 'postgres'
DB_PASS = 'password'
DB_HOST = '3.95.222.41'
DB_PORT = '5432'
DB_NAME = 'veterinaria'

# Configura tu conexión a PostgreSQL
engine = create_engine(f'postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}')

# Reemplaza con el ID del producto que deseas analizar
PRODUCTO_ID = 1

# Cargar ventas agregadas por fecha para un producto específico
query = f"""
SELECT nv.fecha::date AS ds, SUM(dv.cantidad) AS y
FROM detalle_ventas dv
JOIN nota_ventas nv ON dv.nota_venta_id = nv.id
WHERE dv.producto_id = {PRODUCTO_ID}
GROUP BY ds
ORDER BY ds
"""

df = pd.read_sql(query, engine)

if df.empty:
    print("No hay ventas para ese producto.")
    exit()

# Crear y entrenar el modelo Prophet
model = Prophet(daily_seasonality=True)
model.fit(df)

# Crear el rango de fechas futuras (30 días)
future = model.make_future_dataframe(periods=30)
forecast = model.predict(future)

# Mostrar predicción
forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(10)

# Graficar
import matplotlib.pyplot as plt
fig = model.plot(forecast)
plt.title("Predicción de demanda (30 días)")
plt.xlabel("Fecha")
plt.ylabel("Unidades vendidas")
plt.show()
