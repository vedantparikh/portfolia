import { Info } from "lucide-react";
import { useEffect, useId, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Link } from "react-router";

import { GUIDE_BY_ID } from "../metricGuide";

const WIDTH = 320;

// ⓘ next to a metric: what it is, how to read it, good/bad, what it implies
const InfoTip = ({ id, className = "" }) => {
  const entry = GUIDE_BY_ID[id];
  const [position, setPosition] = useState(null);
  const button = useRef(null);
  const panel = useRef(null);
  const panelId = useId();

  useEffect(() => {
    if (!position) return undefined;
    const close = () => setPosition(null);
    const onKey = (event) => event.key === "Escape" && close();
    const onPointer = (event) => {
      if (!panel.current?.contains(event.target) && !button.current?.contains(event.target)) close();
    };
    document.addEventListener("keydown", onKey);
    document.addEventListener("mousedown", onPointer);
    window.addEventListener("scroll", close, true);
    window.addEventListener("resize", close);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("mousedown", onPointer);
      window.removeEventListener("scroll", close, true);
      window.removeEventListener("resize", close);
    };
  }, [position]);

  if (!entry) return null;

  const toggle = (event) => {
    event.stopPropagation();
    if (position) {
      setPosition(null);
      return;
    }
    const rect = button.current.getBoundingClientRect();
    const left = Math.min(Math.max(8, rect.left - 12), window.innerWidth - WIDTH - 8);
    const below = rect.bottom + 6;
    const fitsBelow = below + 360 < window.innerHeight;
    setPosition(fitsBelow ? { left, top: below } : { left, bottom: window.innerHeight - rect.top + 6 });
  };

  return (
    <>
      <button
        ref={button}
        type="button"
        onClick={toggle}
        aria-label={`About ${entry.name}`}
        aria-expanded={Boolean(position)}
        aria-controls={position ? panelId : undefined}
        className={`inline-flex align-middle text-gray-500 hover:text-gray-300 focus:outline-none focus-visible:text-primary-400 ${className}`}
      >
        <Info size={14} />
      </button>
      {position &&
        createPortal(
          <div
            ref={panel}
            id={panelId}
            role="dialog"
            aria-label={entry.name}
            style={{ position: "fixed", width: WIDTH, ...position }}
            className="z-[70] max-h-[70vh] overflow-y-auto rounded-lg border border-dark-600 bg-dark-900 p-4 text-left text-sm shadow-xl"
          >
            <p className="font-semibold text-gray-100">{entry.name}</p>
            <p className="mt-1 text-gray-300">{entry.short}</p>
            <dl className="mt-3 space-y-2">
              <div>
                <dt className="text-xs uppercase tracking-wide text-gray-500">How to read it</dt>
                <dd className="text-gray-300">{entry.read}</dd>
              </div>
              <div>
                <dt className="text-xs uppercase tracking-wide text-success-400">Good</dt>
                <dd className="text-gray-300">{entry.good}</dd>
              </div>
              <div>
                <dt className="text-xs uppercase tracking-wide text-danger-400">Watch out</dt>
                <dd className="text-gray-300">{entry.bad}</dd>
              </div>
              <div>
                <dt className="text-xs uppercase tracking-wide text-primary-400">What it implies</dt>
                <dd className="text-gray-300">{entry.implies}</dd>
              </div>
            </dl>
            <Link
              to={`/concepts#${entry.id}`}
              onClick={() => setPosition(null)}
              className="mt-3 inline-block text-xs text-primary-400 hover:text-primary-300"
            >
              How it is calculated, with an example →
            </Link>
          </div>,
          document.body,
        )}
    </>
  );
};

export default InfoTip;
