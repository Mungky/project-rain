"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useUIStore } from "@/stores/ui-store";
import { useAuthStore } from "@/stores/auth-store";
import { cn } from "@/lib/utils";
import { NimbusChat } from "@/components/nimbus/nimbus-chat";

export default function DCCPage() {
  const setShowRain = useUIStore((s) => s.setShowRain);

  useEffect(() => {
    setShowRain(true);
  }, [setShowRain]);

  return (
    <div className="flex-1 flex flex-col min-h-0 relative z-10">
      <NimbusChat />
    </div>
  );
}
