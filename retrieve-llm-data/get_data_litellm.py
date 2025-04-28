"""
Retrieve data from various models using litellm

A better way to run this code is via the CLI. See the README.md

If running directly, be sure to update:
 1. the parameters in this file
 2. The .env file
"""
import logging
import os
import sqlite3
from pathlib import Path
from sqlite3 import Connection
import typing
import dotenv

from litellm import completion
from litellm.types.utils import ModelResponse

from database_utils import init_db_schema, insert_prompt_to_db, insert_response_to_db

logging.basicConfig(filename='log.log',filemode='w',encoding='utf-8',level=logging.DEBUG)
logging.getLogger()

# PARAMETERS
sql_db_name = '../records_catejan.db' # Used to store the ids of prompts and responses
root_input_prompt_dir = Path('../prompts') # Top level directory with sub-directories for each prompt
prompt_id: int = 13
root_output_dir = Path('../outputs')
temperature = 0.7
number_of_responses_per_prompt = 1

# input_list_of_processes = '../lookup_strings_list.csv'
# model = "mistral/mistral-large-latest"
# model = "ollama_chat/llama3.2:latest"
# model = "anthropic/claude-3-5-sonnet-20240620"
# model = "gemini/gemini-2.5-pro-exp-03-25"
model = "openai/gpt-4.1-nano"

embedding_model = "mistral/mistral-embed" # For mistral models
# embedding_model = "gemini/text-embedding-004" # For Gemini
# rate_limit = 5/60 # 0.4 #  requests per second max for Anthropic
rate_limit = 0.4 #  requests per second max for Mistral
k_matches_from_embedding = 5
max_tokens_response =  2048 # may need to change
# END PARAMETERS


def get_prompt(top_prompt_dir: str, prompt_id: int, conn: Connection) -> str:
    """Finds the prompt text file within a given input directory and returns it as a string"""
    input_dir = Path(top_prompt_dir) / f'prompt_{prompt_id}' if not isinstance(top_prompt_dir, Path) else top_prompt_dir / f'prompt_{prompt_id}'
    assert input_dir.is_dir()
    assert isinstance(prompt_id,int)
    assert prompt_id > 0

    candidate_files = [x for x in input_dir.glob('prompt_*.txt')]
    if len(candidate_files)>1:
        raise ValueError(f'More than one prompt found in {input_dir}')

    with open(candidate_files[0],encoding='utf-8',mode='r') as f:
        prompt_txt = f.read()
    try:
        insert_prompt_to_db(conn=conn, prompt_text=prompt_txt, prompt_id=prompt_id)
    except ValueError:
        logging.warning(f'Prompt id={prompt_id} is already in the database')

    return prompt_txt


def run_prompt_from_dir_cli(root_input_prompt_dir: str, prompt_id: int, model: str, output_dir: str,
                        temperature: float, number_of_responses_per_prompt: int, sql_db_name:str, naming_system:str='response_id') -> None:
    root_input_prompt_dir = Path(root_input_prompt_dir)
    output_dir = Path(output_dir)
    try:
        temperature=float(temperature)
        prompt_id=int(prompt_id)
        with sqlite3.connect(sql_db_name) as conn:
            init_db_schema(conn)
        run_prompt_from_dir(root_input_prompt_dir, prompt_id, model, output_dir,
                        temperature, number_of_responses_per_prompt, conn, naming_system)

    finally:
        conn.close()


def run_prompt_from_dir(root_input_prompt_dir: str, prompt_id: int, model: str, output_dir: str,
                        temperature: float, number_of_responses_per_prompt: int, conn: Connection, naming_system:typing.Literal['response_id','descriptive']='response_id') -> None:
    """

    :param api_base:
    :param root_input_prompt_dir:
    :param prompt_id:
    :param model:
    :param output_dir:
    :param temperature:
    :param number_of_responses_per_prompt: Maximum 10
    """
    assert isinstance(prompt_id,int)
    assert isinstance(temperature,float)
    assert 0<=temperature<=1
    assert isinstance(number_of_responses_per_prompt,int)
    assert 0 < number_of_responses_per_prompt < 10
    assert isinstance(model,str)

    root_input_prompt_dir = Path(root_input_prompt_dir) if not isinstance(root_input_prompt_dir, Path) else root_input_prompt_dir
    output_dir = Path(output_dir) if not isinstance(output_dir,Path) else output_dir
    output_dir.mkdir(exist_ok=True,parents=True)

    model_name_part = model.split('/')[-1]
    provider_name = model.split('/')[0] #
    required_api_key = os.getenv(f'{provider_name.upper()}_API_KEY')
    if required_api_key is None:
        raise ValueError(f'Required api key {required_api_key} is null')

    logging.info('Loading prompt from')
    prompt_txt = get_prompt(root_input_prompt_dir, prompt_id=prompt_id,conn=conn)

    logging.info('Loaded prompt')
    logging.info(prompt_txt)
    logging.info('Writing prompt to output dir')
    with open(output_dir / f'prompt_{prompt_id}.txt', 'w', encoding='utf-8') as fw:
        fw.write(prompt_txt)
    logging.info('Written prompt to output dir')
    if temperature == 0 and number_of_responses_per_prompt > 1:
        logging.warning(
            'The temperature parameter is set to 0, but the number of responses per prompt is more than 1. Setting the number of response to 1, because response will always be the same (if no tools are used)')
        number_of_responses_per_prompt = 1

    for n in range(number_of_responses_per_prompt):
        if provider_name.lower() == 'ollama_chat':
            response = completion(model=model,
                                  messages=[{'role': 'user', 'content': prompt_txt}],
                                  temperature=temperature,
                                  max_tokens=max_tokens_response,
                                  stream=False)
            if not isinstance(response, ModelResponse):
                # LiteLLM returns also an id tuple
                raise Exception('Unexpected response. Should be a ModelResponse')
            response_text = response.choices[0].message.content
            logging.info(response)

        else:
            response = completion(model=model,
                                  messages=[{'role': 'user', 'content': prompt_txt}],
                                  temperature=temperature,
                                  max_tokens=max_tokens_response)
            if not isinstance(response, ModelResponse):
                # LiteLLM returns also an id tuple
                raise Exception('Unexpected response. Should be a ModelResponse')
            response_text = response.choices[0].message.content
            logging.info(response)

        response_id = insert_response_to_db(conn=conn,response_text=response_text,prompt_id=prompt_id,model_name=model,temperature=temperature,tools='',image_path='',llm_provider=provider_name)
        if naming_system == 'response_id':
            filename = f'response_{response_id}_chat.txt'
        elif naming_system == 'descriptive':
            model_name_part_for_filename = model_name_part.replace(':','').replace('/','').replace('\\','')
            filename = f'prompt_{prompt_id}_run_{n}_temp_{temperature}_model_{model_name_part_for_filename}_chat.txt'
        else:
            raise NotImplementedError(f'naming_system={naming_system} is not implemented. Double check it is one of the options in the type hint')
        with open(output_dir / filename, encoding='utf-8', mode='w') as fw:
            fw.write(response_text)
    logging.info('Done.')

if __name__ == '__main__':
    try:
        output_dir = root_output_dir / f'prompt_{prompt_id}'
        output_dir.mkdir(exist_ok=True, parents=True)

        dotenv.load_dotenv('../.env')
        api_base = os.getenv("OLLAMA_API_BASE")

        with sqlite3.connect(sql_db_name) as conn:
            init_db_schema(conn)

            run_prompt_from_dir(root_input_prompt_dir, prompt_id, model, output_dir, temperature, number_of_responses_per_prompt,
                            conn=conn)
    finally:
        conn.close()
