"use client";

import { useConversations } from "@/hooks/use-conversations";
import { useHealth } from "@/hooks/use-health";
import { useDocuments } from "@/hooks/use-documents";
import { GlassPanel } from "@/components/identity/glass-panel";
import { motion } from "framer-motion";
import { useUIStore } from "@/stores/ui-store";
import { useEffect, useState } from "react";
import Link from "next/link";
import { Clock, MessageSquare, Database, ArrowRight, Plus } from "lucide-react";

export default function ChatPage() {
  const { data: conversations } = useConversations();
  const { data: health } = useHealth();
  const { data: docs } = useDocuments();
  const setShowRain = useUIStore((s) => s.setShowRain);
  // First-name greeting — friendlier than the sci-fi "Operator".
  const greeting = "Fikri";

  useEffect(() => {
    setShowRain(true);
  }, [setShowRain]);

  const recentChats = conversations?.slice(0, 6) || [];
  const [time, setTime] = useState("");
  const [date, setDate] = useState("");

  useEffect(() => {
    const update = () => {
      setTime(new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }));
      setDate(new Date().toLocaleDateString([], { weekday: 'long', month: 'long', day: 'numeric' }));
    };
    update();
    const id = setInterval(update, 60_000);
    return () => clearInterval(id);
  }, []);

  const docCount = docs?.documents.length ?? 0;
  const systemOk = health?.status === "ok";

  return (
    <div className="flex-1 flex flex-col p-6 md:p-12 overflow-y-auto relative z-10 custom-scrollbar">
      {/* Welcome Header — tighter than before. Time + status pill share one row. */}
      <header className="mb-10 md:mb-12 space-y-3">
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center gap-3 text-white/40"
        >
          <Clock size={14} />
          <span className="text-[11px] font-mono uppercase tracking-[0.2em]">
            {time} • {date}
          </span>
          <span className="opacity-30">·</span>
          <span
            className={
              "text-[10px] font-bold uppercase tracking-widest flex items-center gap-1.5 " +
              (systemOk ? "text-emerald-400" : "text-rose-400")
            }
          >
            <span
              className={
                "w-1.5 h-1.5 rounded-full " +
                (systemOk ? "bg-emerald-400 animate-pulse" : "bg-rose-400")
              }
            />
            {systemOk ? "All systems operational" : "Degraded"}
          </span>
        </motion.div>
        <motion.h1
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="text-3xl md:text-4xl font-bold tracking-tight text-ink-100"
        >
          Welcome back, <span className="text-white/55">{greeting}</span>
        </motion.h1>
      </header>

      {/* Primary CTA strip — replaces the three sparse cards. */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 md:gap-4 mb-10">
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15 }}
        >
          <Link href="/chat" className="block h-full group">
            <GlassPanel className="p-5 h-full border border-white/15 bg-white text-black hover:bg-white/95 transition-all shadow-[0_0_40px_rgba(255,255,255,0.08)] flex items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-black text-white">
                  <Plus size={18} />
                </div>
                <div>
                  <p className="text-sm font-bold tracking-tight">Start new conversation</p>
                  <p className="text-[11px] opacity-60">Pick a persona and begin.</p>
                </div>
              </div>
              <ArrowRight size={16} className="opacity-50 group-hover:translate-x-0.5 transition-transform" />
            </GlassPanel>
          </Link>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
        >
          <Link href="/chat/documents" className="block h-full group">
            <GlassPanel className="p-5 h-full border border-white/10 bg-white/[0.04] hover:bg-white/[0.07] hover:border-white/20 transition-all flex items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-white/5 text-white/70">
                  <Database size={18} />
                </div>
                <div>
                  <p className="text-sm font-bold tracking-tight text-ink-100">Archive</p>
                  <p className="text-[11px] text-white/40">
                    {docCount === 0
                      ? "No documents yet."
                      : `${docCount} document${docCount === 1 ? "" : "s"} indexed.`}
                  </p>
                </div>
              </div>
              <ArrowRight size={16} className="text-white/30 group-hover:text-white/60 group-hover:translate-x-0.5 transition-all" />
            </GlassPanel>
          </Link>
        </motion.div>
      </div>

      {/* Recent Conversations — main content of the page. */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-[11px] font-bold uppercase tracking-[0.3em] text-white/25">
            Recent conversations
          </h2>
          {recentChats.length > 0 && (
            <span className="text-[10px] font-mono text-white/20 uppercase tracking-widest">
              {recentChats.length} of {conversations?.length ?? 0}
            </span>
          )}
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {recentChats.map((chat, i) => (
            <motion.div
              key={chat.id}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.25 + i * 0.04 }}
            >
              <Link href={`/chat/${chat.id}`} className="block group">
                <GlassPanel className="p-4 border border-white/[0.06] bg-white/[0.02] hover:bg-white/[0.05] hover:border-white/15 transition-all flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-white/5 text-white/35 group-hover:text-white/80 transition-colors shrink-0">
                    <MessageSquare size={15} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-white/75 truncate">
                      {chat.title || "Untitled"}
                    </p>
                    <p className="text-[10px] font-mono text-white/20 uppercase tracking-tighter mt-0.5">
                      {new Date(chat.updated_at).toLocaleDateString()}
                    </p>
                  </div>
                  <ArrowRight size={13} className="text-white/10 group-hover:text-white/40 group-hover:translate-x-0.5 transition-all shrink-0" />
                </GlassPanel>
              </Link>
            </motion.div>
          ))}
          {recentChats.length === 0 && (
            <div className="col-span-full py-10 border border-dashed border-white/5 rounded-2xl text-center">
              <p className="text-sm text-white/25 font-mono italic">No conversations yet.</p>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
