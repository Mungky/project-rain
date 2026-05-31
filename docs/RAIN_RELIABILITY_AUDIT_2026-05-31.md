# Rain — Audit Keandalan & Rencana Perbaikan Bertahap

**Tanggal:** 2026-05-31
**Konteks:** User melaporkan Rain "tidak bisa diandalkan" — cari di web gagal, analisis file gagal, jawaban sering ngaco. Target jangka panjang: Rain jadi asisten pribadi sejati (mentor, teman, antisipatif), bukan sekadar "tahu segalanya".
**Fokus model:** Cloud Ollama (`glm-5.1:cloud`, `kimi-k2.6:cloud`, `gemma4:31b-cloud`).

---

## Ringkasan Eksekutif

Masalah Rain **bukan kecerdasan model** — tapi **fondasi yang rusak** yang membuat model bagus pun tampak bodoh. Lima akar masalah berikut sudah diverifikasi langsung di kode (bukan dari memory lama):

| # | Masalah | Dampak yang dirasakan user | Severity |
|---|---------|----------------------------|----------|
| A1 | Nama tool tidak cocok antara prompt & registry | "Cari di web gak bisa", "python gak jalan" | 🔴 Kritis |
| A2 | File biner (PDF/DOCX/XLSX) dikirim sebagai base64 mentah, tanpa ekstraksi teks | "Analisis file gak bisa / ngaco" | 🔴 Kritis |
| A3 | Protokol tool lewat XML rapuh untuk model cloud | Tool kadang jalan kadang tidak | 🟠 Tinggi |
| A4 | Self-correction memotong jawaban di 500 token | "Jawaban kepotong / jadi aneh" | 🟡 Sedang |
| A5 | Memory & ekstraksi pakai model lemah yang sama | "Catatan/ingatannya ngawur" | 🟡 Sedang |

**Kesimpulan:** Banyak fondasi visi besar Anda **sudah ada** (ekstraksi konteks tiap turn, RAG, few-shot, "critical friend role", self-correction). Semua runtuh karena A1–A3. **Urutan benar: perbaiki fondasi → keandalan → kualitas → memory → kepribadian → proaktif.**

---

## Bagian A — Akar Masalah (Terverifikasi)

### A1 — Nama tool tidak cocok (penyebab utama "search/file/python gak bisa") 🔴

- Registry mengekspos nama tool sebagai **nama folder persis**: `web-search-searxng`, `python-executor`, `web-reader`, `document-search`, `read_file`, `create_file`, `str_replace_editor` (`skill_service.py:67`).
- Tapi prompt persona **Storm** menyuruh model memanggil `web_search` dan `python_executor` (`prompt_templates.py:210,212,223-228`) — nama yang **tidak ada** di registry.
- Eksekutor mencocokkan **nama folder persis** (`executor.py:33-38`). Kalau model emit `<invoke name="web_search">` → `{"error": "Skill 'web_search' not found"}` dikembalikan diam-diam → model mengarang jawaban atau menyerah.
- Tidak ada alias / fuzzy-matching / normalisasi nama sama sekali.

**Bukti:** `chat_mode.py:920-936` (allowlist pakai nama benar) vs `prompt_templates.py:210` (`web_search("X")`), vs `executor.py:37-38` (lookup folder persis).

### A2 — Analisis file rusak total untuk dokumen biner 🔴

- Composer menerima `.pdf .docx .doc .xlsx .xls .pptx .ppt` (`composer.tsx:59-64`).
- Untuk dokumen biner, file dibaca sebagai **base64** (`composer.tsx:108-118`, `reader.readAsDataURL`).
- Backend menyuntikkan `content` itu apa adanya ke prompt sebagai blok "teks" (`chat_mode.py:623-631`) — jadi model menerima **string base64 acak**, bukan isi dokumen.
- **Tidak ada ekstraksi teks** PDF/Office di backend (tidak ada PyPDF / pdfplumber / python-docx / openpyxl di dependency — diverifikasi via grep).
- Hanya `.txt / .md / .csv` yang benar terbaca (jalur `file.text()`, `composer.tsx:119-122`).
- Catatan: skill `read_file` (`read_file/handler.py`) **hanya** membaca folder `workspace`, **bukan** file yang di-upload user — jadi bukan solusi untuk attachment.

### A3 — Protokol tool-call lewat XML rapuh untuk model cloud 🟠

