"""
Analytics Engine - Converts natural language to SQL queries and executes them.
Uses LangChain to create a SQL agent that queries Supabase via API.
"""
import os
import json
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client, Client
from langchain_groq import ChatGroq

load_dotenv()

# --- CONFIGURATION FROM ENV ---
# Ensure these are set in your .env file
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
# Defaults to 'public' schema if not specified
DB_SCHEMA = os.environ.get("DB_SCHEMA", "public") 
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

if not all([SUPABASE_URL, SUPABASE_KEY, GROQ_API_KEY]):
    raise ValueError("Missing required environment variables. Please check your .env file.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

llm = ChatGroq(
    model_name="llama-3.3-70b-versatile",
    temperature=0,
    groq_api_key=GROQ_API_KEY
)

# GUARDRAILS CONFIGURATION
FORBIDDEN_KEYWORDS = [
    "INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER", 
    "TRUNCATE", "GRANT", "REVOKE", "COMMIT", "ROLLBACK", "REPLACE"
]

def validate_readonly(query: str) -> bool:
    """
    Checks if a query contains any forbidden write/DDL keywords.
    Returns True if safe, False if forbidden.
    """
    clean_query = query.upper()
    for keyword in FORBIDDEN_KEYWORDS:
        # Check for keyword surrounded by spaces or at boundaries
        if f" {keyword} " in clean_query or clean_query.startswith(f"{keyword} ") or clean_query.endswith(f" {keyword}"):
            return False
    return True

class SupabaseSQLDatabase:
    def __init__(self, supabase_client, schema_name):
        self.supabase = supabase_client
        self.schema = schema_name
    
    def run(self, query: str) -> str:
        try:
            response = self.supabase.rpc('exec_sql', {'query': query}).execute()
            if response.data:
                data = response.data
                if isinstance(data, str): data = json.loads(data)
                
                if isinstance(data, list) and len(data) > 0:
                    df = pd.DataFrame(data)
                    return df.to_string()
                elif isinstance(data, dict):
                    return json.dumps(data, indent=2)
                else:
                    return "Query executed successfully (no results)"
            else:
                return "Query executed successfully (no results)"
        except Exception as e:
            return f"Error executing query: {str(e)}"
    
    def get_complete_schema(self) -> dict:
        schema_dict = {'tables': {}, 'relationships': []}
        try:
            # Get Tables
            tables_query = f"SELECT DISTINCT table_name FROM information_schema.tables WHERE table_schema = '{self.schema}' AND table_type = 'BASE TABLE' ORDER BY table_name"
            tables_response = self.supabase.rpc('exec_sql', {'query': tables_query}).execute()
            
            if not tables_response.data: return schema_dict
            table_data = tables_response.data
            if isinstance(table_data, str): table_data = json.loads(table_data)
            table_names = [t.get('table_name') for t in table_data if t.get('table_name')]
            
            if not table_names: return schema_dict
            
            for table_name in table_names:
                # 1. Columns
                cols_query = f"SELECT column_name, data_type, character_maximum_length, is_nullable, column_default FROM information_schema.columns WHERE table_schema = '{self.schema}' AND table_name = '{table_name}' ORDER BY ordinal_position"
                cols_resp = self.supabase.rpc('exec_sql', {'query': cols_query}).execute()
                columns = []
                if cols_resp.data:
                    c_data = cols_resp.data
                    if isinstance(c_data, str): c_data = json.loads(c_data)
                    for col in c_data:
                        columns.append({
                            'name': col.get('column_name'),
                            'type': col.get('data_type'),
                            'max_length': col.get('character_maximum_length'),
                            'nullable': col.get('is_nullable') == 'YES',
                            'default': col.get('column_default')
                        })
                
                # 2. Primary Keys (Distinct)
                pk_query = f"SELECT DISTINCT column_name FROM information_schema.table_constraints tc JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema WHERE tc.table_schema = '{self.schema}' AND tc.table_name = '{table_name}' AND tc.constraint_type = 'PRIMARY KEY'"
                pk_resp = self.supabase.rpc('exec_sql', {'query': pk_query}).execute()
                primary_keys = []
                if pk_resp.data:
                    p_data = pk_resp.data
                    if isinstance(p_data, str): p_data = json.loads(p_data)
                    primary_keys = [pk.get('column_name') for pk in p_data if pk.get('column_name')]
                
                # 3. Foreign Keys (Distinct)
                fk_query = f"SELECT DISTINCT kcu.column_name AS column_name, ccu.table_name AS foreign_table_name, ccu.column_name AS foreign_column_name FROM information_schema.table_constraints AS tc JOIN information_schema.key_column_usage AS kcu ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema JOIN information_schema.constraint_column_usage AS ccu ON ccu.constraint_name = tc.constraint_name AND ccu.table_schema = tc.table_schema WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_schema = '{self.schema}' AND tc.table_name = '{table_name}'"
                fk_resp = self.supabase.rpc('exec_sql', {'query': fk_query}).execute()
                foreign_keys = []
                if fk_resp.data:
                    f_data = fk_resp.data
                    if isinstance(f_data, str): f_data = json.loads(f_data)
                    for fk in f_data:
                        if fk.get('column_name'):
                            foreign_keys.append({
                                'column': fk.get('column_name'),
                                'references_table': fk.get('foreign_table_name'),
                                'references_column': fk.get('foreign_column_name')
                            })
                            schema_dict['relationships'].append({
                                'from_table': table_name,
                                'from_column': fk.get('column_name'),
                                'to_table': fk.get('foreign_table_name'),
                                'to_column': fk.get('foreign_column_name')
                            })
                
                # 4. Count (Optional - fail silently)
                row_count = None
                try:
                    count_resp = self.supabase.rpc('exec_sql', {'query': f'SELECT COUNT(*) as count FROM "{self.schema}"."{table_name}"'}).execute()
                    if count_resp.data:
                        cnt_data = count_resp.data
                        if isinstance(cnt_data, str): cnt_data = json.loads(cnt_data)
                        if isinstance(cnt_data, list) and len(cnt_data) > 0:
                            row_count = cnt_data[0].get('count') if isinstance(cnt_data[0], dict) else cnt_data[0]
                except: pass
                
                schema_dict['tables'][table_name] = {
                    'columns': columns,
                    'primary_keys': primary_keys,
                    'foreign_keys': foreign_keys,
                    'row_count': row_count
                }
            return schema_dict
        except Exception as e:
            print(f"Error getting schema: {e}")
            return {'tables': {}, 'relationships': []}
            
    def get_table_info(self, table_names: list = None) -> str:
        return self._format_schema_for_llm(self.get_complete_schema())
    
    def _format_schema_for_llm(self, schema_dict: dict) -> str:
        if not schema_dict or not schema_dict.get('tables'): return "No schema info"
        result = [f"# DATABASE SCHEMA: {self.schema}"]
        for t_name, t_info in schema_dict['tables'].items():
            result.append(f"\n### Table: {t_name}")
            result.append("\n**Columns:**")
            for col in t_info['columns']:
                result.append(f"  - {col['name']} ({col['type']})")
        return "\n".join(result)

def get_complete_schema_dict() -> dict:
    db = SupabaseSQLDatabase(supabase, DB_SCHEMA)
    return db.get_complete_schema()

def execute_query(query: str) -> tuple[str, pd.DataFrame, str, dict]:
    query = query.strip().rstrip(';')

    # GUARDRAIL CHECK
    if not validate_readonly(query):
        error_msg = "⛔ SECURITY ALERT: Write commands (INSERT, UPDATE, DELETE, DROP) are blocked."
        return "Query Blocked", pd.DataFrame(), error_msg, {"violation": True}

    error_msg = None
    debug_info = {'query': query, 'response_type': None, 'has_data': False}
    
    try:
        response = supabase.rpc('exec_sql', {'query': query}).execute()
        
        if hasattr(response, 'error') and response.error:
            return f"Error: {response.error}", pd.DataFrame(), str(response.error), debug_info

        if hasattr(response, 'data') and response.data:
            data = response.data
            
            # Handle Supabase Error Objects disguised as data
            if isinstance(data, dict) and 'error' in data:
                return "Error", pd.DataFrame(), data['error'].get('message', 'Unknown Error'), debug_info
            if isinstance(data, str):
                try: 
                    data = json.loads(data)
                    if isinstance(data, dict) and 'error' in data:
                        return "Error", pd.DataFrame(), data['error'].get('message'), debug_info
                except: pass

            # Convert to DF
            if isinstance(data, list) and len(data) > 0:
                df = pd.DataFrame(data)
                return f"Returned {len(df)} rows", df, None, debug_info
            elif isinstance(data, dict) and 'error' not in data:
                df = pd.DataFrame([data])
                return "Returned 1 row", df, None, debug_info
            else:
                return "Success (No Results)", pd.DataFrame(), None, debug_info
        
        return "Success (No Results)", pd.DataFrame(), None, debug_info
            
    except Exception as e:
        return f"Exception: {str(e)}", pd.DataFrame(), str(e), debug_info

def query_agent(natural_language_query: str) -> tuple[str, pd.DataFrame, str, str]:
    db = SupabaseSQLDatabase(supabase, DB_SCHEMA)
    complete_schema = db.get_complete_schema()
    available_tables = list(complete_schema.get('tables', {}).keys())
    
    if not available_tables:
        return "", pd.DataFrame(), "error", "No tables found", {}
        
    table_summary = []
    for table_name in available_tables:
        table_info = complete_schema['tables'][table_name]
        columns = [col['name'] for col in table_info.get('columns', [])]
        table_summary.append(f"- {table_name}: columns = {', '.join(columns)}")
    table_summary_str = "\n".join(table_summary)
    
    # 1. Identify Tables
    id_prompt = f"""Identify tables/columns from {DB_SCHEMA} for: "{natural_language_query}"
    Available: {table_summary_str}
    Return JSON: {{ "tables": [], "columns_needed": [] }}
    """
    id_resp = llm.invoke(id_prompt).content.strip()
    
    try:
        import re
        json_match = re.search(r'\{[^}]+\}', id_resp, re.DOTALL)
        if json_match:
            ident = json.loads(json_match.group())
            valid_tables = [t for t in ident.get('tables', []) if t in available_tables]
        else:
            valid_tables = []
    except:
        valid_tables = []
        
    if not valid_tables:
         return "", pd.DataFrame(), "error", "Could not identify relevant tables", {}

    # 2. Generate SQL
    schema_ctx = []
    for t in valid_tables:
        info = complete_schema['tables'][t]
        cols = [c['name'] for c in info['columns']]
        schema_ctx.append(f"Table {t}: {', '.join(cols)}")
        if info['primary_keys']: schema_ctx.append(f"PK: {info['primary_keys']}")
        if info['foreign_keys']: 
            for fk in info['foreign_keys']: 
                if fk['references_table'] in valid_tables:
                    schema_ctx.append(f"FK: {fk['column']} -> {fk['references_table']}.{fk['references_column']}")
    
    sql_prompt = f"""Generate SQL for: "{natural_language_query}"
    Schema: {DB_SCHEMA}
    Tables: {', '.join(valid_tables)}
    Context:
    {chr(10).join(schema_ctx)}
    
    Rules:
    1. Postgres syntax.
    2. Prefix tables with {DB_SCHEMA}.
    3. NO semicolons.
    4. NO markdown.
    5. Window functions must be in SELECT/subqueries.
    6. Return ONLY SQL.
    """
    
    sql_resp = llm.invoke(sql_prompt).content.strip()
    
    # Clean SQL
    sql_query = sql_resp.replace('```sql', '').replace('```', '').strip()
    
    # 3. Execute
    res_str, df, error, debug = execute_query(sql_query)
    status = "error" if error else "success"
    
    return sql_query, df, status, error, debug

# Export
sql_agent = query_agent