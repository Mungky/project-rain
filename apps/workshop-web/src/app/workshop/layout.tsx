"use client";

import { AuthGuard } from "@/components/system/auth-guard";
import { RainBackdrop } from "@/components/identity/rain-backdrop";
import { GlassPanel } from "@/components/identity/glass-panel";
import { HealthBadge } from "@/components/system/health-badge";
import { useUIStore } from "@/stores/ui-store";
import { AnimatePresence, motion } from "framer-motion";
import Image from "next/image";
import Link from "next/link";
import { FolderOpen, MessageSquare } from "lucide-react";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const tools = [
  { href: "/workshop/dcc", label: "DCC", icon: FolderOpen, description: "Document Control Center" },
];

export default function WorkshopLayout({ children }: { children: React.ReactNode }) {
  const showRain = useUIStore((s) => s.showRain);
  const pathname = usePathname();

  return (
    <AuthGuard>
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

        <div className="relative flex-1 flex h-screen overflow-hidden p-4 gap-4">
          {/* Sidebar */}
          <div className="w-[280px] h-full shrink-0 z-20">
            <GlassPanel className="h-full rounded-2xl border border-white/10 flex flex-col overflow-hidden bg-white/5 backdrop-blur-2xl">
              <div className="p-6 flex items-center gap-3 border-b border-white/10">
                <Link href="/chat" className="flex items-center gap-3 group">
                  <div className="relative">
                    <Image src="/rain-logo.svg" alt="Rain" width={28} height={28} className="relative z-10 transition-transform group-hover:scale-110" />
                    <div className="absolute inset-0 bg-white/20 blur-md group-hover:bg-white/40 transition-colors" />
                  </div>
                  <span className="font-bold text-lg tracking-[0.2em] text-white/90">RAIN</span>
                </Link>
              </div>

              <nav className="p-4 space-y-1">
                <p className="text-[9px] font-bold uppercase tracking-[0.3em] text-white/20 px-3 mb-3">Workshop Tools</p>
                {tools.map((tool) => (
                  <Link
                    key={tool.href}
                    href={tool.href}
                    className={cn(
                      "flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition-all",
                      pathname === tool.href
                        ? "bg-white text-black font-semibold"
                        : "text-white/50 hover:text-white hover:bg-white/5"
                    )}
                  >
                    <tool.icon size={16} />
                    <span>{tool.label}</span>
                    <span className="text-[9px] opacity-40 ml-auto">{tool.description}</span>
                  </Link>
                ))}
              </nav>

              <div className="mt-auto p-4 border-t border-white/10">
                <Link
                  href="/chat"
                  className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm text-white/30 hover:text-white hover:bg-white/5 transition-all"
                >
                  <MessageSquare size={16} />
                  Back to Chat
                </Link>
              </div>
            </GlassPanel>
          </div>

          {/* Main */}
          <main className="flex-1 flex flex-col min-w-0 h-full relative z-10 overflow-hidden">
            {children}
          </main>
        </div>

        <HealthBadge />
      </div>
    </AuthGuard>
  );
}
