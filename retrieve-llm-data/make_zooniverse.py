import csv
import logging
import os
import re
from pathlib import Path
import sqlite3

import dotenv

from utils import save_text_as_img_markdown

logging.basicConfig(filename='make_zooniverse.log',filemode='w',encoding='utf-8',level=logging.DEBUG)
logging.getLogger()

# PARAMETERS
input_dir = Path('../outputs/prompt_6')
prompt_id = 6
temperature = 0 # For duck.ai it appears to be 0
llm_provider = 'duck.ai'
run_date = '2025-04-13' # In this case the date the prompt was run is this date. Update if running in the future.
prompt_txt = 'prompt.txt'
prompt_run_by = 'artur'
start_response_line_no = 8

def make_zooniverse_files(prompt_dir,db_name:str,poppler_path:str=None):
    if not poppler_path:
        dotenv.load_dotenv()
        poppler_path = os.getenv('POPPLER_PATH')
    assert poppler_path is not None
    assert poppler_path != ''
    prompt_dir = Path(prompt_dir) if not isinstance(prompt_dir,Path) else prompt_dir
    assert prompt_dir.is_dir()

    logging.info(f'Start making zooniverse files for {prompt_dir}')
    logging.info(f'Initiating connection to db {db_name}')
    conn = sqlite3.connect(db_name)
    logging.info(f'Connected to {db_name}')
    manifest_header = ['response_id', 'prompt_id', 'prompt_image', 'response_image_1', 'response_image_2', '#llm_model',
                       '#temperature', '#date_run', '#llm_provider', '#prompt_run_by']

    rows_in_manifest = []
    rows_in_manifest.append(manifest_header)

    logging.info('Looking for files ending with _chat.txt')
    for file in prompt_dir.glob('*_chat.txt'):
        logging.info(f'Reading file {file.name}')
        re_match_response_id_pattern = re.match(r'response_([0-9]{1,3})_chat.txt',file.name,re.I)
        re_match_descriptive = re.match(r'prompt_?<prompt_id>([0-9]{1,3})_run_?<n>([0-9]{1,3})_temp_?<temp>(([0-9][.])?[0-9]+)_model_?<model>(.{1,100})_chat.txt',file.name,re.I)
        if re_match_response_id_pattern:
            response_id = re_match_response_id_pattern.groups()[0]
            try:
                response_id = int(response_id)
            except ValueError as e:
                raise e
        else:
            raise NotImplementedError('Can only take in files with the response id in them')
        with open(file,'r',encoding='utf-8') as f:
            md_text = f.read()
            save_text_as_img_markdown(md_text,output_path=prompt_dir/ file.name.replace(file.suffix,".png"),poppler_path=poppler_path)

        select_model_name = conn.execute('SELECT model_name,temperature,tools,execution_datestamp,llm_provider,prompt_run_by,prompt_id from responses where id=?',[response_id])
        db_data_for_response_id = select_model_name.fetchone()
        if not db_data_for_response_id:
            raise ValueError(f'Could not find response id {response_id} in the database {db_name}')
        llm_provider_model_name = db_data_for_response_id[0]
        temperature = db_data_for_response_id[1]
        tools = db_data_for_response_id[2]
        execution_date = db_data_for_response_id[3]

        model_name = llm_provider_model_name.split('/')[1]
        llm_provider = llm_provider_model_name.split('/')[0]
        prompt_run_by = db_data_for_response_id[5]
        prompt_id = db_data_for_response_id[6]

        rows_in_manifest.append(
        [response_id, prompt_id, 'prompt.png', file.name, '', model_name, temperature, execution_date, llm_provider, prompt_run_by])

    select_prompt_text = conn.execute('select prompt_text from prompts where id = ?',[prompt_id])
    prompt_text = select_prompt_text.fetchone()
    if not prompt_text:
        logging.warning(f'prompt text could not be found for prompt {prompt_id}. Skipping...')
    else:
        logging.info('Saving prompt image ...')
        save_text_as_img_markdown(prompt_text[0],output_path=prompt_dir / 'prompt.png')
        logging.info('Done saving prompt image')
    with open(prompt_dir / 'manifest.csv', 'w', newline='') as fw:
        csv_writer = csv.writer(fw,delimiter=',')
        csv_writer.writerows(rows_in_manifest)
    logging.info(f'Done creating files for prompt {prompt_id} for Zooniverse. Saved in prompt dir folder {prompt_dir.absolute()}')

