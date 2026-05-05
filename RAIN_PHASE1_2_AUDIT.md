# 🌧️ Laporan Deep Audit: Project Rain (Fase 1 & Fase 2)
**Tanggal Audit:** 28 April 2026
**Fase Saat Ini:** Transisi menuju Fase 3 (Work Mode & Orchestration)

---

## 1. Visi & Filosofi Utama
Project Rain adalah **Local AI Operating System** yang dirancang untuk menyaingi model raksasa (seperti Claude Opus atau Gemini Ultra) bukan dengan ukuran model yang lebih besar, melainkan melalui arsitektur orkestrasi yang cerdas. 

**Batasan Perangkat Keras (Hardware Target):**
*   **Target:** RTX 3050 Mobile / 4GB VRAM / 16GB RAM.
*   **Strategi:** Menyisakan ruang VRAM (Max 3.5GB untuk LLM tunggal), menggunakan model kecil yang efisien (seperti `kimi-k2.6:cloud`, Llama 3 8B, atau Ollama custom), dan *embedder* berbasis CPU (`nomic-embed-text` ~300MB).

**Core Thesis:** 
*Sebuah model lokal 3B, apabila diorkestrasi dengan baik (RAG presisi, kritik/revisi berulang, dan ekosistem *skill* otonom), dapat mengalahkan model API berparameter 200B dalam tugas-tugas terstruktur.*

---

## 2. Tech Stack (Teknologi yang Digunakan)

### Frontend (UI/UX)
*   **Framework Utama:** Next.js 16 (App Router) + React 19.1.0
*   **Styling & UI:** Tailwind CSS 4, Framer Motion (Animasi *fluid*), Lucide React (Ikon), `clsx` & `tailwind-merge`.
*   **State Management:** Zustand (State lokal/UI), TanStack React Query v5 (Data *fetching* & *caching* sinkronisasi server).
*   **Markdown & Render:** `react-markdown`, `react-syntax-highlighter`, `rehype-katex`, `remark-math` (Rendering LaTeX dan kode).
*   **API Client:** `openapi-typescript` untuk *generate* tipe TS langsung dari FastAPI OpenAPI secara otomatis.

### Backend (Orkestrasi & API)
*   **Framework Utama:** Python 3.11+, FastAPI (Backend REST & SSE API).
*   **Server:** Uvicorn (ASGI server).
*   **Validasi & Skema:** Pydantic v2 (Input/Output API), Pydantic Settings (Environment variables).
*   **LLM Providers:** `ollama`, `anthropic`, `openai`, `google-generativeai`. (Diatur lewat layer Abstraksi Adapter).
*   **Data Processing & Parsers:** `pypdf`, `python-docx`, `pandas`, `openpyxl`.
*   **Observability:** `langfuse` (Terintegrasi untuk *tracing* langkah-langkah agen).

### Database & Infrastruktur (Tri-DB + MinIO)
Semua dijalankan melalui `docker-compose.yml` terpusat, dengan limitasi RAM yang dikontrol ketat untuk menunjang mesin *low-end*:
*   **PostgreSQL 16 (Alpine):** *Single source of truth* untuk relasi data (Metadata, percakapan, preferensi user, registrasi *skill*). Dikelola menggunakan SQLAlchemy 2.0 (Async) dan Alembic (Migrations).
*   **Redis 7 (Alpine):** *State management* cepat (Caching, antrean).
*   **Qdrant:** *Vector database* untuk RAG (Koleksi `documents` dan `context_library`), menggunakan *Cosine similarity* dengan *int8 quantization* untuk menghemat RAM.
*   **MinIO:** *Object storage* skala lokal (menyimpan file mentah yang di-*upload* user untuk RAG atau artefak *skill*).
*   **SearXNG:** *Self-hosted meta-search engine* (berjalan di port 8080) yang menyatukan hasil Google, Bing, Wikipedia secara anonim untuk digunakan oleh *skill* web-search.

---

## 3. Struktur Direktori & "Jahitan" Sistem (Stitching)

Proyek ini menggunakan struktur **Monorepo** yang dipisah secara konseptual berdasarkan tanggung jawab *Agent Developer*:

```text
/ (Root)               → Dipegang oleh "Parent Agent" (Orkestrator Build)
├── backend/           → Dipegang oleh "Backend Agent" (Logika Python, LLM)
├── db/                → Dipegang oleh "DB Agent" (Skema, Migrasi, Docker)
├── frontend/          → Dipegang oleh "Frontend Agent" (Next.js, UI)
└── skills_registry/   → Repositori *skill* modular yang bisa dipasang/dicopot
```

**Bagaimana Mereka Terhubung (The Stitching):**
1.  **Backend ↔ DB:** Backend terhubung ke PostgreSQL menggunakan SQLAlchemy Async (`asyncpg`). Model Pydantic dan Model SQLAlchemy dipisahkan dengan rapi. Migrasi ditangani secara independen oleh Alembic di dalam folder `/db`.
2.  **Backend ↔ Frontend:** Menggunakan HTTP/REST standard. Khusus untuk interaksi LLM, digunakan metode **Server-Sent Events (SSE)**. Data yang mengalir via SSE dibungkus dalam JSON (seperti `type: "token"`, `type: "tool_call"`, `type: "reasoning"`, `type: "done"`).
3.  **Type Safety Sepanjang Jalur:** Frontend *tidak* menulis tipe API secara manual. Mereka menggunakan `openapi:gen` yang membaca *schema* dari Backend FastAPI dan menghasilkan `api-types.ts`.
4.  **Sandbox Skill:** Skrip `skills.sh` menjahit ekosistem *skill* (seperti ekstensi). Setiap *skill* memiliki `manifest.yaml` dan dieksekusi di *sandbox* (subprocess).

