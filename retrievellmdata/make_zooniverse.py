import csv
import logging
import os
import re
from pathlib import Path
import sqlite3
from typing import List

import dotenv
import pandas as pd

from retrievellmdata.bulk_get_data_litellm_gemini_openai_mistral import root_output_dir
from utils import save_text_as_img_markdown

from datetime import datetime

current_date = datetime.now()
formatted_date = current_date.strftime('%Y-%m-%d')





def make_zooniverse_subject_set_from_directory(prompt_dir, db_name: str, poppler_path: str = None):
    if not poppler_path:
        dotenv.load_dotenv()
        poppler_path = os.getenv('POPPLER_PATH')
    assert poppler_path is not None
    assert poppler_path != ''
    prompt_dir = Path(prompt_dir) if not isinstance(prompt_dir, Path) else prompt_dir
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
        re_match_descriptive = re.match(
            'prompt_?<prompt_id>([0-9]{1,10})_run_?<n>([0-9]{1,3})_temp_?<temp>(([0-9][.])?[0-9]+)_model_?<model>(.{1,100})_chat.txt',
            file.name, re.I)
        re_match_response_id_pattern = re.match(r'response_([0-9]{1,3})_chat.txt', file.name, re.I)
        re_match_descriptive = re.match(
            r'prompt_(?P<prompt_id>[0-9]{1,3})_run_(?P<n>[0-9]{1,3})_temp_(?P<temp>([0-9][.])?[0-9]+)_model_(?P<model>.{1,100})_chat.txt',
            file.name, re.I)
        if re_match_response_id_pattern:
            response_id = re_match_response_id_pattern.groups()[0]
            try:
                response_id = int(response_id)
            except ValueError as e:
                raise e
        elif re_match_descriptive:
            response_id_cursor = conn.execute("""select id from responses where response_filename = ?""", [file.name])
            response_id = response_id_cursor.fetchone()
            if response_id is None:
                raise Exception(
                    f'Could not find response filename {file.name} in the database {db_name}. Double check db name')
            if isinstance(response_id, tuple):
                response_id = response_id[0]
        else:
            raise NotImplementedError('Can only take in files with the response id in them')
        with open(file, 'r', encoding='utf-8') as f:
            md_text = f.read()
            save_text_as_img_markdown(md_text, output_path=prompt_dir / file.name.replace(file.suffix, ".png"),
                                      poppler_path=poppler_path)

        select_model_name = conn.execute(
            'SELECT model_name,temperature,tools,execution_datestamp,llm_provider,prompt_run_by,prompt_id from responses where id=?',
            [response_id])
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
            [response_id, prompt_id, 'prompt.png', file.name, '', model_name, temperature, execution_date, llm_provider,
             prompt_run_by])

    select_prompt_text = conn.execute('select prompt_text from prompts where id = ?', [prompt_id])
    prompt_text = select_prompt_text.fetchone()
    if not prompt_text:
        logging.warning(f'prompt text could not be found for prompt {prompt_id}. Skipping...')
    else:
        logging.info('Saving prompt image ...')
        save_text_as_img_markdown(prompt_text[0], output_path=prompt_dir / f'prompt_{prompt_id}.png',poppler_path=poppler_path)
        logging.info('Done saving prompt image')
    with open(prompt_dir / 'manifest.csv', 'w', newline='') as fw:
        csv_writer = csv.writer(fw, delimiter=',')
        csv_writer.writerows(rows_in_manifest)
    logging.info(
        f'Done creating files for prompt {prompt_id} for Zooniverse. Saved in prompt dir folder {prompt_dir.absolute()}')


