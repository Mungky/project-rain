"use client";

import { GlassPanel } from "@/components/identity/glass-panel";
import { RainBackdrop } from "@/components/identity/rain-backdrop";
import { ConversationSidebar } from "@/components/chat/conversation-sidebar";
import { InfoPanel } from "@/components/chat/info-panel";
import { SettingsModal } from "@/components/system/settings-modal";
import { HealthBadge } from "@/components/system/health-badge";
import { ImageLightbox } from "@/components/chat/image-lightbox";
import { ArtifactsPanel } from "@/components/chat/artifacts-panel";
import { useUIStore } from "@/stores/ui-store";
import { AnimatePresence, motion } from "framer-motion";
import Image from "next/image";
import Link from "next/link";
import { Menu, X } from "lucide-react";
import { useShallow } from "zustand/react/shallow";
import { useEffect } from "react";
import { usePathname } from "next/navigation";

export default function ChatLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { showRain, mobileSidebarOpen, toggleMobileSidebar, closeMobileSidebar } = useUIStore(
    useShallow((s) => ({
      showRain: s.showRain,
      mobileSidebarOpen: s.mobileSidebarOpen,
      toggleMobileSidebar: s.toggleMobileSidebar,
      closeMobileSidebar: s.closeMobileSidebar,
    }))
  );

  // Close mobile drawer when route changes (user picked a conversation).
  const pathname = usePathname();
  useEffect(() => {
    closeMobileSidebar();
  }, [pathname, closeMobileSidebar]);

  return (
    <div className="relative min-h-screen bg-black overflow-hidden flex font-sans text-white">
      <AnimatePresence>
        {showRain && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 2 }}
            className="fixed inset-0 z-0"
          >
            <RainBackdrop />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Mobile top bar */}
      <div className="md:hidden fixed top-0 inset-x-0 z-40 flex items-center justify-between px-3 py-2 bg-black/70 backdrop-blur-xl border-b border-white/5">
        <button
          onClick={toggleMobileSidebar}
          className="p-2 rounded-xl text-white/70 hover:bg-white/10 transition-colors"
          aria-label="Open conversations"
        >
          <Menu size={20} />
        </button>
        <Link href="/chat" className="flex items-center gap-2">
          <Image src="/rain-logo.svg" alt="Rain" width={20} height={20} />
          <span className="font-bold text-sm tracking-[0.2em] text-white/90">RAIN</span>
        </Link>
        <div className="w-9" />
      </div>

      {/* Mobile sidebar drawer overlay */}
      <AnimatePresence>
        {mobileSidebarOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              onClick={closeMobileSidebar}
              className="md:hidden fixed inset-0 z-40 bg-black/60 backdrop-blur-sm"
            />
            <motion.div
              initial={{ x: "-100%" }}
              animate={{ x: 0 }}
              exit={{ x: "-100%" }}
              transition={{ type: "spring", damping: 25, stiffness: 250 }}
              className="md:hidden fixed inset-y-0 left-0 z-50 w-[85vw] max-w-[320px] p-3"
            >
              <GlassPanel className="h-full rounded-2xl border border-white/10 flex flex-col overflow-hidden bg-black/90 backdrop-blur-2xl">
                <div className="p-4 flex items-center justify-between border-b border-white/10">
                  <Link href="/chat" className="flex items-center gap-3 group" onClick={closeMobileSidebar}>
                    <Image src="/rain-logo.svg" alt="Rain" width={24} height={24} />
                    <span className="font-bold text-base tracking-[0.2em] text-white/90">RAIN</span>
                  </Link>
                  <button
                    onClick={closeMobileSidebar}
                    className="p-2 rounded-xl text-white/40 hover:text-white hover:bg-white/10 transition-colors"
                    aria-label="Close"
                  >
                    <X size={18} />
                  </button>
                </div>
                <ConversationSidebar />
              </GlassPanel>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* 3-Column System (desktop) */}
      <div className="relative flex-1 flex h-screen overflow-hidden p-2 md:p-4 gap-2 md:gap-4 pt-[3.5rem] md:pt-4">
        {/* Sidebar (Left) — hidden on mobile (drawer above replaces it) */}
        <div className="hidden md:block w-[280px] h-full shrink-0 z-20">
          <GlassPanel className="h-full rounded-2xl border border-white/10 flex flex-col overflow-hidden bg-white/5 backdrop-blur-2xl">
            <div className="p-6 flex items-center gap-3 border-b border-white/10">
              <Link href="/chat" className="flex items-center gap-3 group">
                <div className="relative">
                  <Image
                    src="/rain-logo.svg"
                    alt="Rain Logo"
                    width={28}
                    height={28}
                    className="relative z-10 transition-transform group-hover:scale-110"
                  />
                  <div className="absolute inset-0 bg-white/20 blur-md group-hover:bg-white/40 transition-colors" />
                </div>
                <span className="font-bold text-lg tracking-[0.2em] text-white/90">RAIN</span>
              </Link>
            </div>
            <ConversationSidebar />
          </GlassPanel>
        </div>

        {/* Main Chat (Center) */}
        <main className="flex-1 flex flex-col min-w-0 h-full relative z-10">
          <div className="flex-1 relative flex flex-col overflow-hidden">
            {children}
          </div>
        </main>

        {/* Info Panel (Right) — hidden on mobile (Brain icon in top bar opens it) */}
        <div className="hidden md:block">
          <InfoPanel />
        </div>
        <ArtifactsPanel />
      </div>

      {/* Settings modal — always accessible */}
      <AnimatePresence>
        <SettingsModal key="settings" />
      </AnimatePresence>

      <HealthBadge />
      <ImageLightbox />
    </div>
  );
}