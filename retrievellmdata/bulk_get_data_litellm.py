import logging
import sqlite3
from pathlib import Path
from typing import List

import dotenv

from database_utils import init_db_schema
from get_data_litellm import run_prompt_from_dir


logging.basicConfig(filename='log.log',filemode='w',encoding='utf-8',level=logging.DEBUG)
logging.getLogger()

# PARAMETERS
sql_db_name = '../records_cajetan.db' # Used to store the ids of prompts and responses
root_input_prompt_dir = Path('../prompts') # Top level directory with sub-directories for each prompt
prompt_id: int = 13
root_output_dir = Path('../outputs')
temperature = 0.7
number_of_responses_per_prompt = 1

models = [
"mistral/mistral-large-latest",
"ollama_chat/llama3.2:latest",
"anthropic/claude-3-5-sonnet-20240620",
"gemini/gemini-2.5-pro-exp-03-25",
"openai/gpt-4.1-nano"
]
rate_limits = []

def bulk_run_models_on_prompt(prompt_id:int,root_input_prompt_dir, models:List[str],temperature=0, number_of_responses_per_prompt=1):
    for model in models:
        try:
            output_dir = root_output_dir / f'prompt_{prompt_id}'
            output_dir.mkdir(exist_ok=True, parents=True)

            dotenv.load_dotenv('../.env')

            with sqlite3.connect(sql_db_name) as conn:
                init_db_schema(conn)

                run_prompt_from_dir(root_input_prompt_dir, prompt_id, model, output_dir, temperature, number_of_responses_per_prompt,
                                conn=conn)
        finally:
            conn.close()


def bulk_run_all(sql_db_name, root_input_prompt_dir, temperature, number_of_responses_per_prompt):
    with sqlite3.connect(sql_db_name) as conn:
        prompt_ids = conn.execute('SELECT Id FROM Prompts')
    count_prompts = len(prompt_ids)
    for prompt_id in prompt_ids:
        logging.info(f'========= RUNNING PROMPT {prompt_id} / {count_prompts} ACROSS {len(models)} MODELS ==========================')
        try:
            output_dir = root_output_dir / f'prompt_{prompt_id}'
            output_dir.mkdir(exist_ok=True, parents=True)

            dotenv.load_dotenv('../.env')

            with sqlite3.connect(sql_db_name) as conn:
                init_db_schema(conn)

                bulk_run_models_on_prompt(root_input_prompt_dir, prompt_id, output_dir, temperature,
                                    number_of_responses_per_prompt,
                                    conn=conn)
        finally:
            logging.info(f'================ FINISHED RUNNING {count_prompts} PROMPTS ACROSS {len(models)} MODELS ==========================')
            conn.close()