---

## 4. Fitur yang Telah Dibangun & Diselesaikan

### Fase 1: Walking Skeleton (Terselesaikan)
*   **Core Chat Engine:** Interaksi *chat* dasar menggunakan Ollama lokal dengan persistensi percakapan ke PostgreSQL.
*   **SSE Streaming Engine:** Aliran *token* dari LLM ke UI langsung dan reaktif.
*   **Visual Identity:** UI bergaya *glassmorphism*, warna *deep blue/slate* yang bersih.

### Fase 2: Memory & Skills (Terselesaikan & Diperluas)
*   **Sistem RAG Terintegrasi:** Pipa dokumen lengkap. `Upload Dokumen -> MinIO -> Chunking (512 token) -> Embed (Ollama/Nomic) -> Qdrant`. Frontend mendapat tab `Workshop` untuk mengatur ini.
*   **Ekosistem Skill & Executor:** `skills.sh` telah berjalan. 3 *skill* bawaan aktif: `web-search-searxng`, `web-reader`, dan `python-executor` (dengan batasan *timeout* 30 detik untuk *sandbox*).
*   **Sistem Memori Proaktif (Context Library):** 
    *   Fitur ekstraksi memori latar belakang (*background extraction*). Rain mengingat percakapan penting secara otomatis di belakang layar.
    *   Tersedia alat bawaan `update_user_memory` dan `save_context_entry`.
*   **Multi-Provider LLM:** Sistem tak lagi terikat hanya pada Ollama. Dukungan API Anthropic (Claude 3.5), OpenAI (GPT-4o), dan Google (Gemini 1.5/2.0) sudah terpasang rapi lewat antarmuka *Adapter*. Manajemen API Key aman di UI.
*   **ReAct Loop Engine:** Backend mampu melakukan *looping* untuk memanggil *tools*, mengevaluasi hasilnya, dan memutuskan untuk merespons atau menggunakan *tool* lain (hingga batas iterasi maksimal 8 kali).
*   **UI/UX Polish:** Blok "Thinking" interaktif, manajemen batas token, tombol salin, panel pengaturan dinamis.
*   **Fitur Observabilitas:** Terhubung dengan *Langfuse* untuk merekam *tracing* multi-agen (berguna untuk *debugging*).
*   **Sistem Ketahanan Tinggi (Resilience):** Sistem kini memiliki pemetaan temperatur pintar berdasarkan tugas (*detect_task_type*), limit token yang luas (*8192 token* untuk respons komprehensif), dan **Fallback Otomatis** (jika Ollama *overload*/mengembalikan kode 503, *backend* otomatis me-*retry* pesan dengan model cadangan dari penyedia lain atau lokal).

---

## 5. Arsitektur Agen Saat Ini

Saat berada di dalam sesi *chat*, Rain menggunakan siklus **ReAct (Reason + Act)**:
1.  **Evaluasi Router:** Menggunakan `model_router.py` untuk memilih model yang paling tepat berdasarkan tipe *prompt* pengguna (apakah ada gambar? Apakah panjang historinya? dsb).
2.  **Prompt Injeksi:** Menyuntikkan preferensi kustom pengguna + entri *Knowledge Base* (Context Library) yang aktif ke dalam System Prompt.
3.  **Eksekusi Loop (Maks. 8x):**
    *   Agen mulai *streaming* respons.
    *   Jika menemui pemanggilan *skill* (`tool_call`), sistem menghentikan *streaming* teks ke UI, menjalankan skrip Python *skill* tersebut, mendapatkan hasil (misal: JSON hasil *search* web), lalu menyuntikkannya ke *array message* dan memancing LLM merespons kembali dengan hasil yang didapat.
4.  **Self-Correction (Disabled in Chat, Prep for Phase 3):** Memiliki logika pengoreksi diri (*Critic*) untuk menilai ulang jawabannya secara tertutup sebelum dikembalikan ke *user*.

---

## 6. Persiapan Transisi ke Fase 3 (Work Mode & Orchestration)

Platform utama telah terbukti sangat stabil (API, LLM Streaming, RAG, Integrasi Tools, dan Database semuanya solid). Pondasi ini siap diinjak untuk Fase 3.

**Yang Akan Dibangun di Fase 3:**
1.  **Work Mode:** Beralih dari *Chat* 1-on-1 menjadi *Dashboard* Multi-Agen.
2.  **Skema AgentRun:** DB Agent harus membuat tabel status `pending`, `running`, `completed`, `failed` untuk melacak pekerjaan panjang.
3.  **Hierarki Agen:** Sistem *planner* yang memecah *prompt* menjadi *sub-task* (Survey -> Architect -> Implementor -> Critic).
4.  **UI Canvas/Graph:** Menggunakan `React Flow` di frontend untuk memvisualisasikan bagaimana agen bekerja sama, saling mengoper data (*ground truth*), dan membangun aplikasi otonom.

---
**Status Audit Final:** Sistem Fase 1 & 2 telah **SELESAI DENGAN SANGAT BAIK DAN MELEBIHI EKSPEKTASI**. Arsitektur sangat rapi (*loose coupling, tight cohesion*), aman dari *breaking changes*, dan sangat modular. Siap dilanjutkan ke Fase 3.