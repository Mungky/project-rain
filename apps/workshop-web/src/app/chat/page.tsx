"use client";

import { useConversations } from "@/hooks/use-conversations";
import { useHealth } from "@/hooks/use-health";
import { useDocuments } from "@/hooks/use-documents";
import { GlassPanel } from "@/components/identity/glass-panel";
import { motion } from "framer-motion";
import { useUIStore } from "@/stores/ui-store";
import { useAuthStore } from "@/stores/auth-store";
import { useEffect, useState } from "react";
import Link from "next/link";
import { Clock, MessageSquare, Database, Activity, ArrowRight, Plus } from "lucide-react";

export default function ChatPage() {
  const { data: conversations } = useConversations();
  const { data: health } = useHealth();
  const { data: docs } = useDocuments();
  const setShowRain = useUIStore((s) => s.setShowRain);
  const username = useAuthStore((s) => s.user?.username ?? "Operator");

  useEffect(() => {
    setShowRain(true);
  }, [setShowRain]);

  const recentChats = conversations?.slice(0, 3) || [];
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

  return (
    <div className="flex-1 flex flex-col p-8 md:p-12 overflow-y-auto relative z-10 custom-scrollbar">
      {/* Welcome Header */}
      <header className="mb-12 space-y-2">
        <motion.div 
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center gap-3 text-white/40 mb-4"
        >
          <Clock size={16} />
          <span className="text-xs font-mono uppercase tracking-[0.2em]">{time} • {date}</span>
        </motion.div>
        <motion.h1 
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="text-4xl md:text-5xl font-bold tracking-tighter text-white"
        >
          Welcome back, <span className="text-white/60">{username}</span>
        </motion.h1>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-12">
        {/* System Pulse Card */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.2 }}
        >
          <GlassPanel className="p-6 h-full border-white/10 bg-white/5 backdrop-blur-3xl group hover:border-white/20 transition-all">
            <div className="flex items-center justify-between mb-6">
              <div className="p-2 rounded-xl bg-white/5 text-white/60">
                <Activity size={20} />
              </div>
              {health?.status === "ok" ? (
                <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-[10px] font-bold text-emerald-500 uppercase tracking-widest">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                  Operational
                </div>
              ) : (
                <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-rose-500/10 border border-rose-500/20 text-[10px] font-bold text-rose-400 uppercase tracking-widest">
                  <span className="w-1.5 h-1.5 rounded-full bg-rose-400" />
                  Degraded
                </div>
              )}
            </div>
            <h3 className="text-sm font-bold text-white mb-2 tracking-wide">System Pulse</h3>
            <div className="space-y-3">
              <div className="flex justify-between text-xs font-mono">
                <span className="text-white/30 uppercase">Neural Engine</span>
                <span className={health?.ollama ? "text-emerald-500" : "text-rose-500"}>{health?.ollama ? "READY" : "OFFLINE"}</span>
              </div>
              <div className="flex justify-between text-xs font-mono">
                <span className="text-white/30 uppercase">Memory Core</span>
                <span className={health?.postgres ? "text-emerald-500" : "text-rose-500"}>{health?.postgres ? "SYNCED" : "OFFLINE"}</span>
              </div>
              <div className="flex justify-between text-xs font-mono">
                <span className="text-white/30 uppercase">Cache</span>
                <span className={health?.redis ? "text-emerald-500" : "text-rose-500"}>{health?.redis ? "READY" : "OFFLINE"}</span>
              </div>
              <div className="flex justify-between text-xs font-mono">
                <span className="text-white/30 uppercase">Storage</span>
                <span className={health?.minio ? "text-emerald-500" : "text-rose-500"}>{health?.minio ? "READY" : "OFFLINE"}</span>
              </div>
              <div className="flex justify-between text-xs font-mono">
                <span className="text-white/30 uppercase">Vector DB</span>
                <span className={health?.qdrant ? "text-emerald-500" : "text-rose-500"}>{health?.qdrant ? "READY" : "OFFLINE"}</span>
              </div>
            </div>
          </GlassPanel>
        </motion.div>

        {/* Neural Archive Summary */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.3 }}
        >
          <GlassPanel className="p-6 h-full border-white/10 bg-white/5 backdrop-blur-3xl group hover:border-white/20 transition-all">
             <div className="flex items-center justify-between mb-6">
              <div className="p-2 rounded-xl bg-white/5 text-white/60">
                <Database size={20} />
              </div>
              <Link href="/chat/documents" className="text-[10px] font-bold text-white/30 hover:text-white uppercase tracking-widest transition-colors flex items-center gap-1">
                View All <ArrowRight size={10} />
              </Link>
            </div>
            <h3 className="text-sm font-bold text-white mb-2 tracking-wide">Neural Archive</h3>
            <p className="text-xs text-white/40 leading-relaxed">
              Currently indexing <span className="text-white font-mono">{docs?.documents.length || 0}</span> knowledge fragments across the local cluster.
            </p>
          </GlassPanel>
        </motion.div>

        {/* Quick Start Card */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.4 }}
        >
          <Link href="/chat" className="block h-full group">
            <GlassPanel className="p-6 h-full border-white/20 bg-white text-black hover:bg-white/90 transition-all shadow-[0_0_40px_rgba(255,255,255,0.1)]">
               <div className="flex items-center justify-between mb-6">
                <div className="p-2 rounded-xl bg-black text-white">
                  <Plus size={20} />
                </div>
              </div>
              <h3 className="text-sm font-black uppercase tracking-[0.1em] mb-2">Initialize Session</h3>
              <p className="text-xs font-medium opacity-60">Spawn a new neural thread to begin processing.</p>
            </GlassPanel>
          </Link>
        </motion.div>
      </div>

      {/* Recent Nodes */}
      <section className="space-y-6">
        <h2 className="text-xs font-bold uppercase tracking-[0.3em] text-white/20">Recent Neural Threads</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {recentChats.map((chat, i) => (
            <motion.div
              key={chat.id}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.5 + i * 0.1 }}
            >
              <Link href={`/chat/${chat.id}`}>
                <GlassPanel className="p-4 border-white/5 bg-white/[0.02] hover:bg-white/5 hover:border-white/10 transition-all flex items-center gap-4">
                  <div className="p-2.5 rounded-lg bg-white/5 text-white/30 group-hover:text-white transition-colors">
                    <MessageSquare size={16} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-white/70 truncate">{chat.title || "Untitled Session"}</p>
                    <p className="text-[10px] font-mono text-white/20 uppercase tracking-tighter">{new Date(chat.updated_at).toLocaleDateString()}</p>
                  </div>
                  <ArrowRight size={14} className="text-white/10" />
                </GlassPanel>
              </Link>
            </motion.div>
          ))}
          {recentChats.length === 0 && (
             <div className="col-span-full py-12 border-2 border-dashed border-white/5 rounded-2xl text-center">
                <p className="text-sm text-white/20 font-mono italic">No active neural threads found.</p>
             </div>
          )}
        </div>
      </section>
    </div>
  );
}