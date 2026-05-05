"use client";

import { create } from "zustand";

interface LightboxState {
  isOpen: boolean;
  images: { src: string; alt: string }[];
  currentIndex: number;
  open: (images: { src: string; alt: string }[], index: number) => void;
  close: () => void;
  next: () => void;
  prev: () => void;
}

export const useLightboxStore = create<LightboxState>((set, get) => ({
  isOpen: false,
  images: [],
  currentIndex: 0,

  open: (images, index) =>
    set({ isOpen: true, images, currentIndex: index }),

  close: () =>
    set({ isOpen: false, images: [], currentIndex: 0 }),

  next: () => {
    const { images, currentIndex } = get();
    if (images.length <= 1) return;
    set({ currentIndex: (currentIndex + 1) % images.length });
  },

  prev: () => {
    const { images, currentIndex } = get();
    if (images.length <= 1) return;
    set({
      currentIndex: (currentIndex - 1 + images.length) % images.length,
    });
  },
}));