# def make_zooniverse_manifest_file_for_subject_set(input_dir:Path, prompt_id:int, prompt_filename:str, prompt_run_by, start_line_no:int):
#     """
#
#     :param input_dir: The path to the directory containing the responses to a given prompt.
#     :param prompt_id: An integer id for the prompt, used for storing in a sqlite database
#     :param prompt_filename: The name of the file containing the prompt used to generate the responses
#     :param prompt_run_by:
#     :param start_line_no:
#     :return:
#     """
#     if f'{prompt_id}' not in input_dir.name:
#         raise ValueError('Are you sure you have the right prompt id?')
#
#     # END PARAMETERS
#     manifest_header = ['response_id','prompt_id','prompt_image','response_image_1','response_image_2','#llm_model','#temperature','#date_run','#llm_provider','#prompt_run_by']
#     rows_in_manifest = list()
#
#     import sqlite3
#     conn = sqlite3.connect('../records.db')
#     conn.execute(
#         'CREATE TABLE IF NOT EXISTS responses (id INTEGER PRIMARY KEY AUTOINCREMENT, prompt_id INTEGER NOT NULL, response_text NVARCHAR(15000) NOT NULL, cot_text NVARCHAR(15000) NULL,  image_path NVARCHAR(500) NOT NULL)')
#
#     rows_in_manifest.append(manifest_header)
#
#     allowed_models = ['claude_3_haiku', 'gpt_o3_mini', 'gpt_o4_mini','llama_3.3_70b','mistral_small_3']
#
#     files_in_input_dir = [x for x in input_dir.iterdir()]
#     print(files_in_input_dir)
#     prompt_text = input_dir / 'prompt.txt'
#
#     for i, model in enumerate(allowed_models):
#         print(model)
#         filename = f'{model}_response.png'
#         chat_filename = f'{model}_chat.txt'
#         expected_filepath = input_dir / filename
#         expected_filepath_chat = input_dir / chat_filename
#         print(expected_filepath)
#
#         response = ''
#         if expected_filepath not in files_in_input_dir:
#             raise ValueError(f'Could not find response for {model} in {input_dir}')
#         if expected_filepath_chat not in files_in_input_dir:
#             print(f'Could not find chat for {model} in {files_in_input_dir}')
#         else:
#             chat = open(expected_filepath_chat,'r',encoding='utf-8').readlines()
#             response = '\n'.join(chat[start_response_line_no:])
#             print(f'Found response = {response[:50]}...')
#
#         # SQL operations (now done in the litellm)
#         conn.execute(f"INSERT INTO responses (prompt_id,response_text,image_path) VALUES ({prompt_id},?,?)",(response,filename))
#         conn.commit()
#         response_id_sqlite_response = conn.execute(f"select max(id) from responses where prompt_id={prompt_id}").fetchone()
#         response_id = response_id_sqlite_response[0]
#         print(response_id)
#         rows_in_manifest.append([response_id,prompt_id,'prompt.png',filename,'',model,temperature,run_date,llm_provider,prompt_run_by])
#
#     with open(input_dir / 'manifest.csv', 'w', newline='') as fw:
#         csv_writer = csv.writer(fw,delimiter=',')
#         csv_writer.writerows(rows_in_manifest)
#     print('done')

if __name__ == '__main__':
    make_zooniverse_files(r'C:\Users\Artur\Documents\Projects (local)\GLAD AI\llm testing\Zooniverse project\outputs\prompt_102','records5.db')