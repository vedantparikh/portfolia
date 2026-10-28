import { useEffect, useId, useRef } from "react";
import { createPortal } from "react-dom";

const FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]):not([type="hidden"]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

const open = [];

const focusables = (node) =>
  [...node.querySelectorAll(FOCUSABLE)].filter(
    (el) => el.offsetParent !== null || el === document.activeElement,
  );

// Rendered into document.body. The overlay is the dialog and takes focus unless a
// child autofocused. Esc and (optionally) a click on the backdrop close it, Tab
// stays inside, and focus returns to the opener. Without `labelledBy`, the first
// heading labels it.
const Modal = ({
  onClose,
  children,
  overlayClassName = "fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4",
  closeOnBackdrop = false,
  closeOnEscape = true,
  labelledBy,
}) => {
  const ref = useRef(null);
  const onCloseRef = useRef(onClose);
  const headingId = useId();

  useEffect(() => {
    onCloseRef.current = onClose;
  });

  useEffect(() => {
    const node = ref.current;
    const previous = document.activeElement;
    open.push(node);

    if (!labelledBy) {
      const heading = node.querySelector("h1, h2, h3, h4");
      if (heading) {
        if (!heading.id) heading.id = headingId;
        node.setAttribute("aria-labelledby", heading.id);
      }
    }
    if (!node.contains(document.activeElement)) {
      node.focus();
    }

    const onKeyDown = (event) => {
      if (open[open.length - 1] !== node) return;
      if (event.key === "Escape" && closeOnEscape) {
        event.stopPropagation();
        onCloseRef.current?.();
        return;
      }
      if (event.key !== "Tab") return;
      const items = focusables(node);
      if (items.length === 0) {
        event.preventDefault();
        node.focus();
        return;
      }
      const first = items[0];
      const last = items[items.length - 1];
      if (event.shiftKey && (document.activeElement === first || !node.contains(document.activeElement))) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && (document.activeElement === last || !node.contains(document.activeElement))) {
        event.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", onKeyDown);

    return () => {
      document.removeEventListener("keydown", onKeyDown);
      open.splice(open.indexOf(node), 1);
      if (previous instanceof HTMLElement && previous.isConnected) {
        previous.focus();
      }
    };
  }, [closeOnEscape, headingId, labelledBy]);

  return createPortal(
    <div
      ref={ref}
      role="dialog"
      aria-modal="true"
      aria-labelledby={labelledBy}
      tabIndex={-1}
      className={`${overlayClassName} outline-none`}
      onClick={
        closeOnBackdrop
          ? (event) => {
              if (event.target === event.currentTarget) onClose?.();
            }
          : undefined
      }
    >
      {children}
    </div>,
    document.body,
  );
};

export default Modal;
