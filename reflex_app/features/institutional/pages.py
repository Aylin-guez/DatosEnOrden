from __future__ import annotations

import reflex as rx

from reflex_app.components.common.cards import flow_card, help_card, support_action_card
from reflex_app.constants.public import (
    STUDIO_CONTACT_EMAIL,
    STUDIO_CONVERSATION_URL,
    SUPPORT_DONATION_URL,
    SUPPORT_SOURCE_SUGGESTION_URL,
)
from reflex_app.constants.demo import DEMO_INVESTIGATION_TARGET
from reflex_app.constants.routes import PAGE_PROJECT, PAGE_STUDIO, PAGE_SUPPORT
from reflex_app.helpers.routing import _investigation_href
from reflex_app.layouts.page import page_section
from reflex_app.metadata.pages import PUBLIC_OG_IMAGE_URL, _page_meta
from reflex_app.layouts.shell import shell


def support_cta_block() -> rx.Component:
    return rx.hstack(
        rx.link("Apoyar el lanzamiento", href=SUPPORT_DONATION_URL, class_name="button"),
        rx.link("Sugerir una fuente", href=SUPPORT_SOURCE_SUGGESTION_URL, class_name="button button-secondary"),
        rx.link("Conversar sobre Studio", href=f"mailto:{STUDIO_CONTACT_EMAIL}", class_name="button button-secondary"),
        spacing="3",
        wrap="wrap",
        class_name="hero-actions",
    )