- Semua model Ollama dipaksa lewat jalur teks XML `<function_calls>` (`chat_mode.py:962-994`); tools JSON native **sengaja dikosongkan** (`tools = []`, line 993-994) karena dulu native gagal diam-diam.
- Parser XML (`ollama.py:11-20`) menuntut format `<invoke name="...">` + `<parameter name="...">` persis. Model cloud (glm/kimi/gemma) sering: bungkus dalam ```` ```xml ````, salah ketik tag, atau tidak emit sama sekali.
- Tidak ada: retry/repair saat parsing gagal, *forced tool use* saat user jelas minta "cari di web", maupun deteksi "model gagal panggil tool padahal harus".
- `glm-5.1:cloud` adalah thinking-model — kepatuhan emit XML-nya memang sudah diragukan di QA audit 2026-05-27.

### A4 — Self-correction memotong jawaban 🟡

- Pass evaluasi mandiri (`chat_mode.py:1485-1530`) jalan untuk Storm + bila `self_correction_enabled`.
- Dibatasi `max_tokens=500` (line 1507). Jawaban panjang yang **benar** bisa terpotong → koreksi malah lebih buruk.
- Heuristik "OK vs revisi" rapuh (`> 150 char` dianggap revisi, line 1525) → bisa salah ganti jawaban bagus dengan potongan.

### A5 — Memory & pembelajaran terhambat model lemah 🟡

- Ekstraksi konteks tiap turn (`_extract_context_background`, `chat_mode.py:97-225`) & judul & few-shot semuanya pakai `glm-5.1:cloud` / model Ollama pertama yang tersedia.
- Kalau model lemah → ringkasan yang disimpan ke knowledge base ngawur → RAG menyuntik konteks buruk → jawaban makin ngaco (lingkaran setan).
- Arsitektur memory-nya **bagus** (Qdrant dedup via cosine 0.82, kategori, update vs create). Bottleneck-nya kualitas model ekstraksi + tidak ada review/koreksi entri.

---

## Bagian B — Rencana Bertahap

Setiap fase berdiri sendiri & bisa dipilih terpisah. Estimasi = waktu kerja kasar. Saya rekomendasikan urut Fase 0 → 6.

### Fase 0 — Quick Wins (≈ 1–2 jam) ⚡ paling tinggi ROI

**Tujuan:** Hentikan kebocoran paling konyol tanpa ubah arsitektur.

1. **Samakan nama tool di prompt dengan registry** (`prompt_templates.py`): ganti `web_search`→`web-search-searxng`, `python_executor`→`python-executor`, dst. Atau lebih baik: hapus nama hardcoded dari prelude, biarkan hanya blok `AVAILABLE TOOLS` (`chat_mode.py:975`) yang jadi sumber kebenaran tunggal.
2. **Alias + normalisasi nama tool di eksekutor** (`executor.py`): map `web_search`/`search`/`web-search`→`web-search-searxng`, `python`/`code`→`python-executor`, dll. Normalisasi `-`/`_` sebelum lookup. Ini jaring pengaman walau model salah nama.
3. **Naikkan `max_tokens` self-correction** (`chat_mode.py:1507`) jadi mengikuti panjang jawaban asli (mis. `max(len_asli*1.3, 1500)`), atau matikan untuk jawaban panjang.

**Verifikasi:** kirim "cari berita AI terbaru hari ini" di persona Drizzle → tool `web-search-searxng` terpanggil & hasil muncul. Cek log `Executing skill:`.

### Fase 1 — Keandalan Tool-Calling Cloud Ollama (≈ 1–2 hari) 🔴

**Tujuan:** Tool jalan ~100%, bukan kadang-kadang.

1. **Uji native tool-calling Ollama Cloud sekarang** — Ollama sudah jauh membaik. Bila glm/kimi/gemma patuh native JSON tools, ganti jalur XML → native (jauh lebih andal). Buat eksperimen kecil sebelum komit.
2. **Forced tool use untuk intent eksplisit** — kalau `detect_task_type`/`detect_tag` = research atau user tulis "cari/search/terbaru/berita", paksa minimal 1 panggilan `web-search-searxng` sebelum boleh menjawab.
3. **Repair loop saat parsing gagal** — bila respons mengandung kata kunci tool tapi XML rusak, kirim ulang dengan instruksi format yang lebih tegas (1x retry).
4. **Toleransi parser XML** (`ollama.py:_parse_xml_tool_calls`): terima `'`/`"`, abaikan code-fence, parse nama yang dinormalisasi.
5. **Tampilkan kegagalan tool ke user** alih-alih diam — kalau search gagal 2x, beri tahu "pencarian web sedang bermasalah" bukan mengarang.

**Verifikasi:** 10 query riset berbeda → semua memicu search & mengutip sumber. Catat success rate sebelum/sesudah.

### Fase 2 — Analisis File Beneran (≈ 1 hari) 🔴

**Tujuan:** Upload PDF/DOCX/XLSX → benar-benar dianalisis.

1. **Ekstraksi teks server-side** di backend sebelum inject ke prompt: `pypdf`/`pdfplumber` (PDF), `python-docx` (DOCX), `openpyxl` (XLSX), `python-pptx` (PPTX). Tambah ke dependency rain-api.
2. Di `chat_mode.py:622-631`: untuk attachment non-image, deteksi mime → ekstrak teks → inject teks bersih (bukan base64). Fallback: kalau gagal ekstrak, beri tahu user jujur.
3. **Chunk + index ke Qdrant** untuk file besar (RAG atas dokumen) sehingga bisa tanya-jawab dokumen panjang tanpa kebanjiran token.
4. (Opsional) OCR untuk PDF hasil scan (`pytesseract`) — fase lanjutan.

