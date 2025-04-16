"""A simple SQLite database to keep track of which prompts have been run and their responses"""

import sqlite3


def init_db_schema(conn):
    conn.execute(
        'CREATE TABLE IF NOT EXISTS prompts (id INTEGER NOT NULL, prompt_text NVARCHAR(15000) NOT NULL, context_filepath NVARCHAR(400) NULL, image_path NVARCHAR(500) NULL)'
    )
    conn.execute(
        'CREATE TABLE IF NOT EXISTS responses (id INTEGER PRIMARY KEY AUTOINCREMENT, prompt_id INTEGER NOT NULL, response_text NVARCHAR(15000) NOT NULL, model_name TEXT NOT NULL, execution_datestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, cot_text NVARCHAR(15000) NULL, temperature REAL NULL DEFAULT 0, tools NVARCHAR(1000) NULL, image_path NVARCHAR(500) NULL, FOREIGN KEY(prompt_id) REFERENCES prompts(id));')
    conn.commit()

def insert_prompt_to_db(conn:sqlite3.Connection, prompt_text:str, prompt_id:int=None, context_filepath:str=None):
    assert isinstance(conn, sqlite3.Connection)
    assert isinstance(prompt_text,str)
    if prompt_id:
        assert isinstance(prompt_id,int)
        assert prompt_id > 0
        id_already_in_db = conn.execute("""select * from prompts where id=?""", prompt_id)
        id_already_in_db.fetchall()
        if len(id_already_in_db) > 0:
            raise ValueError(f'prompt id {id_already_in_db} is already in the database')
    if context_filepath:
        assert isinstance(context_filepath,str)
    if not prompt_id:
        current_max_id = conn.execute("""select max(prompt_id) from prompts""")
        current_max_id = current_max_id.fetchone()
        if current_max_id is None:
            current_max_id=0
        prompt_id = current_max_id + 1

    conn.execute("INSERT INTO prompts(id,prompt_text,context_filepath) VALUES (?,?,?)",(prompt_id,prompt_text,context_filepath))
    conn.commit()

def insert_response_to_db(conn:sqlite3.Connection,prompt_id:int,model_name:str,response_text:str,temperature:float,tools:str='',image_path:str='') -> int:
    assert isinstance(conn, sqlite3.Connection)
    assert isinstance(response_text,str)

    assert isinstance(prompt_id,int)

    assert isinstance(temperature,float)
    if image_path:
        assert isinstance(image_path,str)
    if tools:
        assert isinstance(tools,str)

    conn.execute("INSERT INTO responses(prompt_id,response_text,model_name,temperature,tools,image_path) VALUES (?,?,?,?,?,?)",(prompt_id,response_text,model_name,temperature,tools,image_path))
    conn.commit()
    response_id_select = conn.execute("SELECT id from responses order by execution_datestamp desc limit 1")
    response_id = response_id_select.fetchone()[0]
    return response_id
