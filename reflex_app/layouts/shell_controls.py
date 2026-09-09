from __future__ import annotations

import reflex as rx


def scroll_top_control() -> rx.Component:
    scroll_to_document_top = """
    (() => {
      const owner = document.scrollingElement || document.documentElement;
      owner.scrollTo({ top: 0, behavior: 'smooth' });
    })()
    """
    return rx.box(
        rx.script(
            """
            (() => {
              const updateScrollTopButton = () => {
                const button = document.querySelector('[data-deo-scroll-top="true"]');
                if (!button) return;
                const scrollOwner = document.scrollingElement || document.documentElement;
                button.classList.toggle('scroll-top-visible', scrollOwner.scrollTop > window.innerHeight * 0.9);
              };
              if (!window.__deoScrollTopVisibilityReady) {
                window.__deoScrollTopVisibilityReady = true;
                window.addEventListener('scroll', updateScrollTopButton, { passive: true });
                window.addEventListener('resize', updateScrollTopButton);
              }
              requestAnimationFrame(updateScrollTopButton);
            })();
            """
        ),
        rx.box(
            rx.button(
                "Volver arriba",
                id="scroll-top-button",
                type="button",
                data_deo_scroll_top="true",
                on_click=rx.run_script(scroll_to_document_top),
                class_name="scroll-top-button",
            ),
            data_deo_scroll_top_owner="true",
        ),
    )
