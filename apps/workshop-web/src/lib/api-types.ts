export interface Paths {
  "/v1/health": {
    get: {
      responses: {
        200: {
          content: {
            "application/json": {
              status: string;
              ollama: boolean;
              postgres: boolean;
              redis: boolean;
            };
          };
        };
      };
    };
  };
  "/v1/conversations": {
    get: {
      responses: {
        200: {
          content: {
            "application/json": ConversationResponse[];
          };
        };
      };
    };
    post: {
      responses: {
        200: {
          content: {
            "application/json": ConversationResponse;
          };
        };
      };
    };
  };
  "/v1/conversations/{conversation_id}": {
    get: {
      responses: {
        200: {
          content: {
            "application/json": ConversationDetailResponse;
          };
        };
      };
    };
    patch: {
      body: Partial<ConversationDetailResponse>;
      responses: {
        200: {
          content: {
            "application/json": ConversationDetailResponse;
          };
        };
      };
    };
    delete: {
      responses: {
        204: {};
      };
    };
  };
  "/v1/conversations/{conversation_id}/messages": {
    post: {
      responses: {
        200: {
          content: {
            "text/event-stream": unknown;
          };
        };
      };
    };
  };
  "/v1/messages/{message_id}/feedback": {
    put: {
      body: FeedbackPayload;
      responses: {
        200: {
          content: {
            "application/json": { ok: boolean };
          };
        };
      };
    };
  };
  "/v1/documents": {
    get: {
      responses: {
        200: {
          content: {
            "application/json": DocumentListResponse;
          };
        };
      };
    };
    post: {
      responses: {
        201: {
          content: {
            "application/json": DocumentUploadResponse;
          };
        };
      };
    };
  };
  "/v1/documents/{document_id}": {
    delete: {
      responses: {
        204: {};
      };
    };
  };
  "/v1/models": {
    get: {
      responses: {
        200: {
          content: {
            "application/json": ModelResponse[];
          };
        };
      };
    };
  };
  "/v1/skills": {
    get: {
      responses: {
        200: {
          content: {
            "application/json": SkillResponse[];
          };
        };
      };
    };
    post: {
      body: { git_url: string };
      responses: {
        201: {
          content: {
            "application/json": SkillResponse;
          };
        };
      };
    };
  };
  "/v1/skills/{name}": {
    delete: {
      responses: {
        204: {};
      };
    };
  };
  "/v1/user/preferences": {
    get: {
      responses: {
        200: {
          content: {
            "application/json": UserPreferencesResponse;
          };
        };
      };
    };
    patch: {
      body: Partial<UserPreferencesResponse>;
      responses: {
        200: {
          content: {
            "application/json": UserPreferencesResponse;
          };
        };
      };
    };
  };
}

export interface ProviderConfig {
  enabled: boolean;
  key?: string;
  base_url?: string;
}

export interface UserPreferencesResponse {
  providers: {
    anthropic: ProviderConfig;
    openai: ProviderConfig;
    google: ProviderConfig;
    ollama: ProviderConfig;
  };
  custom_system_prompt: string | null;
  hidden_models: string[];
  custom_modes: CustomMode[];
}

export type Persona = "drizzle" | "shower" | "storm";

/** A user-defined behavior mode. */
export interface CustomMode {
  key: string;
  label: string;
  directive: string;
}

/** A selectable behavior mode (built-in preset or custom). */
export interface ModeOption {
  key: string;
  label: string;
  subtitle: string;
  builtin: boolean;
}

export interface ModesResponse {
  modes: ModeOption[];
}

