# AutoVerse AI 🚗⚡
### Generative AI Powered Automotive Intelligence Platform

AutoVerse AI is an enterprise-grade, academic research platform designed to explore, understand, compare, and analyze automobiles using **Generative AI**, **Local Large Language Models (Ollama Llama 3)**, **Retrieval-Augmented Generation (RAG)**, **Natural-Language-to-SQL (NL-to-SQL)**, and verified automotive database analytics.

---

## 🏛️ System Architecture

AutoVerse AI implements a multi-tier, decoupled architecture designed for zero data fabrication and low-latency local inference:

```
[ User Interaction ] 
         │
         ▼
[ Streamlit Web Interface (Dark Automotive Theme) ]
         │
         ▼
[ RAG Engine & Intent Classifier ]
   ├── Conceptual Automotive Question ──────> [ Domain Knowledge Prompt ] ─────┐
   └── Structured Vehicle Query (Price/Spec) ──> [ NL-to-SQL Generator ]        │
                                                        │                      │
                                                        ▼                      │
                                             [ Read-Only SQL Validator ]       │
                                                        │                      │
                                                        ▼                      │
                                             [ SQLite DB: autoverse.db ]       │
                                                        │                      │
                                                        ▼                      │
                                             [ Tabular Grounded Context ] ─────┤
                                                                               │
                                                                               ▼
                                                                [ Ollama Server (Llama 3) ]
                                                                               │
                                                                               ▼
                                                                [ Grounded AI Response & Audit ]
```

### Core Architecture Components:
1. **Frontend Presentation Layer (`app.py`)**: Built with Streamlit, custom CSS, dark carbon-fiber aesthetics, glowing cyan accents (`#00D2FF`), responsive layouts, and Plotly interactive visualizations.
2. **Local LLM Runtime (`llm_engine.py`)**: Communicates with the local Ollama server running `llama3:latest` on Apple Silicon via REST APIs (`/api/chat`, `/api/generate`, `/api/tags`).
3. **Retrieval-Augmented Generation Layer (`rag_engine.py`)**:
   - Classifies query intent (General Knowledge vs Structured DB Query vs Comparison).
   - Generates SQLite queries dynamically from natural language.
   - Enforces read-only safety validation (blocks `DROP`, `DELETE`, `UPDATE`, `INSERT`).
   - Retrieves grounded context from `autoverse.db` and injects strict anti-hallucination rules.
4. **Data Persistence Layer (`database.py`)**: High-performance SQLite database (`autoverse.db`) containing 8 relational tables with over 100,000+ automotive records.
5. **Specialized Intelligence Modules**:
   - `comparison.py`: Side-by-side vehicle comparison and AI technical test-drive verdict.
   - `recommendations.py`: Persona-driven vehicle matcher with explainable AI rationales.
   - `analytics.py`: Market distributions, brand pricing, and regional fuel economics using Plotly.

---

## 🚀 Key Modules & Capabilities

| Module | Purpose | Key Technologies |
| :--- | :--- | :--- |
| **💬 AI Chatbot** | Multi-turn automotive chat grounded in database records | Ollama Llama 3, RAG, Memory |
| **🔍 Vehicle Explorer** | Faceted filtering by brand, fuel, transmission, price, city | Streamlit, Pandas, SQLite |
| **⚖️ Vehicle Comparison** | Side-by-side spec comparison table + LLM analysis | Pandas, Ollama Llama 3 |
| **🎯 AI Recommender** | Persona-based quiz with explainable AI advice | Custom Scoring, Llama 3 Rationale |
| **📊 Market Analytics** | Interactive Plotly visualizer for price and mileage trends | Plotly Dark, Pandas |
| **🗄️ Database & Schema** | Schema viewer, table statistics, read-only SQL sandbox | SQLite3, PRAGMA, Safe Executor |

---

## 📂 Project Structure

