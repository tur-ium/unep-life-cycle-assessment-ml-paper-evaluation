import sqlite3
import pandas as pd

# Connect to the database
conn = sqlite3.connect("../records_cajetan.db")

# Display database tables
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print("Database tables:", [table[0] for table in tables])

# View prompts
df_prompts = pd.read_sql_query("SELECT * FROM prompts", conn)
print("\nPrompts:")
print(df_prompts)

# View responses
df_responses = pd.read_sql_query("SELECT * FROM responses", conn)
print("\nResponses:")
print(df_responses)

# Join prompts and responses
df_joined = pd.read_sql_query("""
    SELECT p.prompt_id, p.prompt_text, r.model_name, r.response_text 
    FROM prompts p 
    JOIN responses r ON p.prompt_id = r.prompt_id
""", conn)
print("\nJoined data:")
print(df_joined)

# Detailed view of responses with timestamps
print("\nDetailed responses (sorted by prompt and time):")
df_detailed = pd.read_sql_query("""
    SELECT 
        r.prompt_id, 
        r.response_id,
        r.model_name,
        r.created_at,
        r.response_filename,
        SUBSTR(r.response_text, 1, 50) || '...' AS response_preview
    FROM responses r
    ORDER BY r.prompt_id, r.created_at
""", conn)
print(df_detailed)

# Close connection
conn.close()