export interface ConversationResponse {
  id: string;
  title: string | null;
  persona: Persona;
  behavior_mode?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ConversationDetailResponse {
  id: string;
  user_id: string;
  title: string | null;
  persona: Persona;
  behavior_mode?: string | null;
  auto_skills: boolean;
  enabled_skills: string[];
  messages: MessageResponse[];
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
}

export interface MessageAttachment {
  id: string;
  filename: string;
  mime: string;
}

export interface MessageResponse {
  id: string;
  role: "user" | "assistant" | "system" | "tool";
  content: string;
  reasoning_content: string | null;
  tool_events: ToolEvent[] | null;
  react_steps: ReactStep[] | null;
  feedback: number | null;
  model: string | null;
  tokens_in: number | null;
  tokens_out: number | null;
  attachments: MessageAttachment[];
  created_at: string;
}

export type FeedbackRating = 1 | -1 | 0 | null;

export interface FeedbackPayload {
  feedback: FeedbackRating;
}

export interface DocumentResponse {
  id: string;
  user_id: string;
  filename: string;
  mime: string;
  minio_key: string;
  qdrant_collection: string;
  source_type: "manual" | "chat";
  message_id: string | null;
  status: "uploading" | "processing" | "ready" | "error";
  created_at: string;
  updated_at: string;
}

export interface DocumentListResponse {
  documents: DocumentResponse[];
  total_count: number;
}

export interface DocumentUploadResponse {
  id: string;
  filename: string;
  mime: string;
  status: string;
  chunk_count: number;
  created_at: string;
}

export type ModelCapability = "chat" | "tools" | "vision" | "thinking" | "image-gen";

export interface ModelResponse {
  id: string;
  name: string;
  display_name: string | null;
  provider: string;
  enabled: boolean;
  capabilities: ModelCapability[];
}

export interface PromptResponse {
  id: string;
  name: string;
  description: string | null;
  content: string;
  category: string | null;
  is_default: boolean;
  created_at: string;
  updated_at: string;
}

export interface CreatePromptBody {
  name: string;
  content: string;
  description?: string | null;
  category?: string | null;
  is_default?: boolean;
}

// Drizzle (chat) tags
export type DrizzleTag =
  | "default"
  | "general_knowledge"
  | "text"
  | "vision"
  | "document"
  | "math"
  | "instruction"
  | "multi_turn"
  | "creative_writing"
  | "coding"
  | "hard_prompt"
  | "hard_prompt_en"
  | "english";

// Shower (quick-reply) tags
export type ShowerTag =
  | "default"
  | "general_knowledge"
  | "text"
  | "translation"
  | "english";

// Storm (orchestrator) tags — full set like Drizzle
export type StormTag =
  | "default"
  | "general_knowledge"
  | "text"
  | "vision"
  | "document"
  | "math"
  | "instruction"
  | "multi_turn"
  | "creative_writing"
  | "coding"
  | "hard_prompt"
  | "hard_prompt_en"
  | "english";

export type ModelTag = DrizzleTag | ShowerTag | StormTag;

export const DRIZZLE_TAG_LABELS: Record<DrizzleTag, string> = {
  default:          "Default",
  general_knowledge:"General Knowledge",
  text:             "Text",
  vision:           "Vision",
  document:         "Document",
  math:             "Math",
  instruction:      "Instruction",
  multi_turn:       "Multi-Turn",
  creative_writing: "Creative Writing",
  coding:           "Coding",
  hard_prompt:      "Hard Prompt",
  hard_prompt_en:   "Hard Prompt (EN)",
  english:          "English",
};

export const SHOWER_TAG_LABELS: Record<ShowerTag, string> = {
  default:          "Default",
  general_knowledge:"General Knowledge",
  text:             "Text",
  translation:      "Translation",
  english:          "English",
};

export const STORM_TAG_LABELS: Record<StormTag, string> = {
  ...DRIZZLE_TAG_LABELS,
};

export const MODEL_TAG_LABELS: Record<ModelTag, string> = {
  ...DRIZZLE_TAG_LABELS,
  ...SHOWER_TAG_LABELS,
  ...STORM_TAG_LABELS,
};

export function getTagsForPersona(persona: string): ModelTag[] {
  if (persona === "shower") return Object.keys(SHOWER_TAG_LABELS) as ShowerTag[];
  if (persona === "storm") return Object.keys(STORM_TAG_LABELS) as StormTag[];
  return Object.keys(DRIZZLE_TAG_LABELS) as DrizzleTag[];
}

// ── Usage ─────────────────────────────────────────────────────────────────────

export type UsagePeriod = "all" | "today" | "week" | "month";

export interface UsageByModel {
  model: string;
  tokens_in: number;
  tokens_out: number;
  messages: number;
}

export interface UsageResponse {
  total_tokens_in: number;
  total_tokens_out: number;
  total_messages: number;
  total_conversations: number;
  by_model: UsageByModel[];
  period: UsagePeriod;
}

export interface ModelCapabilityOverride {
  model_id: string;
  display_name?: string | null;
  capabilities: ModelCapability[];
  tags: ModelTag[];
  notes?: string | null;
  persona: Persona;
}

export interface UpsertModelCapabilitiesBody {
  capabilities?: ModelCapability[];
  tags?: ModelTag[];
  display_name?: string | null;
  notes?: string | null;
  persona: Persona;
}

export interface PingModelRequest {
  model_id: string;
  provider: string;
  persona?: Persona;
}

export interface PingModelResponse {
  reachable: boolean;
  model_id: string;
  provider: string;
  error: string | null;
}

export interface ImageGenRequest {
  prompt: string;
  model: string;
  size?: string;
  quality?: string;
  n?: number;
}

export interface ImageGenResponse {
  images: string[];  // data URIs or URLs
  model: string;
  provider: string;
}

export interface SkillResponse {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
}

export interface ContextEntryResponse {
  id: string;
  title: string;
  content: string;
  category: string | null;
  subcategory: string | null;
  source_type: "manual" | "session" | "archive";
  source_id: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CreateContextEntryBody {
  title: string;
  content: string;
  category?: string | null;
  subcategory?: string | null;
  source_type?: "manual" | "session" | "archive";
  source_id?: string | null;
}

export interface UpdateContextEntryBody {
  title?: string;
  content?: string;
  category?: string | null;
  subcategory?: string | null;
  is_active?: boolean;
}

export interface ToolEvent {
  name: string;
  args?: Record<string, unknown>;
  result?: unknown;
  status: "calling" | "done";
}

export interface ReactStep {
  iteration: number;
  tools: { name: string; arg_preview: string }[];
}

export type ChatChunk =
  | { type: "token"; data: string }
  | { type: "reasoning"; data: string }
  | { type: "neural_context"; data: unknown[] }
  | { type: "tool_call"; data: { name: string; args: Record<string, unknown> } }
  | { type: "tool_result"; data: { name: string; result: unknown } }
  | { type: "react_step"; data: { iteration: number; tools: { name: string; arg_preview: string }[] } }
  | { type: "correction"; data: string }
  | { type: "done"; data: { message_id?: string; model?: string; tokens_in?: number; tokens_out?: number; citations?: string[] } }
  | { type: "error"; data: { code: string; message: string } };

// ── Agent Runs (Phase 3) ───────────────────────────────────────────────────────

export interface CreateRunRequest {
  goal: string;
  title: string;
}

export interface RunResponse {
  id: string;
  title: string;
  goal: string;
  status: string;
  created_at: string;
}

export interface AgentRunEvent {
  type: string;
  status?: string;
  message?: string;
  run_id?: string;
  timestamp?: string;
}
