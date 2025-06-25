# bi_inventario.py

import pandas as pd
from sqlalchemy import create_engine

DB_USER = 'postgres'
DB_PASS = 'password'
DB_HOST = 'localhost'
DB_PORT = '5432'
DB_NAME = 'veterinaria'

engine = create_engine(f'postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}')

def calcular_inventario_bi():
    productos = pd.read_sql('SELECT id, nombre, stock FROM productos', engine)
    ventas = pd.read_sql('SELECT producto_id, cantidad FROM detalle_ventas', engine)
    entradas = pd.read_sql('SELECT producto_id, cantidad FROM detalle_nota_entradas', engine)

    # Demanda anual
    demanda = ventas.groupby('producto_id')['cantidad'].sum() * 2
    productos = productos.merge(demanda.rename('demanda_anual'), left_on='id', right_index=True, how='left').fillna(0)

    productos['costo_pedido'] = 50
    productos['costo_mant'] = 10
    productos['tiempo_reposicion'] = 7

    productos['eoq'] = ((2 * productos['demanda_anual'] * productos['costo_pedido']) / productos['costo_mant']).pow(0.5)
    productos['rop'] = (productos['demanda_anual'] / 365) * productos['tiempo_reposicion']

    ventas_abc = ventas.groupby('producto_id')['cantidad'].sum().sort_values(ascending=False)
    abc_cum = ventas_abc.cumsum() / ventas_abc.sum()
    clasificacion = abc_cum.apply(lambda x: 'A' if x <= 0.8 else ('B' if x <= 0.95 else 'C'))
    productos = productos.merge(clasificacion.rename('clasificacion_abc'), left_on='id', right_index=True, how='left').fillna('C')

    resultado = productos[['id', 'nombre', 'stock', 'eoq', 'rop', 'clasificacion_abc']]
    return resultado.to_dict(orient='records')
