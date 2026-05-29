"""
Seed Drizzle's Brain with foundational domain knowledge via the Rain API.

5 domains: Business Development, Finance, Technology, Investment, AI Technology
Strategy:
  - is_active=True  → always injected in system prompt (domain anchors, 1 per domain)
  - is_active=False → Qdrant-only, retrieved via semantic search when relevant

Usage:
    # While Rain API is running (Docker):
    cd apps/rain-api
    python scripts/seed_knowledge.py

    # Custom API URL or token:
    RAIN_API_URL=http://localhost:8000 RAIN_API_TOKEN=xxx python scripts/seed_knowledge.py

    # Dry run (no changes):
    python scripts/seed_knowledge.py --dry-run
"""

import asyncio
import os
import sys
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ── Knowledge entries ─────────────────────────────────────────────────────────
# (title, content, category, subcategory, is_active)
# content < 400 chars — dense, specific, actionable
# is_active=True  → always in Drizzle's system prompt (max 5 per session)
# is_active=False → RAG-only, pulled in when semantically relevant

KNOWLEDGE: list[tuple[str, str, str, str, bool]] = [

    # ════════════════════════════════════════════════════════════════════
    # BUSINESS DEVELOPMENT
    # ════════════════════════════════════════════════════════════════════

    (
        "BD Framework: GTM Archetypes",
        "Startup GTM: 3 archetypes — (1) Product-led: product drives signup+upgrade (Slack, Notion, Figma); "
        "(2) Sales-led: outbound/enterprise (Salesforce); (3) Community-led: community drives discovery (dbt, Hashicorp). "
        "Most B2B startups start sales-led, shift to product-led at scale when NRR > 100%.",
        "Market", "Business Development", True,   # ANCHOR: always in system prompt
    ),
    (
        "Unit Economics: CAC & LTV Formulas",
        "CAC = total sales+marketing spend / new customers acquired. "
        "LTV = (avg monthly revenue per customer × gross margin%) / monthly churn rate. "
        "Healthy SaaS: LTV:CAC ≥ 3:1, CAC payback ≤ 12 months. "
        "LTV:CAC < 1 = unsustainable growth. NRR > 100% = growth without new customers.",
        "Market", "Business Development", False,
    ),
    (
        "Indonesia B2B Business Development Dynamics",
        "Indonesia B2B: warm intro > cold outreach 5-10x. Enterprise: procurement + IT + finance triple sign-off, "
        "cycle 3-9 months. SME: owner-led decision, 1-4 weeks. Government: e-katalog/LKPP procurement, budget cycle Dec-Jan. "
        "BUMN partnership unlocks gov contracts. Telco partnership unlocks SME distribution.",
        "Market", "Business Development", False,
    ),
    (
        "Growth Loops vs Funnels",
        "Loops compound, funnels don't. Types: (1) Viral — user invites user (WhatsApp, Zoom); "
        "(2) Content — user content attracts users (YouTube, TikTok); (3) Paid — revenue funds ads (D2C). "
        "Identify natural loop before scaling paid. No loop = acquisition treadmill. "
        "Strong loop = CAC drops as scale increases.",
        "Market", "Business Development", False,
    ),
    (
        "Product-Market Fit Signals",
        "PMF signals: (1) 40% rule — 40%+ users say 'very disappointed' if product disappeared (Sean Ellis test); "
        "(2) Organic word-of-mouth without paid; (3) NRR > 100%; (4) Short sales cycles + low churn. "
        "Without PMF, scaling = pouring money into a leaky bucket. "
        "Pivot signals: < 10% 40% rule score, high churn, long sales cycles.",
        "Market", "Business Development", False,
    ),
    (
        "Partnership Models for Indonesian Startups",
        "Partnership types: (1) Channel/reseller — partner sells for 20-40% commission; "
        "(2) Tech integration — API/embedded; (3) Co-marketing — shared audience, joint campaigns; (4) OEM — white-label. "
        "Indonesia-specific: BUMN partnerships unlock gov sector; "
        "Tokopedia/Shopee/Blibli seller networks unlock SME reach; telco (Telkom, XL) bundles unlock rural distribution.",
        "Market", "Business Development", False,
    ),

    # ════════════════════════════════════════════════════════════════════
    # FINANCE
    # ════════════════════════════════════════════════════════════════════

    (
        "Startup Finance: Key Metrics Overview",
        "Startup finance essentials: Runway = cash / monthly net burn (target ≥ 18 months). "
        "Gross margin = (revenue - COGS) / revenue (SaaS target > 70%). CAC payback ≤ 12 months. "
        "MRR growth > 10%/month early stage. Rule of 40: growth% + profit margin% ≥ 40 at scale. "
        "Track weekly. Cash is oxygen.",
        "Market", "Finance", True,   # ANCHOR
    ),
    (
        "P&L Structure for Startups",
        "P&L: Revenue - COGS = Gross Profit (→ Gross Margin%). Gross Profit - OpEx (S&M + R&D + G&A) = EBITDA. "
        "EBITDA - D&A = EBIT. EBIT - Interest - Tax = Net Income. "
        "SaaS COGS: hosting, payment processing, customer support. "
        "Focus early: maximize gross margin%, minimize burn per unit of growth.",
        "Market", "Finance", False,
    ),
    (
        "Burn Rate & Runway Calculation",
        "Gross burn = total monthly cash spend. Net burn = gross burn - revenue collected. "
        "Runway = cash balance / net burn. Default dead = date cash runs out at current trajectory. "
        "Healthy seed: net burn < $80-150K/month. Healthy Series A: < $300K/month. "
        "Raise when runway > 12 months (not when desperate — distressed valuation follows).",
        "Market", "Finance", False,
    ),
    (
        "Startup Valuation Methods",
        "Valuation: (1) ARR multiple — SaaS 5-15x ARR (2024, down from 20-30x peak 2021); "
        "(2) Berkus — up to $500K per milestone (pre-revenue only); (3) Comparable — similar funded peers; "
        "(4) DCF — rare pre-Series B. Indonesia benchmarks: pre-seed $1-3M, seed $3-10M, Series A $10-30M. "
        "Series A typical: 3-8x ARR multiple.",
        "Market", "Finance", False,
    ),
    (
        "Indonesia Tax for Startups (PT)",
        "PT tax: PPh Badan 22% standard; revenue ≤ 4.8B IDR: PP 23 option (0.5% of revenue, final). "
        "PPN 11% on taxable goods/services; PKP registration mandatory when revenue > 4.8B IDR/year. "
        "ESOP: taxed at exercise event (PPh 21 progressive). Dividen ke WNI: PPh final 10%. "
        "e-SPT for annual filing, e-Faktur for PPN invoicing.",
        "Market", "Finance", False,
    ),
    (
        "SaaS Financial Ratios & Benchmarks",
        "Key SaaS metrics: MRR churn < 2% = excellent, < 5% = acceptable. "
        "NRR (net revenue retention) > 100% = expansion > churn. "
        "Magic number = new ARR / prior quarter S&M spend (> 0.75 = efficient growth). "
        "Quick ratio = (new MRR + expansion MRR) / (churned + contraction MRR) > 4 = healthy. "
        "ARPU = MRR / active customers.",
        "Market", "Finance", False,
    ),

    # ════════════════════════════════════════════════════════════════════
    # TECHNOLOGY
    # ════════════════════════════════════════════════════════════════════

    (
        "Modern Tech Stack 2025",
        "Startup stack: Frontend — Next.js 14+ (web), React Native/Expo (mobile). "
        "Backend — FastAPI/Python (AI-heavy) or Node.js/Hono (lean APIs). "
        "DB — PostgreSQL (primary), Redis (cache/queue), Qdrant (vectors). "
        "Infra — Docker + Coolify/Railway (early stage), AWS/GCP (at scale). "
        "AI — Claude Sonnet (quality+reasoning), Gemini Flash (speed/cost), Llama 3.3 (local).",
        "Technical", "Technology", True,   # ANCHOR
    ),
    (
        "Monolith vs Microservices Decision",
        "Start monolith. Split only when: (1) team > 8 engineers; (2) different scaling profiles per domain; "
        "(3) different deploy cadences; (4) clear bounded contexts. "
        "Microservices pre-$1M ARR = coordination overhead kills velocity. "
        "Anti-pattern: distributed monolith (microservices with tight coupling). "
        "Modular monolith = best middle ground before true microservices.",
        "Technical", "Technology", False,
    ),
    (
        "Database Selection Guide",
        "DB selection: PostgreSQL = default (relational, ACID, JSON, handles 80% of cases). "
        "MongoDB = flexible schema, document model. Redis = cache, sessions, pub/sub, rate limiting. "
        "ClickHouse = analytics/OLAP. Qdrant/Pinecone = vector similarity. "
        "pgvector = vectors inside Postgres (good for < 1M vectors). "
        "Rule: don't add a new DB unless PostgreSQL provably can't do it.",
        "Technical", "Technology", False,
    ),
    (
        "API Design Principles",
        "REST for CRUD, GraphQL for nested/complex queries, gRPC for internal microservices (faster serialization). "
        "REST versioning: /v1/ prefix, never break existing clients. "
        "Pagination: cursor-based > offset for large/real-time datasets. "
        "Rate limiting: token bucket per API key (100 req/min baseline). "
        "Auth: JWT (stateless) or session cookie (stateful, simpler). "
        "Error format: {code, message, details} always structured.",
        "Technical", "Technology", False,
    ),
    (
        "Scalability Patterns",
        "Scaling order of operations: (1) Caching — Redis hot data, CDN static (biggest wins, cheapest); "
        "(2) Async queues — offload heavy jobs (Celery, BullMQ, Redis Queue); "
        "(3) Vertical scaling — bigger server (fast, limited); "
        "(4) DB read replicas; (5) Horizontal — load balancer + stateless servers. "
        "Don't optimize until you've measured the bottleneck. Premature optimization wastes 60-80% of engineering.",
        "Technical", "Technology", False,
    ),
    (
        "Security Essentials for Web Apps",
        "OWASP Top 10 mitigations: SQL injection → parameterized queries only. "
        "XSS → Content-Security-Policy + sanitize user input. Auth bugs → short JWT TTL + refresh tokens. "
        "IDOR → verify resource ownership server-side for every request. "
        "Secrets → env vars + vault, never in code or git. "
        "HTTPS everywhere. Rate limit auth endpoints (5 attempts / 15 min). Log all auth events.",
        "Technical", "Technology", False,
    ),

    # ════════════════════════════════════════════════════════════════════
    # INVESTMENT
    # ════════════════════════════════════════════════════════════════════

    (
        "Startup Funding Stages Overview",
        "Stages: Pre-seed ($100K-500K, idea/MVP, angels); Seed ($500K-3M, early traction, micro-VCs); "
        "Series A ($3-15M, PMF proven, institutional VCs); Series B ($15-50M, scaling model); "
        "Series C+ ($50M+, expansion/dominance). Dilution per round: 15-25% typical. "
        "Indonesia Series A bar: $500K-2M ARR, 2x+ YoY growth, defensible market.",
        "Market", "Investment", True,   # ANCHOR
    ),
    (
        "Indonesia VC Ecosystem 2024-2025",
        "Key VCs: East Ventures (seed-Series A, 100+ portfolio, most active); Sequoia SEA (Series A-B); "
        "Vertex Ventures SEA (Series A-B); MDI Ventures (Telkom-backed, B2B/enterprise); "
        "AC Ventures (early-stage); Intudo Ventures (Indonesia-focus); GDP Venture (media/consumer); "
        "INDICO (Telkomsel CVC). Corporate VCs: GoPay, Grab, DANA. Total VC deployed Indonesia 2023: ~$1.5B.",
        "Market", "Investment", False,
    ),
    (
        "VC Due Diligence Framework",
        "VCs check: (1) Team — founder-market fit, execution history, domain expertise; "
        "(2) Market — TAM/SAM/SOM, growth rate, competitive dynamics; "
        "(3) Product — retention cohorts, NPS, technical moat; "
        "(4) Financials — unit economics, burn efficiency, revenue quality; "
        "(5) Legal — clean cap table, IP ownership, corporate structure. "
        "Red flags: single customer > 30% revenue, missing cap table, 3+ co-founder disputes.",
        "Market", "Investment", False,
    ),
    (
        "Term Sheet Key Terms",
        "Term sheet: Pre-money vs post-money (post = pre + investment). "
        "Liquidation preference: 1x non-participating = standard (investor gets 1x then common participates). "
        "2x participating = harsh on founders. Anti-dilution: weighted average (standard) vs full ratchet (very harsh). "
        "Board: 2 founders + 1 investor at seed = standard. Pro-rata rights = right to invest in future rounds.",
        "Market", "Investment", False,
    ),
    (
        "Cap Table Management",
        "Cap table tracks ownership % of all shareholders. ESOP pool: 10-15% pre-Series A (dilutes founders pre-money). "
        "Dilution: new_% = old_% × (pre-money shares / post-money shares). "
        "Vesting: 4-year vest, 1-year cliff (founders + employees standard). "
        "Uncapped SAFEs with multiple rounds → unexpected heavy dilution at conversion. Use Carta/Pulley.",
        "Market", "Investment", False,
    ),
    (
        "Startup Metrics Investors Track at Each Stage",
        "Seed: MoM growth > 15%, early PMF signals, team quality. "
        "Series A: ARR $500K-2M, 2x+ YoY growth, NRR > 100%, cohort retention. "
        "Series B: ARR $3-10M, efficient growth (burn multiple < 1.5x), market leadership signals. "
        "Burn multiple = net burn / net new ARR. Pipeline coverage: 3x ARR target. CAC payback ≤ 12 months.",
        "Market", "Investment", False,
    ),

    # ════════════════════════════════════════════════════════════════════
    # AI TECHNOLOGY
    # ════════════════════════════════════════════════════════════════════

    (
        "LLM Landscape Mid-2025",
        "Frontier: Claude Opus 4.8 (complex reasoning), GPT-4o (multimodal), Gemini 1.5 Pro (2M context). "
        "Fast/cheap: Claude Haiku 4.5 (~$0.25/M tokens in), Gemini Flash, GPT-4o-mini. "
        "Open-source: Llama 3.3 70B, DeepSeek V3, Qwen2.5. Local: DeepSeek V4 Pro via Ollama. "
        "Best for: coding → Claude; multimodal → GPT-4o/Gemini; long-doc → Gemini Pro.",
        "Technical", "AI Technology", True,   # ANCHOR
    ),
    (
        "RAG Architecture & Best Practices",
        "RAG pipeline: load docs → chunk (512-1024 tokens, 20% overlap) → embed → vector DB. "
        "At query: embed query → similarity search (top-k=4-6) → inject into context → generate. "
        "Hybrid search (dense vector + BM25 keyword) outperforms pure vector search. "
        "Reranking (Cohere, bge-reranker) improves precision. Key metrics: retrieval recall, answer faithfulness.",
        "Technical", "AI Technology", False,
    ),
    (
        "Fine-tuning vs RAG vs Prompting",
        "Choose: Prompting → fast iteration, flexible tasks, no infra. "
        "RAG → factual grounding, updated knowledge, source attribution, reduces hallucination (use when facts matter). "
        "Fine-tuning → consistent format/tone, domain vocabulary, high-volume same-task workloads. "
        "Cost: fine-tuning $50-500 one-time + cheaper inference; RAG = extra latency + infra; prompting = pay per token.",
        "Technical", "AI Technology", False,
    ),
    (
        "AI Product Development Framework",
        "AI product dev checklist: (1) Define input/output contract precisely; "
        "(2) Build eval set (50-200 examples) BEFORE shipping; (3) Escalate: prompting → RAG → fine-tuning; "
        "(4) Latency budget: 2-5s complex, < 1s simple; (5) Cost model: tokens × price × volume × margin; "
        "(6) Monitor in prod: hallucination rate, user corrections, latency p95.",
        "Technical", "AI Technology", False,
    ),
    (
        "Prompt Engineering Techniques",
        "Techniques: (1) Role — 'You are an expert in...'; (2) CoT — 'Think step by step'; "
        "(3) Few-shot — 2-5 examples; (4) Output format — specify exact JSON schema; "
        "(5) Temperature: 0.1-0.3 factual/code, 0.7-1.0 creative; "
        "(6) System = persona+rules, user = task. "
        "Claude: responds best to direct XML-structured prompts with explicit constraints.",
        "Technical", "AI Technology", False,
    ),
    (
        "AI Business Models & Monetization",
        "Models: (1) API-first — sell inference (OpenAI, Anthropic); "
        "(2) AI SaaS — vertical SaaS with AI features (Notion AI, GitHub Copilot, Harvey); "
        "(3) White-label/embedded — license model to enterprises; "
        "(4) Data flywheel — product improves with usage data (Scale AI); "
        "(5) Autonomous agent — per-task billing (AI employee model). "
        "Indonesia 2024-25: B2B vertical AI SaaS most fundable; consumer AI hardest to monetize.",
        "Technical", "AI Technology", False,
    ),
    (
        "LLM Cost Optimization Strategies",
        "Reduce costs: (1) Prompt caching — Anthropic/OpenAI cache system prompts (> 1024 tokens), 90% discount on hits; "
        "(2) Model routing — small model (Haiku/Flash) for simple, large for complex tasks; "
        "(3) Batch API — 50% discount, async processing; (4) Context compression — summarize old messages; "
        "(5) Output caching — cache deterministic responses (same input = same output). "
        "Combined strategy saves 40-70% on LLM spend.",
        "Technical", "AI Technology", False,
    ),
]


