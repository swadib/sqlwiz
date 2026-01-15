"""
Visualization Engine - Intelligent plotting using LLM-driven configuration.
"""
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from langchain_groq import ChatGroq
import os

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
llm = ChatGroq(model_name="llama-3.3-70b-versatile", temperature=0, groq_api_key=GROQ_API_KEY)

def preprocess_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Intelligently convert columns to correct types for plotting.
    """
    df_clean = df.copy()
    
    for col in df_clean.columns:
        col_lower = col.lower()
        if 'year' in col_lower and pd.api.types.is_numeric_dtype(df_clean[col]):
            if df_clean[col].nunique() < 20:
                df_clean[col] = df_clean[col].astype(str)
                
    for col in df_clean.select_dtypes(include=['object']):
        try:
            if df_clean[col].astype(str).str.contains(r'\d{4}-\d{2}-\d{2}', regex=True).any():
                df_clean[col] = pd.to_datetime(df_clean[col])
        except (ValueError, TypeError):
            continue
            
    return df_clean

def get_visualization_config(df: pd.DataFrame, query: str) -> dict:
    """
    Asks the LLM to analyze the data and query to output a JSON plotting configuration.
    """
    if df.empty:
        return {"chart_type": "none"}

    profile = []
    for col in df.columns:
        dtype = str(df[col].dtype)
        sample = str(df[col].head(5).tolist())
        profile.append(f"- {col} ({dtype}): Sample {sample}")
    
    data_summary = "\n".join(profile)

    system_prompt = """
    You are a Data Visualization Expert. 
    Analyze the USER QUERY and the DATA SUMMARY to recommend the best Plotly chart.
    
    CRITICAL: You must identify if the user wants to compare multiple categories over time.
    
    Output ONLY a valid JSON object with these keys:
    - "chart_type": One of ["bar", "line", "scatter", "pie", "histogram", "box", "table"]
    - "x": Column for X-axis
    - "y": Column for Y-axis (numeric)
    - "color": Column for color segmentation/legend (CRITICAL for comparing groups)
    - "barmode": "group" (side-by-side) or "stack" or "relative" (only for bar charts)
    - "title": A descriptive title
    - "orientation": "v" (vertical) or "h" (horizontal)
    
    GUIDELINES:
    1. **Comparison Over Time (Multi-Year):**
       - If you have [Year, Category, Value]:
       - Option A (Trends): chart_type="line", x="Year", y="Value", color="Category"
       - Option B (Comparison): chart_type="bar", x="Year", y="Value", color="Category", barmode="group"
    
    2. **Distribution/Proportions:**
       - Use "pie" only for simple totals.
       - Use "bar" for ranking many items.
       
    3. **Colors:**
       - If you map a numeric "Year" column to 'color', ensure the chart interprets it as categorical if the user wants distinct colors per year.
    """
    
    user_prompt = f"""
    USER QUERY: "{query}"
    
    DATA SUMMARY:
    {data_summary}
    
    JSON RESPONSE:
    """
    
    try:
        response = llm.invoke(system_prompt + user_prompt)
        content = response.content.strip()
        
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
            
        config = json.loads(content)
        return config
    except Exception as e:
        print(f"Visualization Agent Error: {e}")
        
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        cat_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
        
        fallback_config = {"chart_type": "table", "title": "Data Table"}
        
        if len(numeric_cols) > 0 and len(cat_cols) > 0:
            fallback_config = {
                "chart_type": "bar",
                "x": cat_cols[0],
                "y": numeric_cols[0],
                "title": f"Bar Chart of {numeric_cols[0]} by {cat_cols[0]}"
            }
            
        return fallback_config

def create_visualization(df: pd.DataFrame, query: str) -> go.Figure:
    """
    Main entry point. Preprocesses data -> Gets Config -> Renders Plot.
    """
    if df.empty:
        return None
        
    df = preprocess_dataframe(df)
    
    if len(df) > 1000:
        df_display = df.head(1000)
    else:
        df_display = df

    config = get_visualization_config(df_display, query)
    
    chart_type = config.get("chart_type", "table")
    x_col = config.get("x")
    y_col = config.get("y")
    color_col = config.get("color")
    barmode = config.get("barmode", "group")
    title = config.get("title", f"Analysis: {query}")
    orientation = config.get("orientation", "v")

    fig = None
    
    try:
        if chart_type == "line":
            if x_col:
                try:
                    df_display = df_display.sort_values(by=x_col)
                except:
                    pass
            
            fig = px.line(
                df_display, 
                x=x_col, 
                y=y_col, 
                color=color_col, 
                title=title, 
                markers=True
            )
            
        elif chart_type == "bar":
            if y_col and orientation == 'v' and not color_col:
                df_display = df_display.sort_values(by=y_col, ascending=False).head(50)
            
            fig = px.bar(
                df_display, 
                x=x_col, 
                y=y_col, 
                color=color_col, 
                title=title, 
                orientation=orientation,
                barmode=barmode,
                text_auto='.2s'
            )
            
        elif chart_type == "scatter":
            fig = px.scatter(
                df_display, 
                x=x_col, 
                y=y_col, 
                color=color_col, 
                title=title, 
                trendline="ols" if len(df_display) > 2 else None
            )
            
        elif chart_type == "pie":
            fig = px.pie(
                df_display, 
                names=x_col, 
                values=y_col, 
                title=title,
                hole=0.3
            )
            
        elif chart_type == "histogram":
            fig = px.histogram(df_display, x=x_col, color=color_col, title=title)
            
        elif chart_type == "box":
            fig = px.box(df_display, x=x_col, y=y_col, color=color_col, title=title)
            
        else:
            return None 

        if fig:
            fig.update_layout(
                template="plotly_white",
                height=600,
                margin=dict(t=80, b=100, l=50, r=50), 
                hovermode="x unified",
                
                legend=dict(
                    orientation="h",
                    yanchor="top",
                    y=-0.2,
                    xanchor="center",
                    x=0.5
                ),
                
                title=dict(
                    text=title,
                    y=0.95,
                    x=0.5,
                    xanchor='center',
                    font=dict(size=20)
                )
            )
            
    except Exception as e:  
        print(f"Plotting Error: {e}")
        return None

    return fig