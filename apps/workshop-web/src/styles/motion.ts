import type { Variants, Transition } from "framer-motion";

export const easeStandard: Transition = {
  duration: 0.32,
  ease: [0.22, 1, 0.36, 1],
};

export const easeQuick: Transition = {
  duration: 0.18,
  ease: [0.4, 0, 0.2, 1],
};

export const easeSlow: Transition = {
  duration: 0.48,
  ease: [0.22, 1, 0.36, 1],
};

export const fadeUp: Variants = {
  hidden: { opacity: 0, y: 8 },
  visible: { opacity: 1, y: 0 },
};

export const fade: Variants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1 },
};

export const tokenAppear: Variants = {
  hidden: { opacity: 0, filter: "blur(1.5px)" },
  visible: { opacity: 1, filter: "blur(0)" },
};

// Spring-based message entrance — natural, not too bouncy
export const messageAppear: Variants = {
  hidden: { opacity: 0, y: 12, scale: 0.98 },
  visible: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { type: "spring", damping: 22, stiffness: 200, mass: 0.6 },
  },
};

// Copy success checkmark bounce
export const copySuccess: Variants = {
  initial: { scale: 1 },
  bounce: { scale: [1, 1.35, 1], transition: { duration: 0.4, ease: "easeOut" } },
};

// Shimmer skeleton loading animation
export const shimmer = {
  background: [
    "linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.04) 50%, transparent 100%)",
    "linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.04) 50%, transparent 100%)",
  ],
  backgroundSize: "200% 100%",
  backgroundPosition: ["200% 0", "-200% 0"],
  transition: { repeat: Infinity, duration: 1.8, ease: "linear" },
};