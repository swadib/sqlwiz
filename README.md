# 💻 SQLWIZ

**SQLWIZ** is a "plug-and-play" AI Data Analyst that connects to any PostgreSQL/Supabase database. It transforms natural language questions into safe, executable SQL queries, provides an interactive workbench for editing, and automatically generates intelligent visualizations—all wrapped in a retro hacker-terminal interface.

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

### 1. Prerequisites
* Python 3.9 or higher
* A Supabase project (or any PostgreSQL database exposed via API)
* A Groq API Key (Free tier available at [console.groq.com](https://console.groq.com))

### 2. Clone the Repository
```bash
git clone [https://github.com/yourusername/sql-terminal.git](https://github.com/yourusername/sql-terminal.git)
cd sql-terminal
