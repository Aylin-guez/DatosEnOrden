from __future__ import annotations

import os
from urllib.parse import quote_plus


DEMO_INVESTIGATION_TARGET = "SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO"
DEMO_INVESTIGATION_URL = f"{os.getenv('DATOSENORDEN_PUBLIC_BASE_URL', 'https://datosenorden.cl').rstrip('/')}/investigation?id={quote_plus(DEMO_INVESTIGATION_TARGET)}"