@rx.page(
    route="/project",
    title="Estado del proyecto - DatosEnOrden",
    description="Estado público del proyecto DatosEnOrden, su propósito, alcance y límites.",
    image=PUBLIC_OG_IMAGE_URL,
    meta=_page_meta(
        "/project",
        "DatosEnOrden, proyecto, evidencia verificable, lectura pública, MVP",
        "Estado del proyecto - DatosEnOrden",
        "Por qué existe DatosEnOrden, cómo funciona y qué significa un MVP con evidencia verificable.",
    ),
)
def project() -> rx.Component:
    return shell(
        rx.box(
            rx.text("Acerca de DatosEnOrden Ciudadano", class_name="title"),
            rx.text(
                "DatosEnOrden existe para que la información pública se pueda leer como una historia verificable, no como un listado suelto de registros.",
                class_name="subtitle",
            ),
            rx.text("MVP con datos locales de prueba. No representa datos oficiales reales.", class_name="badge badge-purple launch-notice"),
            rx.hstack(
                rx.button("Volver al inicio", on_click=rx.redirect("/"), class_name="button"),
                rx.button("Abrir expediente de ejemplo", on_click=rx.redirect(_investigation_href(DEMO_INVESTIGATION_TARGET)), class_name="button button-secondary"),
                spacing="3",
                wrap="wrap",
                class_name="hero-actions",
            ),
            class_name="hero",
        ),
        page_section(
            "Qué es DatosEnOrden",
            rx.grid(
                help_card("Leer evidencia", "Tomar documentos, relaciones y cronologías y convertirlos en una lectura pública útil."),
                help_card("Conectar fuentes", "Cruzar compras, presupuesto, lobby, publicaciones, empresas y control en un mismo recorrido."),
                help_card("Mantener trazabilidad", "Cada afirmación visible debe poder volver a una referencia o fragmento concreto."),
                columns="3",
                spacing="3",
                class_name="responsive-grid",
            ),
            subtitle="La versión pública muestra el producto sin esconder sus límites ni prometer automatizaciones inexistentes.",
        ),
        page_section(
            "Por qué existe",
            rx.text(
                "El problema no es la falta de datos, sino que los datos suelen venir dispersos, con lenguaje técnico y sin una ruta clara para verificarlos.",
                class_name="story-summary",
            ),
            rx.text(
                "DatosEnOrden junta fuentes, evidencia y contexto para que una persona pueda entender qué pasó, dónde verlo y qué parte del texto lo sostiene.",
                class_name="story-summary",
            ),
            subtitle="El foco no es deslumbrar con volumen; es reducir fricción de lectura y hacer visible la procedencia.",
        ),
        page_section(
            "Cómo funciona",
            rx.grid(
                flow_card(1, "Fuentes", "Cada registro nace desde un origen identificable y marcado como local de prueba cuando corresponde."),
                flow_card(2, "Evidencia", "Fragmentos, documentos y anclas permiten volver a la parte exacta del contenido."),
                flow_card(3, "Relaciones", "EntityEngine, RelationshipGraph y StateGraph ordenan los cruces sin inventar conclusiones."),
                flow_card(4, "Lectura", "La interfaz traduce la trazabilidad técnica a una experiencia pública clara."),
                columns="4",
                spacing="3",
                class_name="responsive-grid",
            ),
            subtitle="La arquitectura existente se reutiliza; el valor está en la lectura y en la trazabilidad, no en cambiarla.",
        ),
        page_section(
            "Qué significa MVP",
            rx.grid(
                help_card("Más cobertura", "Seguir completando fuentes y aumentando la conectividad útil de los demos."),
                help_card("Mejor lectura", "Pulir búsquedas, documento, cronología y vistas de producto con menos fricción."),
                help_card("Publicación segura", "Mantener despliegue, backups y monitoreo simples para el primer lanzamiento público."),
                help_card("Studio", "Mostrar el uso para organizaciones sin vender humo ni prometer magia."),
                columns="2",
                spacing="3",
                class_name="responsive-grid",
            ),
            subtitle="El proyecto avanza por iteraciones pequeñas y visibles, con evidencia verificable antes que marketing.",
        ),
        page_section(
            "Cómo ayudar",
            rx.grid(
                help_card("Menos fricción", "Equipos no técnicos pueden revisar, compartir y seguir un caso sin fricción innecesaria."),
                help_card("Universidades", "Explorar investigación, convenios, fuentes públicas y evidencia institucional."),
                help_card("ONG", "Monitorear temas públicos con trazabilidad y lenguaje ciudadano."),
                help_card("Organismos públicos", "Centralizar evidencia pública y seguimiento documental."),
                columns="2",
                spacing="3",
                class_name="responsive-grid",
            ),
            subtitle="Pensado para quien necesita una lectura de trabajo, no una demo técnica.",
        ),
        page_section(
            "Límite actual",
            rx.text(
                "No hay afirmaciones automáticas, ni inferencias encubiertas, ni fuentes inventadas. Hay lectura verificable con demo local.",
                class_name="story-summary",
            ),
            rx.text(
                "DatosEnOrden Studio se encuentra en desarrollo activo. Algunas capacidades ya forman parte de la plataforma pública y otras se incorporarán progresivamente.",
                class_name="story-summary",
            ),
            subtitle="Eso es suficiente para un primer lanzamiento público y deja claro dónde termina la demo.",
        ),
        page_section(
            "Cómo seguir",
            rx.text(
                "Si encuentras una mejora obvia, reporta la ruta y el texto exacto: eso ayuda más que ideas vagas.",
                class_name="story-summary",
            ),
            subtitle="La iteración siguiente debe mejorar la lectura sin cambiar la arquitectura base.",
        ),
        active_page=PAGE_PROJECT,
    )


