"use client";

import { useEffect, useRef } from "react";
import { ArrowUpRight, Search, X } from "lucide-react";

export default function SearchResults({
  matches,
  query,
  busy,
  error,
  onClose,
  onSelect,
}: {
  matches: any[];
  query: string;
  busy: boolean;
  error: string;
  onClose: () => void;
  onSelect: (symbol: string) => void;
}) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const closeRef = useRef(onClose);
  closeRef.current = onClose;
  useEffect(() => {
    const dialog = dialogRef.current!;
    const previous = document.activeElement as HTMLElement | null;
    const overflow = document.body.style.overflow;
    dialog.showModal();
    document.body.style.overflow = "hidden";
    dialog.querySelector<HTMLButtonElement>(".search-match")?.focus();
    return () => {
      dialog.close();
      document.body.style.overflow = overflow;
      previous?.focus();
    };
  }, []);
  return (
    <dialog
      className="company-search-dialog"
      ref={dialogRef}
      aria-labelledby="search-dialog-title"
      onCancel={(e) => {
        e.preventDefault();
        closeRef.current();
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="search-dialog-content">
        <div className="search-dialog-heading">
          <Search size={21} />
          <div>
            <h2 id="search-dialog-title">Resultados para «{query}»</h2>
            <p>Selecciona la empresa y comprueba su mercado.</p>
          </div>
          <button
            className="icon"
            aria-label="Cerrar resultados"
            onClick={onClose}
          >
            <X size={20} />
          </button>
        </div>
        {error && (
          <div className="search-dialog-error" role="alert">
            {error}
          </div>
        )}
        <div
          className="search-matches"
          onKeyDown={(e) => {
            if (!["ArrowDown", "ArrowUp", "Home", "End"].includes(e.key))
              return;
            const buttons = Array.from(
              e.currentTarget.querySelectorAll<HTMLButtonElement>(
                "button:not(:disabled)",
              ),
            );
            if (!buttons.length) return;
            e.preventDefault();
            const current = buttons.indexOf(
              document.activeElement as HTMLButtonElement,
            );
            const next =
              e.key === "Home"
                ? 0
                : e.key === "End"
                  ? buttons.length - 1
                  : (current +
                      (e.key === "ArrowDown" ? 1 : -1) +
                      buttons.length) %
                    buttons.length;
            buttons[next].focus();
          }}
        >
          {matches.map((m) => (
            <button
              className="search-match"
              key={m.symbol}
              disabled={busy}
              onClick={() => onSelect(m.symbol)}
            >
              <span className="ticker-icon">{m.symbol.slice(0, 2)}</span>
              <span>
                <b>{m.symbol}</b>
                <small>{m.name}</small>
              </span>
              <span className="search-exchange">
                {m.exchange || "Mercado no indicado"}
              </span>
              <ArrowUpRight size={17} />
            </button>
          ))}
        </div>
        <div className="search-dialog-footer" role="status">
          {busy
            ? "Recuperando la empresa…"
            : `${matches.length} coincidencias · cobertura SEC`}
          <span>↑ ↓ navegar · Enter abrir · Esc cerrar</span>
        </div>
      </div>
    </dialog>
  );
}
