from __future__ import annotations


def get_discovery_cases() -> dict[str, object]:
    return {
        "cases": [
            {
                "id": "public_spending",
                "title": "¿En qué se gasta el presupuesto?",
                "description": "Explora cómo presupuesto y compras públicas pueden conectarse.",
                "concepts": ["Presupuesto", "Compra pública", "Organismo", "Proveedor"],
                "suggested_sources": ["DIPRES", "ChileCompra"],
                "example_query": "Servicio de Salud Arauco",
                "cta": "Explorar gasto público",
            },
            {
                "id": "state_suppliers",
                "title": "¿Qué empresas venden al Estado?",
                "description": "Revisa proveedores, órdenes de compra y organismos compradores.",
                "concepts": ["Proveedor", "Contrato", "Organismo"],
                "suggested_sources": ["ChileCompra", "Registro de Empresas"],
                "example_query": "proveedor",
                "cta": "Explorar proveedores",
            },
            {
                "id": "public_roles",
                "title": "¿Qué cargos públicos aparecen?",
                "description": "Conecta cargos, nombramientos y transparencia activa.",
                "concepts": ["Persona", "Cargo Público", "Nombramiento"],
                "suggested_sources": ["Diario Oficial", "Transparencia Activa", "SERVEL"],
                "example_query": "nombramientos",
                "cta": "Explorar cargos",
            },
            {
                "id": "meetings_and_authorities",
                "title": "¿Quién se reúne con quién?",
                "description": "Explora reuniones de lobby asociadas a organismos o autoridades.",
                "concepts": ["Reunión", "Persona", "Organismo"],
                "suggested_sources": ["Lobby", "Transparencia Activa"],
                "example_query": "reuniones de lobby",
                "cta": "Explorar reuniones",
            },
            {
                "id": "institution_profile",
                "title": "¿Cómo se conecta una institución?",
                "description": "Reúne presupuesto, compras, cargos, auditorías y publicaciones oficiales.",
                "concepts": ["Organismo", "Presupuesto", "Compra", "Auditoría", "Publicación oficial"],
                "suggested_sources": ["DIPRES", "ChileCompra", "Contraloría", "Diario Oficial"],
                "example_query": "Servicio de Salud Arauco",
                "cta": "Abrir perfil institucional",
            },
        ]
    }