async def seed(dry_run: bool = False) -> None:
    """Create all knowledge entries via Rain API."""
    try:
        import httpx
    except ImportError:
        log.error("httpx not installed. Run: pip install httpx")
        sys.exit(1)

    # Try to load .env
    try:
        import dotenv
        env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
        dotenv.load_dotenv(dotenv_path=env_path)
    except ImportError:
        pass

    base_url = os.getenv("RAIN_API_URL", "http://localhost:8000").rstrip("/")
    token = os.getenv("RAIN_API_TOKEN", "")
    headers = {"Authorization": f"Bearer {token}"} if token else {}

    log.info("Target API: %s", base_url)

    if dry_run:
        active = sum(1 for *_, a in KNOWLEDGE if a)
        inactive = sum(1 for *_, a in KNOWLEDGE if not a)
        log.info("DRY RUN — would create %d entries (%d active anchors + %d RAG-only)", len(KNOWLEDGE), active, inactive)
        for title, content, category, subcategory, is_active in KNOWLEDGE:
            status = "ANCHOR" if is_active else "rag   "
            log.info("  [%s] [%-12s / %-22s] %s", status, category, subcategory, title)
        return

    async with httpx.AsyncClient(base_url=base_url, headers=headers, timeout=30) as client:
        # Verify API is reachable
        try:
            r = await client.get("/v1/health")
            r.raise_for_status()
            log.info("API reachable: %s", base_url)
        except Exception as e:
            log.error("Cannot reach Rain API at %s: %s", base_url, e)
            log.error("Make sure Rain is running (docker compose up)")
            sys.exit(1)

        # Fetch existing entries to avoid duplicates
        try:
            r = await client.get("/v1/context", params={"active_only": "false"})
            r.raise_for_status()
            existing_titles = {e["title"] for e in r.json()}
            log.info("Existing entries in Brain: %d", len(existing_titles))
        except Exception as e:
            log.warning("Could not fetch existing entries: %s — proceeding anyway", e)
            existing_titles = set()

        created = skipped = failed = 0

        for title, content, category, subcategory, is_active in KNOWLEDGE:
            if title in existing_titles:
                log.info("  SKIP (exists): %s", title)
                skipped += 1
                continue

            try:
                # Step 1: Create entry (API always creates as active=True)
                r = await client.post("/v1/context", json={
                    "title": title,
                    "content": content,
                    "category": category,
                    "subcategory": subcategory,
                    "source_type": "manual",
                })
                r.raise_for_status()
                entry = r.json()
                entry_id = entry["id"]

                # Step 2: If this should be inactive (RAG-only), update it
                if not is_active:
                    r2 = await client.put(f"/v1/context/{entry_id}", json={"is_active": False})
                    r2.raise_for_status()

                status = "ANCHOR  " if is_active else "rag-only"
                log.info("  [%s] [%-12s] %s", status, category, title)
                created += 1

            except Exception as e:
                log.error("  FAILED: %s — %s", title, e)
                failed += 1

        log.info("")
        log.info("Done — created: %d | skipped: %d | failed: %d | total: %d",
                 created, skipped, failed, len(KNOWLEDGE))
        if created > 0:
            active_new = sum(1 for *_, a in KNOWLEDGE if a) - (skipped if skipped > 0 else 0)
            log.info("  Domain anchors always in Drizzle's system prompt: %d",
                     sum(1 for *_, a in KNOWLEDGE if a))
            log.info("  RAG-only knowledge (retrieved when relevant): %d",
                     sum(1 for *_, a in KNOWLEDGE if not a))


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    asyncio.run(seed(dry_run=dry_run))
