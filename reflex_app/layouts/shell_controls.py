from __future__ import annotations

import reflex as rx


def scroll_top_control() -> rx.Component:
    return rx.box(
        rx.script(
            """
            (() => {
              if (window.__deoScrollTopReady) return;
              window.__deoScrollTopReady = true;
              const updateScrollTopButton = () => {
                const button = document.getElementById('scroll-top-button');
                if (!button) return;
                button.classList.toggle('scroll-top-visible', window.scrollY > window.innerHeight * 0.9);
              };
              window.addEventListener('scroll', updateScrollTopButton, { passive: true });
              window.addEventListener('resize', updateScrollTopButton);
              setTimeout(updateScrollTopButton, 80);
            })();
            """
        ),
        rx.button(
            "Volver arriba",
            id="scroll-top-button",
            on_click=rx.call_script("window.scrollTo({ top: 0, behavior: 'smooth' })"),
            class_name="scroll-top-button",
        ),
    )
