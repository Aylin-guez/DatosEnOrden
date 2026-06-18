CHILECOMPRA_API_DOC_URL = "https://www.chilecompra.cl/api/"
MERCADO_PUBLICO_BASE_URL = "https://www.mercadopublico.cl"

LICITACION_DETAIL_URL = (
    "https://www.mercadopublico.cl/Procurement/Modules/RFB/DetailsAcquisition.aspx?idlicitacion={code}"
)
ORDEN_COMPRA_DETAIL_URL = (
    "https://www.mercadopublico.cl/PurchaseOrder/Modules/PO/DetailsPurchaseOrder.aspx?qs={code}"
)

LICITACION_STATUS = {
    "5": "Publicada",
    "6": "Cerrada",
    "7": "Desierta",
    "8": "Adjudicada",
    "18": "Revocada",
    "19": "Suspendida",
}

ORDEN_COMPRA_STATUS = {
    "4": "Enviada a proveedor",
    "5": "En proceso",
    "6": "Aceptada",
    "9": "Cancelada",
    "12": "Recepcion conforme",
    "13": "Pendiente de recepcionar",
    "14": "Recepcionada parcialmente",
    "15": "Recepcion conforme incompleta",
}