**Verifikasi:** upload PDF 5 halaman → "ringkas dokumen ini" → ringkasan akurat, bukan "saya tidak bisa membaca".

### Fase 3 — Kualitas Jawaban & Evaluasi Tiap Jawaban (≈ 1–2 hari) 🟡

**Tujuan:** "Setiap jawaban dievaluasi" — beneran, bukan asal.

1. **Perbaiki self-correction** (lanjutan A4): kriteria revisi berbasis rubrik (akurasi faktual, jawab pertanyaan?, ada klaim tak terverifikasi?), bukan sekadar panjang.
2. **Critic pass terpisah** (opsional, untuk Storm): model kedua menilai jawaban sebelum dikirim; revisi hanya bila skor < ambang.
3. **Grounding check**: bila jawaban mengandung klaim faktual 2025/2026 tanpa hasil search → tandai/paksa verifikasi.
4. **Konsistensi format** sudah diatur di Storm prelude — pindahkan aturan inti ke validator output (cek code-block seimbang) agar tak bergantung kepatuhan model.

**Verifikasi:** set pertanyaan faktual jebakan → ukur berapa yang ketangkap & dikoreksi.

### Fase 4 — Memory yang Benar-Benar Belajar (≈ 1–2 hari) 🟡

**Tujuan:** "Setiap hal baru tercatat" dengan kualitas tinggi.

1. **Pisahkan model ekstraksi** dari model chat — pakai model paling patuh-instruksi yang tersedia, atau Claude/GPT bila nanti ada key, khusus untuk ekstraksi (volume kecil, dampak besar).
2. **Review entri memory**: pass kecil yang membuang entri duplikat/sampah; gabungkan entri serupa (sudah ada dedup 0.82, perkuat).
3. **Memory berlapis**: profil user (Neural Baseline) vs fakta proyek vs preferensi — sudah ada strukturnya, rapikan agar yang relevan saja yang disuntik.
4. **Recall yang lebih tajam**: naikkan kualitas embedding query, tambah re-ranking sederhana.

**Verifikasi:** ceritakan 5 fakta personal lintas sesi → sesi berikut Rain ingat & pakai dengan benar.

### Fase 5 — Kepribadian Asisten: Mentor & Teman (≈ 2–3 hari) 🟢 visi

**Tujuan:** Bukan "tahu segalanya", tapi asisten pribadi.

1. **Persona "mentor"**: mode yang mengajari bertahap (Socratic), melacak progres belajar Anda di memory, menyesuaikan kedalaman ke level Anda.
2. **Mode "teman/support"**: nada empatik saat Anda down — tanpa toxic positivity; sudah ada bibitnya di "critical friend role".
3. **Profil tujuan profesional**: simpan bidang yang ingin Anda kuasai → Rain proaktif memberi latihan, koreksi, jalur belajar.
4. **Adaptasi gaya** berbasis Neural Baseline (panjang jawaban, bahasa, tingkat teknis).

**Verifikasi:** sesi belajar topik baru → Rain ajari bertahap, ingat sampai mana, lanjut di sesi berikutnya.

### Fase 6 — Proaktif & Antisipasi Kelemahan (≈ 2–3 hari) 🟢 visi

**Tujuan:** "Mengantisipasi kelemahan saya", "bisa diandalkan untuk kerja".

1. **Deteksi pola kelemahan** dari riwayat (mis. sering lupa langkah X, sering keliru di topik Y) → simpan ke memory → ingatkan proaktif.
2. **Scheduled check-ins** (pakai `/schedule` atau cron) — review harian/mingguan, ingatkan tugas, follow-up hal yang menggantung.
3. **Antisipasi di tengah tugas**: sebelum Anda salah, Rain flag risiko ("biasanya di sini kamu lupa commit/migrasi").
4. **Mode kerja**: integrasi dengan tugas nyata (file proyek, todo, deadline yang tersimpan).

**Verifikasi:** Rain memunculkan pengingat/antisipasi relevan tanpa diminta, akurat ≥ sekian%.

---

## Rekomendasi Urutan Eksekusi

1. **Fase 0** dulu — 1-2 jam, langsung memperbaiki keluhan "search/file/python gak bisa" sebagian besar.
2. **Fase 1 + 2** — bikin tool & file analysis benar-benar andal (ini inti keluhan).
3. **Fase 3 + 4** — kualitas jawaban & memory (fondasi untuk visi).
4. **Fase 5 + 6** — bangun kepribadian mentor/teman/proaktif di atas fondasi yang sudah kokoh.

**Catatan model:** Karena fokus Cloud Ollama, batas atas keandalan tetap dibatasi kepatuhan model. Bila suatu saat Anda buka 1 API key Claude/GPT **khusus untuk jalur tool-calling + ekstraksi memory** (volume kecil, murah), lompatan keandalannya besar. Ini opsional, bukan prasyarat.
