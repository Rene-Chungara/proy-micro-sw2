from fastapi import APIRouter
from services.rotacion_model import segmentar_productos

router = APIRouter()

@router.get("/api/segmentacion-productos")
def rotacion():
    return segmentar_productos()