@rx.page(
    route="/studio",
    title="DatosEnOrden Studio",
    description="Entrada comercial para organizaciones que necesitan expedientes, fuentes y automatización documental verificable.",
    image=PUBLIC_OG_IMAGE_URL,
    meta=_page_meta(
        "/studio",
        "datosenorden studio, expedientes, fuentes oficiales, automatización documental, organizaciones",
        "DatosEnOrden Studio",
        "Entrada comercial para organizaciones que necesitan expedientes, fuentes y automatización documental verificable.",
    ),
)
def studio() -> rx.Component:
    return shell(
        rx.box(
            rx.text("DatosEnOrden Studio", class_name="title"),
            rx.text(
                "La plataforma para municipalidades, universidades y equipos que necesitan ordenar información pública con evidencia y contexto.",
                class_name="subtitle",
            ),
            rx.text(
                "Explora conectores, expedientes, cronologías y documentos para trabajar con una lectura trazable, no con hojas sueltas.",
                class_name="muted small",
            ),
            rx.hstack(
                rx.link("Solicitar una conversación", href=STUDIO_CONVERSATION_URL, class_name="button primary-action"),
                rx.link("Enviar correo", href=f"mailto:{STUDIO_CONTACT_EMAIL}", class_name="button button-secondary"),
                spacing="3",
                wrap="wrap",
                class_name="hero-actions",
            ),
            class_name="hero studio-hero",
        ),
        page_section(
            "Qué obtiene una organización",
            rx.grid(
                help_card("Visibilidad", "Una ruta única para leer compras, presupuestos, publicaciones y evidencia relacionada."),
                help_card("Contexto", "Las piezas dejan de vivir en pantallas separadas y pasan a un expediente entendible."),
                help_card("Trazabilidad", "Cada lectura puede volver a su documento o fragmento de origen."),
                help_card("Menos fricción", "Equipos no técnicos pueden revisar, compartir y seguir un caso sin fricción innecesaria."),
                columns="2",
                spacing="3",
                class_name="responsive-grid",
            ),
            subtitle="Pensado para quien necesita una lectura de trabajo, no una demo técnica.",
        ),
        page_section(
            "Casos de uso",
            rx.grid(
                help_card("Municipalidades", "Ordenar documentos, compras, actos administrativos y seguimiento local."),
                help_card("Universidades", "Explorar investigación, convenios, fuentes públicas y evidencia institucional."),
                help_card("ONG", "Monitorear temas publicos con trazabilidad y lenguaje ciudadano."),
                help_card("Empresas", "Comprender proveedores, licitaciones, publicaciones y contexto regulatorio."),
                help_card("Consultoras", "Preparar expedientes verificables para analisis y reportes."),
                help_card("Organismos publicos", "Centralizar evidencia publica y seguimiento documental."),
                columns="2",
                spacing="3",
                class_name="responsive-grid",
            ),
            subtitle="Casos orientativos para conversaciones iniciales; cada implementación se revisa con evidencia y límites claros.",
        ),
        page_section(
            "Flujo",
            rx.grid(
                flow_card(1, "Entrar", "La organización llega por un caso, una fuente o un documento ya conocido."),
                flow_card(2, "Relacionar", "La plataforma conecta entidades, eventos, evidencia y cronología."),
                flow_card(3, "Revisar", "Se abren fragmentos y documentos para validar el texto original."),
                flow_card(4, "Compartir", "La lectura se puede mover internamente sin perder el enlace estable."),
                columns="4",
                spacing="3",
                class_name="responsive-grid",
            ),
            subtitle="Un flujo simple reduce el costo de adopción y hace más fácil explicar valor interno.",
        ),
        page_section(
            "Estado actual",
            rx.text(
                "DatosEnOrden Studio se encuentra en desarrollo activo. Algunas capacidades ya forman parte de la plataforma pública y otras se incorporarán progresivamente.",
                class_name="story-summary",
            ),
            subtitle="La versión pública muestra el producto sin esconder límites ni prometer automatizaciones inexistentes.",
        ),
        active_page=PAGE_STUDIO,
    )


@rx.page(
    route="/support",
    title="Apoyar DatosEnOrden",
    description="Página pública de apoyo y colaboración para el lanzamiento de DatosEnOrden.",
    image=PUBLIC_OG_IMAGE_URL,
    meta=_page_meta(
        "/support",
        "apoyar datosenorden, colaboración, lanzamiento público, feedback",
        "Apoyar DatosEnOrden",
        "Página pública de apoyo y colaboración para el lanzamiento de DatosEnOrden.",
    ),
)
def support() -> rx.Component:
    return shell(
        rx.box(
            rx.text("Apoyar DatosEnOrden", class_name="title"),
            rx.text(
                "El apoyo se canaliza mediante enlaces externos mientras el lanzamiento público mantiene una operación simple.",
                class_name="subtitle",
            ),
            rx.text(
                "Las donaciones no compran influencia ni alteran la prioridad de fuentes; solo ayudan a sostener infraestructura y trabajo continuo.",
                class_name="muted small",
            ),
            rx.text("Evidencia primero.", class_name="muted small"),
            support_cta_block(),
            rx.grid(
                support_action_card("Apoyo", "La plataforma sigue abierta a feedback, correcciones y colaboración puntual.", "Abrir enlace de apoyo", SUPPORT_DONATION_URL),
                support_action_card("Sugerir fuente", "Si falta una fuente pública, deja el enlace y el motivo para revisarlo.", "Sugerir una fuente", SUPPORT_SOURCE_SUGGESTION_URL),
                columns="2",
                spacing="3",
                class_name="responsive-grid",
            ),
        ),
        active_page=PAGE_SUPPORT,
    )