def make_zooniverse_subject_set_per_db(db_name: str, root_prompt_dir: str | Path, zooniverse_output_dir: str|Path, poppler_path: str = None, skip_prompt_ids: List[int] = None):
    # Validate parameters
    if not poppler_path:
        dotenv.load_dotenv()
        poppler_path = os.getenv('POPPLER_PATH')
    assert poppler_path is not None
    assert poppler_path != ''
    root_prompt_dir = Path(root_prompt_dir) if not isinstance(root_prompt_dir, Path) else root_prompt_dir
    assert root_prompt_dir.is_dir()

    if skip_prompt_ids is None:
        skip_prompt_ids = []
    else:
        assert all([isinstance(id,int) for id in skip_prompt_ids])
    zooniverse_output_dir = Path(zooniverse_output_dir) if not isinstance(zooniverse_output_dir, Path) else zooniverse_output_dir
    zooniverse_output_dir.mkdir(parents=True)

    warning_rows = [] # List[response_id,prompt_id,reason]

    logging.info(f'root prompt dir = {root_prompt_dir} found and is a directory')
    logging.info(f'Start making zooniverse files for {root_prompt_dir}')
    logging.info(f'Initiating connection to db {db_name}')
    conn = sqlite3.connect(db_name)
    logging.info(f'Connected to {db_name}')
    manifest_header = ['response_id', 'prompt_id', 'prompt_image', 'response_image_1', 'response_image_2', 'response_image_3','response_image_4','response_image_5', '#llm_model',
                       '#temperature', '#date_run', '#llm_provider', '#prompt_run_by']

    rows_in_manifest = []
    rows_in_manifest.append(manifest_header)
    
    responses_table_columns = ['id','model_name','temperature','tools','execution_datestamp','llm_provider','prompt_run_by','prompt_id','response_filename']
    select_responses = conn.execute(
        'SELECT id,model_name,temperature,tools,execution_datestamp,llm_provider,prompt_run_by,prompt_id,response_filename from responses')
    responses_list = select_responses.fetchall()
    logging.info(f'Loaded {len(responses_list)} response records from database {db_name}')

    filename_idx = responses_table_columns.index('response_filename')
    response_idx = responses_table_columns.index('id')
    model_name_idx = responses_table_columns.index('model_name')
    execution_date_idx = responses_table_columns.index('execution_datestamp')
    llm_provider_idx = responses_table_columns.index('llm_provider')
    prompt_id_idx = responses_table_columns.index('prompt_id')
    prompt_run_by_idx = responses_table_columns.index('prompt_run_by')
    temperature_idx = responses_table_columns.index('temperature')
    for response_info in responses_list:

        logging.info(response_info)
        file_name = response_info[filename_idx]
        response_id = response_info[response_idx]

        model_name = response_info[model_name_idx]
        execution_date = response_info[execution_date_idx]
        llm_provider = response_info[llm_provider_idx]
        prompt_id = response_info[prompt_id_idx]
        prompt_run_by = response_info[prompt_run_by_idx]
        temperature = response_info[temperature_idx]
        file = root_prompt_dir / f'prompt_{prompt_id}' / Path(file_name)
        ######
        if prompt_id in skip_prompt_ids:
            reason = f'Skipping response with id = {response_id} because prompt_id ={prompt_id} is in skip_prompt_ids parameter passed to this function'
            logging.info(reason)
            warning_rows.append([response_id,prompt_id,reason])
            continue
        #####
        if not file.exists():
            warning_msg = f'Could not find response record from database in the location {file}. Check root_output_dir and filename in database. Continuing to check other records in the database ...'
            logging.warning(warning_msg)
            warning_rows.append([response_id, prompt_id, warning_msg])
            continue
        prompt_txt_filepath = root_prompt_dir / f'prompt_{prompt_id}' / f'prompt_{prompt_id}.txt'
        prompt_image_filename = f'prompt_{prompt_id}.png'
        with open(prompt_txt_filepath,'r',encoding='utf-8') as f:
            prompt_txt = f.read()
            prompt_txt = f'## Question:\n\n {prompt_txt}'
            save_text_as_img_markdown(prompt_txt, output_path=zooniverse_output_dir / prompt_image_filename,poppler_path=poppler_path)

        response_filename2 = ''
        response_filename3 = ''
        response_filename4 = ''
        response_filename5 = ''
        with open(file, 'r', encoding='utf-8') as f:
            md_text = f.read()
            # TODO: if the response text is longer, split it up
            base_response_filename = file_name.replace(file.suffix, ".png")
            rendered_response_filenames = save_text_as_img_markdown(md_text, output_path=zooniverse_output_dir / base_response_filename,
                                      poppler_path=poppler_path)
            if len(rendered_response_filenames) > 5:
                warning_msg = f'More than 5 images required to render response {response_id}. This is not supported, therefore this response will not be included in the survey'
                logging.warning(warning_msg)
                warning_rows.append([response_id,prompt_id,warning_msg])
                continue
            if len(rendered_response_filenames)>0:
                response_filename1 = rendered_response_filenames[0]
            if len(rendered_response_filenames)>1:
                response_filename2 = rendered_response_filenames[1]
            if len(rendered_response_filenames)>2:
                response_filename2 = rendered_response_filenames[2]
            if len(rendered_response_filenames)>3:
                response_filename2 = rendered_response_filenames[3]
            if len(rendered_response_filenames)>4:
                response_filename2 = rendered_response_filenames[4]
            else:
                response_filename1 = rendered_response_filenames[0]
        rows_in_manifest.append(
            [response_id, prompt_id, prompt_image_filename, response_filename1, response_filename2, response_filename3, response_filename4, response_filename5, model_name, temperature, execution_date, llm_provider,
             prompt_run_by])
    with open(zooniverse_output_dir / 'manifest.csv', 'w', newline='') as fw:
        csv_writer = csv.writer(fw, delimiter=',')
        csv_writer.writerows(rows_in_manifest)
    # Save warnings
    warning_df = pd.DataFrame(warning_rows)
    warning_df.to_csv(zooniverse_output_dir / 'warnings.csv')

    logging.info(
        f'Done creating files for subject set with {len(warning_rows)} warnings. Saved in prompt dir folder {zooniverse_output_dir.absolute()}')

if __name__ == '__main__':
    # PARAMETERS
    console_handler = logging.StreamHandler()
    file_handler = logging.FileHandler(f'make_zooniverse_{formatted_date}.log', mode='w', encoding='utf-8')

    # Set levels for handlers
    console_handler.setLevel(logging.DEBUG)
    file_handler.setLevel(logging.DEBUG)

    # Create formatters and add them to handlers
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    # Add handlers to the logger
    logger=logging.getLogger()
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    # make_zooniverse_subject_set_from_directory(
    #     r'C:\Users\Artur\Documents\Projects (local)\GLAD AI\llm testing\Zooniverse project\outputs\artur_20250430\prompt_1',
    #     r"C:\Users\Artur\Documents\Projects (local)\GLAD AI\llm testing\Zooniverse project\records_artur_20250430.db")

    input_root_dir = r'C:\Users\Artur\Documents\Projects (local)\GLAD AI\llm testing\Zooniverse project\outputs\artur_20250504_temp1.0'
    output_dir = '../outputs/zooniverse_subject_set_artur_20250504_temp1.0'
    dotenv.load_dotenv('../.env')
    poppler_path = os.getenv('POPPLER_PATH')
    skip_prompt_ids = [
        17, # This prompt is too long to render in one page, therefore not including, as confusing to a reviewer
    ]
    make_zooniverse_subject_set_per_db(r"../records_artur_20250504.db",root_prompt_dir=input_root_dir, zooniverse_output_dir=output_dir,skip_prompt_ids=[17])