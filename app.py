"""
Streamlit App - Terminal Style SQL Interface
"""
import streamlit as st
import pandas as pd
from analytics_engine import sql_agent, execute_query, get_complete_schema_dict
from viz_engine import create_visualization

# --- CONFIGURATION & STYLING ---
st.set_page_config(
    page_title="SQL_TERMINAL",
    page_icon="💻",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;700&display=swap');
    
    .stApp {
        background-color: #0e1117;
        font-family: 'Fira Code', monospace;
    }
    
    /* Global Font Enforcement */
    h1, h2, h3, h4, h5, h6, p, .stMarkdown, .stTextInput > div > div > input, .stTextArea textarea {
        font-family: 'Fira Code', monospace !important;
        color: #e6edf3;
    }
    
    h1, h2, h3 {
        color: #00ff41 !important;
    }
    
    /* Buttons */
    .stButton button {
        background-color: #21262d;
        color: #00ff41;
        border: 1px solid #00ff41;
        border-radius: 0px;
        font-family: 'Fira Code', monospace !important;
    }
    .stButton button:hover {
        background-color: #00ff41;
        color: #000000;
        border: 1px solid #00ff41;
    }
    
    /* Text Area (SQL Editor) */
    .stTextArea textarea {
        background-color: #0d1117;
        color: #ff7b72;
        border: 1px solid #30363d;
    }

    [data-testid="stSidebar"] {
        background-color: #010409;
        border-right: 1px solid #30363d;
    }
    
    code {
        color: #ff7b72;
        font-family: 'Fira Code', monospace !important;
    }
</style>
""", unsafe_allow_html=True)

# --- SESSION STATE INITIALIZATION ---
if "saved_charts" not in st.session_state:
    st.session_state.saved_charts = []

if "query_history" not in st.session_state:
    st.session_state.query_history = []

if "schema_dict" not in st.session_state:
    st.session_state.schema_dict = None

if "active_analysis" not in st.session_state:
    st.session_state.active_analysis = None

# --- CALLBACKS ---

def save_chart_callback():
    """Handles saving the chart to history. Triggered by Button OR Enter key."""
    if st.session_state.active_analysis and 'fig' in st.session_state.active_analysis:
        title = st.session_state.save_title_input
        st.session_state.saved_charts.append({
            "title": title,
            "fig": st.session_state.active_analysis['fig'],
            "sql": st.session_state.active_analysis['sql']
        })
        st.toast(f"MODULE '{title}' SAVED", icon="💾")

def trigger_analysis():
    """Sets the flag to run analysis. Used by both Enter key and Execute button."""
    if st.session_state.query_in_widget:
        st.session_state.run_analysis_flag = True

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("## SYSTEM_STATUS")
    
    if st.button("[ REFRESH SCHEMA ]"):
        with st.spinner("SCANNING DATABASE STRUCTURE..."):
            try:
                st.session_state.schema_dict = get_complete_schema_dict()
                st.success("SCHEMA LOADED")
            except Exception as e:
                st.error(f"ERR: {str(e)}")

    st.markdown("---")
    
    if st.session_state.schema_dict and st.session_state.schema_dict.get('tables'):
        st.markdown("## DATABASE_TOPOLOGY")
        tables = st.session_state.schema_dict['tables']
        for table_name, info in tables.items():
            with st.expander(f"TABLE: {table_name}"):
                pks = info.get('primary_keys', [])
                if pks:
                    st.markdown("**PRIMARY KEYS:**")
                    for pk in pks: st.code(f"{pk}", language="text")
                fks = info.get('foreign_keys', [])
                if fks:
                    st.markdown("**RELATIONSHIPS:**")
                    for fk in fks: st.caption(f"{fk['column']} -> {fk['references_table']}.{fk['references_column']}")
                st.markdown("**COLUMNS:**")
                for col in info.get('columns', []):
                    col_name = col['name']
                    col_type = col['type']
                    prefix = "🔑 " if col_name in pks else "🔗 " if any(fk['column'] == col_name for fk in fks) else ""
                    st.text(f"{prefix}{col_name} ({col_type})")
    else:
        st.text("WAITING FOR SCHEMA...")
    
    st.markdown("---")
    
    st.markdown("## SAVED_MODULES")
    if st.session_state.saved_charts:
        for i, chart in enumerate(st.session_state.saved_charts):
            with st.expander(f"MOD_{i+1}: {chart['title']}", expanded=False):
                st.plotly_chart(chart['fig'], use_container_width=True, key=f"saved_chart_{i}")
                st.code(chart['sql'], language='sql')
                if st.button("DELETE", key=f"del_{i}"):
                    st.session_state.saved_charts.pop(i)
                    st.rerun()
    else:
        st.text("NO MODULES SAVED")
        
    st.markdown("---")
    
    st.markdown("## LOGS")
    if st.session_state.query_history:
        for i, hist in enumerate(reversed(st.session_state.query_history[-10:])):
            smart_title = (hist['question'][:35] + '..') if len(hist['question']) > 35 else hist['question']
            with st.expander(f"{i+1} > {smart_title}"):
                st.code(hist['sql'], language='sql')
                st.text(f"Rows: {hist['result_count']}")
                st.text(f"Status: {hist['status']}")

# --- MAIN INTERFACE ---

st.markdown("""
<div style="
    font-family: 'Fira Code', monospace; 
    white-space: pre; 
    line-height: 1.1; 
    color: #00ff41; 
    font-size: 14px; 
    overflow-x: auto;
    margin-bottom: 20px;
">
  /$$$$$$   /$$$$$$  /$$       /$$      /$$ /$$$$$$ /$$$$$$$$
 /$$__  $$ /$$__  $$| $$      | $$  /$ | $$|_  $$_/|_____ $$ 
| $$  \__/| $$  \ $$| $$      | $$ /$$$| $$  | $$       /$$/ 
|  $$$$$$ | $$  | $$| $$      | $$/$$ $$ $$  | $$      /$$/  
 \____  $$| $$  | $$| $$      | $$$$_  $$$$  | $$     /$$/   
 /$$  \ $$| $$  \ $$| $$      | $$$/ \  $$$  | $$    /$$/    
|  $$$$$$/|  $$$$$$$| $$$$$$$$| $$/   \  $$ /$$$$$$ /$$$$$$$$
 \______/  \____  $$|________/|__/     \__/|______/|________/
                \__/                                         
</div>
""", unsafe_allow_html=True)

st.markdown("### > ANALYTICS_CORE_ONLINE")

# --- INPUT AREA ---

col_in, col_btn = st.columns([4, 1], vertical_alignment="bottom")

with col_in:
    st.text_input(
        "INPUT_COMMAND:", 
        placeholder="Enter natural language query...",
        key="query_in_widget",
        on_change=trigger_analysis
    )

with col_btn:
    st.button("[ EXECUTE ]", use_container_width=True, on_click=trigger_analysis)


# --- EXECUTION LOGIC ---
if st.session_state.get('run_analysis_flag', False):
    st.session_state.run_analysis_flag = False
    
    user_query = st.session_state.query_in_widget
    
    if not st.session_state.schema_dict:
        with st.spinner("INITIALIZING SCHEMA..."):
            st.session_state.schema_dict = get_complete_schema_dict()

    with st.spinner("PROCESSING..."):
        sql_query, df, status, error, debug = sql_agent(user_query)
        
        st.session_state.active_analysis = {
            "query": user_query,
            "sql": sql_query,
            "df": df,
            "status": status,
            "error": error,
            "debug": debug,
            "timestamp": pd.Timestamp.now()
        }
        
        st.session_state.query_history.append({
            "question": user_query,
            "sql": sql_query,
            "result_count": len(df),
            "status": status
        })


# --- DISPLAY & EDIT LOGIC ---

if st.session_state.active_analysis:
    analysis = st.session_state.active_analysis
    
    st.markdown("### > SQL_WORKBENCH")
    
    # 1. EDITABLE SQL
    edited_sql = st.text_area(
        "SOURCE_CODE (EDITABLE):", 
        value=analysis['sql'], 
        height=150,
        key=f"sql_editor_{str(analysis.get('timestamp'))}"
    )
    
    if st.button("[ RUN EDITED QUERY ]", key="run_edit"):
        with st.spinner("EXECUTING CUSTOM QUERY..."):
            result_str, new_df, new_error, new_debug = execute_query(edited_sql)
            status = "error" if new_error else "success"
            
            st.session_state.active_analysis.update({
                "sql": edited_sql,
                "df": new_df,
                "status": status,
                "error": new_error,
                "debug": new_debug
            })
            st.rerun()

    # 2. RESULTS
    if analysis['status'] == "error":
        st.error(f"EXECUTION FAILED: {analysis['error']}")
        with st.expander("DEBUG_TRACE"):
            st.json(analysis['debug'])
    else:
        rows = len(analysis['df'])
        st.markdown(f"### > DATA_RETURN (ROWS: {rows})")
        st.dataframe(analysis['df'], use_container_width=True)
        
        st.markdown("---")
        
        # 3. VISUALIZATION
        viz_container = st.container()
        
        col_v1, col_v2 = st.columns([1, 4])
        with col_v1:
            if st.button("[ GENERATE VISUALIZATION ]"):
                with st.spinner("RENDERING GRAPHICS..."):
                    fig = create_visualization(analysis['df'], analysis['query'])
                    st.session_state.active_analysis['fig'] = fig 
        
        if 'fig' in st.session_state.active_analysis and st.session_state.active_analysis['fig']:
            fig = st.session_state.active_analysis['fig']
            
            fig.update_layout(
                paper_bgcolor='#0e1117',
                plot_bgcolor='#0e1117',
                font_color='#00ff41',
                title_font_color='#00ff41',
                legend_font_color='#ffffff'
            )
            
            st.plotly_chart(fig, use_container_width=True, key="active_viz")
            
            # 4. SAVE MODULE
            st.markdown("#### > SAVE_MODULE")
            c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
            
            with c1:
                st.text_input(
                    "MODULE_NAME", 
                    value=analysis['query'][:50], 
                    key="save_title_input", 
                    on_change=save_chart_callback
                )
            
            with c2:
                st.button("[ SAVE ]", use_container_width=True, on_click=save_chart_callback)