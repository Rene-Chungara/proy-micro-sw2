import pandas as pd
from sqlalchemy import create_engine

# Configura tu conexión
DB_USER = 'postgres'
DB_PASS = 'password'
DB_HOST = '3.95.222.41'
DB_PORT = '5432'
DB_NAME = 'veterinaria'

engine = create_engine(f'postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}')

def cargar_datos():
    productos = pd.read_sql('SELECT id, nombre, stock FROM productos', engine)
    ventas = pd.read_sql('SELECT producto_id, cantidad FROM detalle_ventas', engine)
    entradas = pd.read_sql('SELECT producto_id, cantidad FROM detalle_nota_entradas', engine)
    return productos, ventas, entradas

def calcular_bi(productos, ventas, entradas):
    # Demanda anual (anualiza ventas: por ejemplo, suponiendo datos de 6 meses)
    demanda = ventas.groupby('producto_id')['cantidad'].sum() * 2
    productos = productos.merge(demanda.rename('demanda_anual'), left_on='id', right_index=True, how='left').fillna(0)

    # Parámetros BI básicos (ajusta según tu contexto)
    productos['costo_pedido'] = 50  # ficticio
    productos['costo_mant'] = 10    # ficticio
    productos['tiempo_reposicion'] = 7  # ficticio, días

    # EOQ
    productos['eoq'] = ((2 * productos['demanda_anual'] * productos['costo_pedido']) / productos['costo_mant']).pow(0.5)

    # ROP
    productos['rop'] = (productos['demanda_anual'] / 365) * productos['tiempo_reposicion']

    # ABC (por cantidad vendida)
    ventas_abc = ventas.groupby('producto_id')['cantidad'].sum().sort_values(ascending=False)
    abc_cum = ventas_abc.cumsum() / ventas_abc.sum()
    clasificacion = abc_cum.apply(lambda x: 'A' if x <= 0.8 else ('B' if x <= 0.95 else 'C'))
    productos = productos.merge(clasificacion.rename('clasificacion_abc'), left_on='id', right_index=True, how='left').fillna('C')

    return productos

def guardar_resultados(productos):
    resultado = productos[['id', 'eoq', 'rop', 'clasificacion_abc']]
    resultado = resultado.rename(columns={'id': 'producto_id'})
    resultado.to_sql('bi_resultados', engine, if_exists='replace', index=False)
    print("Resultados BI guardados correctamente.")

if __name__ == "__main__":
    productos, ventas, entradas = cargar_datos()
    productos_bi = calcular_bi(productos, ventas, entradas)
    guardar_resultados(productos_bi)