"use client";

import { useEffect, useCallback, useState } from "react";
import { useLightboxStore } from "@/stores/lightbox-store";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronLeft, ChevronRight, X, ZoomIn, ZoomOut } from "lucide-react";
import { cn } from "@/lib/utils";

export function ImageLightbox() {
  const { isOpen, images, currentIndex, close, next, prev } = useLightboxStore();
  const [zoomed, setZoomed] = useState(false);

  // Keyboard nav
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (!isOpen) return;
      if (e.key === "Escape") close();
      if (e.key === "ArrowRight") next();
      if (e.key === "ArrowLeft") prev();
      if (e.key === "z") setZoomed((z) => !z);
    },
    [isOpen, close, next, prev]
  );

  useEffect(() => {
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  // Listen for lightbox-open custom events
  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent).detail as {
        images: { src: string; alt: string }[];
        index: number;
      };
      useLightboxStore.getState().open(detail.images, detail.index);
    };
    window.addEventListener("lightbox-open", handler);
    return () => window.removeEventListener("lightbox-open", handler);
  }, []);

  // Lock body scroll when open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
      setZoomed(false);
    }
    return () => { document.body.style.overflow = ""; };
  }, [isOpen]);

  if (!isOpen || images.length === 0) return null;

  const current = images[currentIndex];
  if (!current) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.2 }}
        className="fixed inset-0 z-[100] flex items-center justify-center bg-black/95 backdrop-blur-md"
        onClick={close}
      >
        {/* Close button */}
        <button
          onClick={close}
          className="absolute top-4 right-4 p-2 rounded-full bg-white/10 hover:bg-white/20 text-white/70 hover:text-white transition-all z-10"
          aria-label="Close lightbox"
        >
          <X size={20} />
        </button>

        {/* Zoom toggle */}
        <button
          onClick={(e) => { e.stopPropagation(); setZoomed((z) => !z); }}
          className="absolute top-4 left-4 p-2 rounded-full bg-white/10 hover:bg-white/20 text-white/70 hover:text-white transition-all z-10"
          aria-label={zoomed ? "Fit to screen" : "Zoom to 100%"}
        >
          {zoomed ? <ZoomOut size={20} /> : <ZoomIn size={20} />}
        </button>

        {/* Counter */}
        <div className="absolute top-4 left-1/2 -translate-x-1/2 text-xs font-mono text-white/40 bg-white/5 px-3 py-1.5 rounded-full border border-white/10">
          {currentIndex + 1} / {images.length}
        </div>

        {/* Previous */}
        {images.length > 1 && (
          <button
            onClick={(e) => { e.stopPropagation(); prev(); }}
            className="absolute left-4 top-1/2 -translate-y-1/2 p-3 rounded-full bg-white/10 hover:bg-white/20 text-white/70 hover:text-white transition-all z-10"
            aria-label="Previous image"
          >
            <ChevronLeft size={24} />
          </button>
        )}

        {/* Image */}
        <motion.div
          key={currentIndex}
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.2 }}
          className="max-w-[90vw] max-h-[90vh] flex items-center justify-center"
          onClick={(e) => e.stopPropagation()}
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={current.src}
            alt={current.alt}
            className={cn(
              "select-none",
              zoomed
                ? "max-w-none max-h-none"
                : "max-w-[90vw] max-h-[90vh] object-contain rounded-xl"
            )}
            style={zoomed ? { cursor: "zoom-out" } : { cursor: "pointer" }}
            onClick={() => setZoomed((z) => !z)}
          />
        </motion.div>

        {/* Next */}
        {images.length > 1 && (
          <button
            onClick={(e) => { e.stopPropagation(); next(); }}
            className="absolute right-4 top-1/2 -translate-y-1/2 p-3 rounded-full bg-white/10 hover:bg-white/20 text-white/70 hover:text-white transition-all z-10"
            aria-label="Next image"
          >
            <ChevronRight size={24} />
          </button>
        )}
      </motion.div>
    </AnimatePresence>
  );
}


