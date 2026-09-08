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
              const selector = '[data-deo-scroll-top="true"]';
              const keepSingleScrollTopButton = () => {
                const buttons = Array.from(document.querySelectorAll(selector));
                const [button, ...duplicates] = buttons;
                duplicates.forEach((duplicate) => {
                  const owner = duplicate.closest('[data-deo-scroll-top-owner="true"]');
                  (owner || duplicate).remove();
                });
                return button;
              };
              const updateScrollTopButton = () => {
                const button = keepSingleScrollTopButton();
                if (!button) return;
                const scrollOwner = document.scrollingElement || document.documentElement;
                button.classList.toggle('scroll-top-visible', scrollOwner.scrollTop > window.innerHeight * 0.9);
              };
              window.__deoUpdateScrollTop = updateScrollTopButton;
              if (!window.__deoScrollTopObserver) {
                window.__deoScrollTopObserver = new MutationObserver(() => window.__deoUpdateScrollTop?.());
                window.__deoScrollTopObserver.observe(document.documentElement, { childList: true, subtree: true });
              }
              if (!window.__deoScrollTopReady) {
                window.__deoScrollTopReady = true;
                window.addEventListener('scroll', () => window.__deoUpdateScrollTop?.(), { passive: true });
                window.addEventListener('resize', () => window.__deoUpdateScrollTop?.());
              }
              setTimeout(updateScrollTopButton, 80);
            })();
            """
        ),
        rx.box(
            rx.button(
                "Volver arriba",
                id="scroll-top-button",
                data_deo_scroll_top="true",
                on_click=rx.call_script(scroll_to_document_top),
                class_name="scroll-top-button",
            ),
            data_deo_scroll_top_owner="true",
        ),
    )
