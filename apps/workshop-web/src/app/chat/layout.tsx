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
import { useShallow } from "zustand/react/shallow";

export default function ChatLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { showRain } = useUIStore(
    useShallow((s) => ({
      showRain: s.showRain,
    }))
  );

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
      
      {/* 3-Column System */}
      <div className="relative flex-1 flex h-screen overflow-hidden p-4 gap-4">
        
        {/* Sidebar (Left) - NOW FIXED */}
        <div className="w-[280px] h-full shrink-0 z-20">
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

        {/* Info Panel (Right) */}
        <InfoPanel />
        <ArtifactsPanel />
      </div>

      <AnimatePresence>
        <SettingsModal key="settings" />
      </AnimatePresence>
      <HealthBadge />
      <ImageLightbox />
    </div>
  );
}