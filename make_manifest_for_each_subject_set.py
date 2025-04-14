import csv
from pathlib import Path
import sqlite3

# PARAMETERS
input_dir = Path('prompt_6')
prompt_id = 6
temperature = 0 # For duck.ai it appears to be 0
llm_provider = 'duck.ai'
run_date = '2025-04-13' # In this case the date the prompt was run is this date. Update if running in the future.
prompt_txt = 'prompt.txt'
prompt_run_by = 'artur'
start_response_line_no = 8

if f'{prompt_id}' not in input_dir.name:
    raise ValueError('Are you sure you have the right prompt id?')

# END PARAMETERS
manifest_header = ['response_id','prompt_id','prompt_image','response_image_1','response_image_2','#llm_model','#temperature','#date_run','#llm_provider','#prompt_run_by']
rows_in_manifest = list()

import sqlite3
conn = sqlite3.connect('records.db')
conn.execute(
    'CREATE TABLE IF NOT EXISTS responses (id INTEGER PRIMARY KEY AUTOINCREMENT, prompt_id INTEGER NOT NULL, response_text NVARCHAR(15000) NOT NULL, cot_text NVARCHAR(15000) NULL,  image_path NVARCHAR(500) NOT NULL)')

rows_in_manifest.append(manifest_header)

allowed_models = ['claude_3_haiku', 'gpt_o3_mini', 'gpt_o4_mini','llama_3.3_70b','mistral_small_3']

files_in_input_dir = [x for x in input_dir.iterdir()]
print(files_in_input_dir)
prompt_text = input_dir / 'prompt.txt'

for i, model in enumerate(allowed_models):
    print(model)
    filename = f'{model}_response.png'
    chat_filename = f'{model}_chat.txt'
    expected_filepath = input_dir / filename
    expected_filepath_chat = input_dir / chat_filename
    print(expected_filepath)
    response = ''
    if expected_filepath not in files_in_input_dir:
        raise ValueError(f'Could not find response for {model} in {input_dir}')
    if expected_filepath_chat not in files_in_input_dir:
        print(f'Could not find chat for {model} in {files_in_input_dir}')
    else:
        chat = open(expected_filepath_chat,'r',encoding='utf-8').readlines()
        response = '\n'.join(chat[start_response_line_no:])
        print(f'Found response = {response[:50]}...')
    sqlite_insert_response = conn.execute(f"INSERT INTO responses (prompt_id,response_text,image_path) VALUES ({prompt_id},?,?)",(response,filename))
    conn.commit()
    response_id_sqlite_response = conn.execute(f"select max(id) from responses where prompt_id={prompt_id}").fetchone()
    response_id = response_id_sqlite_response[0]
    print(response_id)
    rows_in_manifest.append([response_id,prompt_id,'prompt.png',filename,'',model,temperature,run_date,llm_provider,prompt_run_by])

with open(input_dir / 'manifest.csv', 'w', newline='') as fw:
    csv_writer = csv.writer(fw,delimiter=',')
    csv_writer.writerows(rows_in_manifest)
print('done')
