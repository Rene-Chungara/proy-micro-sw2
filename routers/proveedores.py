from fastapi import APIRouter
from services.proveedor_model import clasificar_proveedores

router = APIRouter()

@router.get("/api/clasificacion-proveedores")
def proveedores():
    return clasificar_proveedores()
