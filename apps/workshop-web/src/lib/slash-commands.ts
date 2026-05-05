"use client";

import type { LucideIcon } from "lucide-react";
import {
  HelpCircle,
  Trash2,
  Download,
  Settings,
  RefreshCw,
  PlusSquare,
  Moon,
  Sun,
} from "lucide-react";

export interface SlashCommand {
  name: string;
  aliases: string[];
  description: string;
  icon: LucideIcon;
  category: "navigation" | "export" | "settings" | "debug" | "theme";
}

export const SLASH_COMMANDS: SlashCommand[] = [
  {
    name: "/help",
    aliases: ["/h", "/?"],
    description: "Show available commands and tips",
    icon: HelpCircle,
    category: "navigation",
  },
  {
    name: "/clear",
    aliases: ["/reset"],
    description: "Start a new conversation",
    icon: Trash2,
    category: "navigation",
  },
  {
    name: "/export",
    aliases: ["/save"],
    description: "Export conversation as JSON or Markdown",
    icon: Download,
    category: "export",
  },
  {
    name: "/settings",
    aliases: ["/config"],
    description: "Open system settings",
    icon: Settings,
    category: "settings",
  },
  {
    name: "/retry",
    aliases: ["/re"],
    description: "Retry the last message",
    icon: RefreshCw,
    category: "debug",
  },
  {
    name: "/new",
    aliases: ["/fresh"],
    description: "New conversation",
    icon: PlusSquare,
    category: "navigation",
  },
  {
    name: "/theme dark",
    aliases: [],
    description: "Switch to dark mode",
    icon: Moon,
    category: "theme",
  },
  {
    name: "/theme light",
    aliases: [],
    description: "Switch to light mode",
    icon: Sun,
    category: "theme",
  },
];

export function filterCommands(query: string): SlashCommand[] {
  if (!query) return SLASH_COMMANDS;
  const q = query.toLowerCase();
  return SLASH_COMMANDS.filter(
    (cmd) =>
      cmd.name.toLowerCase().includes(q) ||
      cmd.aliases.some((a) => a.toLowerCase().includes(q)) ||
      cmd.description.toLowerCase().includes(q)
  );
}

export interface CommandContext {
  clearDraft: () => void;
  createNewConversation: () => void;
  navigateToChat: (id: string) => void;
  openSettings: () => void;
  retryLastMessage: () => void;
  exportConversation: (format: "json" | "md") => void;
  setTheme: (theme: "light" | "dark" | "system") => void;
}

export function executeCommand(
  name: string,
  ctx: CommandContext
): boolean {
  switch (name) {
    case "/help":
      ctx.navigateToChat("help");
      return true;
    case "/clear":
    case "/new":
      ctx.createNewConversation();
      return true;
    case "/export":
      ctx.exportConversation("md");
      return true;
    case "/settings":
      ctx.openSettings();
      return true;
    case "/retry":
      ctx.retryLastMessage();
      return true;
    case "/theme dark":
      ctx.setTheme("dark");
      return true;
    case "/theme light":
      ctx.setTheme("light");
      return true;
    default:
      return false;
  }
}
