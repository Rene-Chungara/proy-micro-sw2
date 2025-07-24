from sqlalchemy import create_engine
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from services.database import engine

def segmentar_productos():
    productos = pd.read_sql("SELECT id, nombre, stock FROM productos", engine)

    ventas = pd.read_sql("""
        SELECT dv.producto_id, dv.cantidad, nv.fecha
        FROM detalle_ventas dv
        JOIN nota_ventas nv ON dv.nota_venta_id = nv.id
    """, engine)

    if ventas.empty:
        return []

    ventas["fecha"] = pd.to_datetime(ventas["fecha"])
    total_vendido = ventas.groupby("producto_id")["cantidad"].sum()
    dias_medios = ventas.sort_values("fecha").groupby("producto_id")["fecha"].apply(lambda x: x.diff().dt.days.dropna().mean()).fillna(999)

    productos = productos.merge(total_vendido.rename("total_vendido"), left_on="id", right_index=True, how="left")
    productos = productos.merge(dias_medios.rename("dias_entre_ventas"), left_on="id", right_index=True, how="left")
    productos.fillna({"total_vendido": 0, "dias_entre_ventas": 999}, inplace=True)

    X = productos[["total_vendido", "dias_entre_ventas", "stock"]]
    X_scaled = StandardScaler().fit_transform(X)

    kmeans = KMeans(n_clusters=3, random_state=42)
    productos["cluster"] = kmeans.fit_predict(X_scaled)

    orden = productos.groupby("cluster")[["total_vendido", "dias_entre_ventas"]].mean().sort_values(["total_vendido", "dias_entre_ventas"], ascending=[False, True]).index.tolist()
    labels = {orden[0]: "Alta", orden[1]: "Media", orden[2]: "Baja"}
    productos["categoria_rotacion"] = productos["cluster"].map(labels)

    return productos[["id", "nombre", "total_vendido", "dias_entre_ventas", "stock", "categoria_rotacion"]].rename(columns={"id": "producto_id"}).to_dict(orient="records")
