import csv
import logging
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List

import dotenv
import pandas as pd

from utils import save_text_as_img_markdown

current_date = datetime.now()
formatted_date = current_date.strftime('%Y-%m-%d')


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


def make_zooniverse_subject_set_per_prompt(db_name: str, root_prompt_dir: str | Path, zooniverse_output_dir: str | Path,
                                       poppler_path: str = None, skip_prompt_ids: List[int] = None):
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
        assert all([isinstance(id, int) for id in skip_prompt_ids])
    zooniverse_output_dir = Path(zooniverse_output_dir) if not isinstance(zooniverse_output_dir,
                                                                          Path) else zooniverse_output_dir
    zooniverse_output_dir.mkdir(parents=True,exist_ok=True)

    warning_rows = []  # List[response_id,prompt_id,reason]

    logging.info(f'root prompt dir = {root_prompt_dir} found and is a directory')
    logging.info(f'Start making zooniverse files for {root_prompt_dir}')
    logging.info(f'Initiating connection to db {db_name}')
    conn = sqlite3.connect(db_name)
    logging.info(f'Connected to {db_name}')
    manifest_header = ['response_id', 'prompt_id', 'prompt_image', 'response_image_1', 'response_image_2',
                       'response_image_3', 'response_image_4', 'response_image_5', '#llm_model',
                       '#temperature', '#date_run', '#llm_provider', '#prompt_run_by']

    rows_in_manifest = {}

    responses_table_columns = ['id', 'model_name', 'temperature', 'tools', 'execution_datestamp', 'llm_provider',
                               'prompt_run_by', 'prompt_id', 'response_filename']
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
            warning_rows.append([response_id, prompt_id, reason])
            continue
        #####
        if not file.exists():
            warning_msg = f'Could not find response record from database in the location {file}. Check root_output_dir and filename in database. Continuing to check other records in the database ...'
            logging.warning(warning_msg)
            warning_rows.append([response_id, prompt_id, warning_msg])
            continue
        prompt_txt_filepath = root_prompt_dir / f'prompt_{prompt_id}' / f'prompt_{prompt_id}.txt'
        prompt_image_filename = f'prompt_{prompt_id}.png'
        with open(prompt_txt_filepath, 'r', encoding='utf-8') as f:
            prompt_txt = f.read()
            prompt_txt = f'## Question:\n\n {prompt_txt}'
            prompt_output_filepath = zooniverse_output_dir / f'prompt_{prompt_id}' / prompt_image_filename
            if not prompt_output_filepath.parent.exists():
                prompt_output_filepath.parent.mkdir(exist_ok=True)

            save_text_as_img_markdown(prompt_txt, output_path=prompt_output_filepath,
                                      poppler_path=poppler_path)

        response_filename2 = ''
        response_filename3 = ''
        response_filename4 = ''
        response_filename5 = ''
        with open(file, 'r', encoding='utf-8') as f:
            md_text = f.read()
            base_response_filename = file_name.replace(file.suffix, ".png")
            output_response_txt_path = zooniverse_output_dir / f'prompt_{prompt_id}' / base_response_filename
            rendered_response_filenames = save_text_as_img_markdown(md_text,
                                                                    output_path=output_response_txt_path,
                                                                    poppler_path=poppler_path)
            if len(rendered_response_filenames) > 5:
                warning_msg = f'More than 5 images required to render response {response_id}. This is not supported, therefore this response will not be included in the survey'
                logging.warning(warning_msg)
                warning_rows.append([response_id, prompt_id, warning_msg])
                continue
            if len(rendered_response_filenames) > 0:
                response_filename1 = rendered_response_filenames[0].name
            if len(rendered_response_filenames) > 1:
                response_filename2 = rendered_response_filenames[1].name
            if len(rendered_response_filenames) > 2:
                response_filename2 = rendered_response_filenames[2].name
            if len(rendered_response_filenames) > 3:
                response_filename2 = rendered_response_filenames[3].name
            if len(rendered_response_filenames) > 4:
                response_filename2 = rendered_response_filenames[4].name
            else:
                response_filename1 = rendered_response_filenames[0].name
        if prompt_id not in rows_in_manifest:
            rows_in_manifest[prompt_id] = [manifest_header]
        rows_in_manifest[prompt_id].append(
            [response_id, prompt_id, prompt_image_filename, response_filename1, response_filename2, response_filename3,
             response_filename4, response_filename5, model_name, temperature, execution_date, llm_provider,
             prompt_run_by])
    for prompt_id in rows_in_manifest:
        with open(zooniverse_output_dir / f'prompt_{prompt_id}' / 'manifest.csv', 'w', newline='') as fw:
            csv_writer = csv.writer(fw, delimiter=',')
            csv_writer.writerows(rows_in_manifest[prompt_id])
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

    input_root_dir = r'../outputs/all_responses_may_2025'
    output_dir = '../outputs/zooniverse_subject_set_may_all_v3'
    dotenv.load_dotenv('../.env')
    poppler_path = os.getenv('POPPLER_PATH')
    skip_prompt_ids = [
        17, # This prompt is too long to render in one page, therefore not including, as confusing to a reviewer
    ]
    make_zooniverse_subject_set_per_prompt(r"../records_may_all.db",root_prompt_dir=input_root_dir, zooniverse_output_dir=output_dir,skip_prompt_ids=[17])