# Zeni User Guide & Houdini Setup

This guide walks you through setting up and using **Zeni** inside SideFX Houdini.

---

## 1. Prerequisites

* **Houdini**: Version 19.5, 20.0, or 20.5 (Windows / Linux / macOS).
* **Python**: Python 3.12 (managed via `uv` or system Python).
* **Gemini API Key**: A free key from [Google AI Studio](https://aistudio.google.com/).

---

## 2. Server Setup

1. **Clone & Install Dependencies**:
   ```bash
   git clone https://github.com/Binitpyro/PMA-CreativeXprize.git
   cd PMA-CreativeXprize
   uv sync
   ```

2. **Configure API Key & Token**:
   Set `GEMINI_API_KEY` in your environment:
   ```bash
   # Windows (PowerShell)
   $env:GEMINI_API_KEY="your-gemini-api-key"
   $env:X_LOCAL_ACCESS_TOKEN="dev_token"

   # Linux / macOS
   export GEMINI_API_KEY="your-gemini-api-key"
   export X_LOCAL_ACCESS_TOKEN="dev_token"
   ```

3. **Run Test Suite**:
   ```bash
   uv run pytest
   ```

---

## 3. In-Houdini Plugin Setup

1. **Add to PYTHONPATH**:
   Before launching Houdini, add the repository root to `PYTHONPATH`:
   ```bash
   # Windows (PowerShell)
   $env:PYTHONPATH="D:\projects\PMA-CreativeXprize;$env:PYTHONPATH"
   ```

2. **Import Shelf Tools**:
   * Open Houdini.
   * Go to **Shelf Toolbar** → Click **+ (Gear Icon)** → **Import Shelf Set...**
   * Browse to `houdini_plugin/shelf/pma_tools.shelf` and import.
   * You will see two new shelf buttons:
     * **PMA: Index Scene**
     * **PMA: Ask**

---

## 4. Using Zeni in Houdini

### Step 1: Indexing Your Scene
1. Open any `.hip` file in Houdini.
2. Click **PMA: Index Scene** on the shelf toolbar.
3. Zeni extracts node graph comments, VEX wrangle code, non-default parameters, and node errors/warnings into your local SQLite FTS5 database.

### Step 2: Asking Questions
1. Click **PMA: Ask** on the shelf toolbar.
2. Type your question in the PySide UI dialog (e.g. *"Why is my velocity wrangle giving an undefined variable warning?"*).
3. Click **Submit**. Zeni streams the answer token-by-token into the dialog formatted as:
   - `### Root Cause`
   - `### VEX / Node Fix`
   - `### Step-by-Step Instructions`
