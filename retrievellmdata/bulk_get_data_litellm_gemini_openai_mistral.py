import logging
import os
import re
import sqlite3
import time
from pathlib import Path
from typing import List


import dotenv

from database_utils import init_db_schema
from get_data_litellm import run_prompt_from_dir

logging.basicConfig(filename='log.log', filemode='w', encoding='utf-8', level=logging.DEBUG)
logging.getLogger()

# PARAMETERS
sql_db_name = '../records_artur_20250505.db'  # Used to store the ids of prompts and responses
root_input_prompt_dir = Path('../prompts')  # Top level directory with sub-directories for each prompt
root_output_dir = Path('../outputs/artur_20250504_temp0.0')
temperature = 0.0 # For OpenAI o-series models the only permitted temperature is fixed to 1 https://community.openai.com/t/why-is-the-temperature-and-top-p-of-o1-models-fixed-to-1-not-0/938922/4
number_of_responses_per_prompt = 1

models = [
    "mistral/mistral-large-2411",
    "gemini/gemini-2.0-flash-001", # 2025-05-04 Enabled billing, therefore increasing to Gemini 2.0 flash (instead of flash lite). 2025-04-03 Having issues accessing gemini-2.0-flash-001. Error 503, model overloaded
    "openai/gpt-4.1", # GPT 4.1 mini and GPT-4.1 (standard) returned rate limit errors when attempted to use
]


def bulk_run_models_on_prompt(prompt_id: int, root_input_prompt_dir:str|Path, models: List[str], root_output_dir, temperature=0.0,
                              number_of_responses_per_prompt=1, wait_time: float = 5):
    for model in models:
        try:
            output_dir = root_output_dir / f'prompt_{prompt_id}'
            output_dir.mkdir(exist_ok=True, parents=True)

            dotenv.load_dotenv('../.env')

            with sqlite3.connect(sql_db_name) as conn:
                init_db_schema(conn)

                run_prompt_from_dir(root_input_prompt_dir, prompt_id, model, output_dir, temperature,
                                    number_of_responses_per_prompt,
                                    conn=conn)
                time.sleep(wait_time)
        finally:
            conn.close()


def bulk_run_all(sql_db_name, root_input_prompt_dir:str|Path, root_output_dir:str|Path, models:List[str], temperature, number_of_responses_per_prompt,
                 sleep_time_between_batches:float=3):
    assert isinstance(sleep_time_between_batches,(float,int))
    root_input_prompt_dir = Path(root_input_prompt_dir) if not isinstance(root_input_prompt_dir,
                                                                          Path) else root_input_prompt_dir
    root_output_dir = Path(root_output_dir) if not isinstance(root_output_dir,
                                                                          Path) else root_output_dir
    prompt_ids = set()
    for x in root_input_prompt_dir.glob('prompt_*'):
        prompt_id_re = re.match(r'prompt_([0-9]{1,3})', x.name)
        if not prompt_id_re:
            continue
        prompt_id = int(prompt_id_re.group(1))
        prompt_ids.add(prompt_id)

    count_prompts = len(prompt_ids)

    for prompt_id in prompt_ids:
        logging.info(
            f'========= RUNNING PROMPT {prompt_id} / {count_prompts} ACROSS {len(models)} MODELS ==========================')
        try:
            dotenv.load_dotenv('../.env')

            with sqlite3.connect(sql_db_name) as conn:
                init_db_schema(conn)

                bulk_run_models_on_prompt(prompt_id, root_input_prompt_dir, models=models, root_output_dir=root_output_dir, temperature=temperature,
                                          number_of_responses_per_prompt=number_of_responses_per_prompt)
                time.sleep(sleep_time_between_batches)
        finally:
            logging.info(
                f'================ FINISHED RUNNING {count_prompts} PROMPTS ACROSS {len(models)} MODELS ==========================')
            conn.close()


if __name__ == '__main__':
    sleep_time = float(os.getenv("SLEEP_TIME_BETWEEN_BATCHES"))
    # bulk_run_models_on_prompt(10,Path(r'C:\Users\Artur\Documents\Projects (local)\GLAD AI\llm testing\Zooniverse project\prompts'),models)
    bulk_run_all(sql_db_name, root_input_prompt_dir=root_input_prompt_dir, root_output_dir=root_output_dir, models=models,temperature= temperature,
                 number_of_responses_per_prompt= number_of_responses_per_prompt,
                 sleep_time_between_batches=sleep_time)
