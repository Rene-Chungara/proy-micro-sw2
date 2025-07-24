from sqlalchemy import create_engine
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from services.database import engine

def clasificar_proveedores():
    # Cargar datos de proveedores y entradas
    proveedores = pd.read_sql("SELECT id, nombre FROM proveedors", engine)

    entradas = pd.read_sql("""
        SELECT id, proveedor_id, monto
        FROM nota_entradas
    """, engine)

    if entradas.empty:
        return []

    detalles = pd.read_sql("""
        SELECT nota_entrada_id, cantidad
        FROM detalle_nota_entradas
    """, engine)

    # Métricas por proveedor
    total_monto = entradas.groupby("proveedor_id")["monto"].sum()
    cantidad_entregas = entradas.groupby("proveedor_id")["id"].count()
    promedio_por_entrega = total_monto / cantidad_entregas

    merged = proveedores.copy()
    merged = merged.merge(total_monto.rename("monto_total"), left_on="id", right_index=True, how="left")
    merged = merged.merge(cantidad_entregas.rename("num_entregas"), left_on="id", right_index=True, how="left")
    merged = merged.merge(promedio_por_entrega.rename("monto_promedio"), left_on="id", right_index=True, how="left")

    merged.fillna(0, inplace=True)

    # Clustering
    X = merged[["monto_total", "num_entregas", "monto_promedio"]]
    X_scaled = StandardScaler().fit_transform(X)

    kmeans = KMeans(n_clusters=3, random_state=42)
    merged["cluster"] = kmeans.fit_predict(X_scaled)

    # Etiquetas de desempeño basadas en promedio
    orden = merged.groupby("cluster")[["monto_total", "num_entregas"]].mean().sort_values(
        ["monto_total", "num_entregas"], ascending=[False, False]
    ).index.tolist()

    etiquetas = {orden[0]: "Alto desempeño", orden[1]: "Desempeño medio", orden[2]: "Bajo desempeño"}
    merged["desempeno"] = merged["cluster"].map(etiquetas)

    return merged[["id", "nombre", "monto_total", "num_entregas", "monto_promedio", "desempeno"]].rename(
        columns={"id": "proveedor_id"}
    ).to_dict(orient="records")