```
autoverse-ai/
├── app.py                  # Main Streamlit dashboard application
├── config.py               # Central configuration, themes, forbidden SQL keywords
├── database.py             # Optimized SQLite connector and safe query executor
├── llm_engine.py           # Ollama Llama 3 client, health checks, chat endpoints
├── rag_engine.py           # Hybrid RAG pipeline and Natural-Language-to-SQL
├── chatbot.py              # Chat session management and starter prompts
├── recommendations.py      # Multi-factor recommendation algorithm and AI rationale
├── comparison.py           # Vehicle comparison specs and AI comparative verdict
├── analytics.py            # Interactive Plotly figures (prices, mileage, fuels)
├── autoverse.db            # Verified SQLite automotive database
├── requirements.txt        # Python dependency manifest
├── test_suite.py           # Automated unit test suite
├── test_ollama.py          # Standalone Ollama connection test
├── test_database.py        # Standalone SQLite table inspection test
├── .env                    # Environment configuration
└── datasets/               # Underlying dataset files
```

---

## 🛠️ Installation & Setup Instructions

### 1. Prerequisites
- **Operating System**: macOS (Apple Silicon recommended)
- **Python**: Python 3.10+ (tested with Python 3.15.2)
- **Ollama**: Download and install from [ollama.com](https://ollama.com)

### 2. Start Ollama and Pull Llama 3
In your terminal, start the Ollama server and pull the Llama 3 model:
```bash
# Verify Ollama is running
ollama serve

# Pull Llama 3 (if not already downloaded)
ollama pull llama3
```

### 3. Setup Virtual Environment
```bash
# Activate your existing virtual environment
source .venv/bin/activate

# Install required dependencies
pip install -r requirements.txt
```

### 4. Configuration (`.env`)
Verify `.env` has the following variables:
```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3
```

---

## 🧪 Testing Instructions

Run the automated test suite to verify database connectivity, SQL safety, Ollama integration, and the RAG pipeline:

```bash
# Run the complete test suite
.venv/bin/python test_suite.py
```

Expected output:
```
Ran 8 tests in ~8s
OK
```

You can also run individual diagnostic scripts:
```bash
# Test SQLite database directly
.venv/bin/python test_database.py

# Test Ollama Llama 3 directly
.venv/bin/python test_ollama.py

# Test RAG query directly
.venv/bin/python rag_engine.py
```

---

## ▶️ Running the Application

Launch the Streamlit web dashboard:

```bash
python -m streamlit run app.py
```
Or with the virtual environment binary:
```bash
.venv/bin/python -m streamlit run app.py
```

Open your browser at: `http://localhost:8501`

---

## 🎓 Academic Project Presentation Guide

When presenting AutoVerse AI for academic evaluations, emphasize the following points:

### 1. Generative AI vs Conventional Search
- Traditional vehicle apps (like CarDekho or CarWale) rely on rigid SQL search forms and fixed filters.
- **AutoVerse AI** allows users to ask free-form natural language questions (e.g., *"Which is the best diesel car under ₹10 lakh with high mileage?"*), translates the question into structured queries, retrieves verified database rows, and synthesizes a human-like response.

### 2. Retrieval-Augmented Generation (RAG) & Grounding
- Standard LLMs suffer from **hallucination**: fabricating car models, claiming inaccurate prices, or inventing mileage numbers.
- AutoVerse AI solves this by injecting actual database records retrieved from `autoverse.db` directly into the LLM context.
- Anti-hallucination guardrails instruct the model to explicitly state when data is not in the database rather than guessing.

### 3. Natural-Language-to-SQL (NL-to-SQL) & Security
- Demonstrates advanced prompting techniques where Llama 3 maps natural language questions to multi-table SQL queries joining `models`, `brands`, `variants`, and `prices`.
- **Security by Design**: Every SQL query passes through an AST/token-based validator that denies any mutation statements (`DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`), enforcing read-only safety.

### 4. Explainable AI (XAI) Recommendations
- Rather than providing a black-box recommendation score, AutoVerse AI generates structured explanations breaking down **why** each vehicle fits the user's specific family size, driving environment, and budget constraints.
