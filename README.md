```markdown
# 💻 SQL_TERMINAL

**SQL_TERMINAL** is a "plug-and-play" AI Data Analyst that connects to any PostgreSQL/Supabase database. It transforms natural language questions into safe, executable SQL queries, provides an interactive workbench for editing, and automatically generates intelligent visualizations—all wrapped in a retro hacker-terminal interface.

![SQL Terminal Interface](https://via.placeholder.com/800x450.png?text=SQL+Terminal+Interface+Preview)

## ⚡ Key Features

* **Natural Language to SQL:** Ask questions in plain English (e.g., *"Show me the top 5 customers by revenue"*) and get valid SQL instantly using Groq (Llama 3).
* **Active Workbench:** Review and edit the generated SQL code before execution to fine-tune your results.
* **Smart Visualization:** The system analyzes your data structure to automatically select and render the best chart type (Bar, Line, Scatter, Pie, etc.) using Plotly.
* **Auto-Schema Scanner:** On startup, the engine scans your database to map all tables, columns, primary keys, and foreign key relationships without manual configuration.
* **Security Guardrails:** Strictly enforces **Read-Only** access at the engine level. Keywords like `INSERT`, `UPDATE`, `DELETE`, `DROP`, and `ALTER` are blocked before execution.
* **Terminal Aesthetic:** A clean, dark-mode UI built with Streamlit, designed for focus and utility.

## 🛠️ Tech Stack

* **Frontend:** [Streamlit](https://streamlit.io/)
* **Database:** [Supabase](https://supabase.com/) (PostgreSQL)
* **AI/LLM:** [LangChain](https://www.langchain.com/) + [Groq](https://console.groq.com/) (Llama 3.3 70B)
* **Visualization:** [Plotly](https://plotly.com/python/)
* **Data Processing:** [Pandas](https://pandas.pydata.org/)

---

## 🚀 Quick Start Guide

### 1. Clone the Repository
```bash
git clone [https://github.com/swadib/fintech_dashboard.git](https://github.com/swadib/fintech_dashboard.git)
cd fintech_dashboard

```

### 2. Install Dependencies

It is recommended to use a virtual environment.

```bash
# Create virtual environment
python -m venv venv

# Activate it (Mac/Linux)
source venv/bin/activate
# Activate it (Windows)
# venv\Scripts\activate

# Install libraries
pip install -r requirements.txt

```

### 3. Configure Environment Variables

Create a `.env` file in the root directory of the project.

```bash
touch .env

```

Add your keys to the file:

```ini
# .env

# Supabase Connection
# You can find these in your Supabase Dashboard -> Project Settings -> API
SUPABASE_URL="[https://your-project-id.supabase.co](https://your-project-id.supabase.co)"
SUPABASE_KEY="your-supabase-service-role-key"

# AI Provider
# Get a free key from [https://console.groq.com](https://console.groq.com)
GROQ_API_KEY="gsk_your_groq_api_key_here"

# Database Schema (Optional)
# Defaults to 'public' if not specified. Change this if your tables are in a different schema.
DB_SCHEMA="public" 

```

### 4. ⚠️ CRITICAL: Setup Database Function

To allow the AI to execute SQL queries safely via the API, you must create a standard Remote Procedure Call (RPC) function in your database.

1. Go to your **Supabase Dashboard**.
2. Open the **SQL Editor**.
3. Paste and run the following SQL command:

```sql
create or replace function exec_sql(query text)
returns json
language plpgsql
security definer
as $$
declare
  result json;
begin
  execute 'select json_agg(t) from (' || query || ') t' into result;
  return result;
end;
$$;

```

*Note: This function takes a text query, executes it, and returns the result as JSON. It is required for the `analytics_engine.py` to communicate with your database.*

### 5. Run the Application

```bash
streamlit run app.py

```

The application will launch in your default browser (usually at `http://localhost:8501`).

---

## 📖 How to Use

1. **Sidebar Status:** Check the sidebar to ensure your schema is loaded. You should see a list of your tables under "DATABASE_TOPOLOGY".
2. **Ask a Question:** Type a question in the input bar at the bottom (e.g., *"What is the total sales amount per month?"*) and hit Enter.
3. **Review SQL:** The generated SQL will appear in the "SQL_WORKBENCH" text area.
4. **Edit (Optional):** If the query isn't quite right, you can edit the SQL code directly in the text area and click **[ RUN EDITED QUERY ]**.
5. **Visualize:** Click **[ GENERATE VISUALIZATION ]** to see a chart. The system will automatically pick the best chart type for your data.
6. **Save:** Enter a name for your analysis and click **[ SAVE ]** to pin it to the sidebar for easy access later.

---

## 🔒 Security & Limitations

This application includes a software-level **Keyword Guardrail** in `analytics_engine.py`. It scans every query for dangerous keywords (`DROP`, `DELETE`, `UPDATE`, `INSERT`, `GRANT`, etc.) and blocks execution if found.

**Production Advice:**
While the software guardrails are robust for general use, for a true production environment, you should use a **Database Role with Read-Only permissions** for the connection string/API key you provide in the `.env` file. This adds a hard layer of security at the database level.
