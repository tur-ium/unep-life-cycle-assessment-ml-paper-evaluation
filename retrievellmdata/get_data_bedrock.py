"""
Retrieve data from various models using AWS Bedrock

A better way to run this code is via the CLI. See the README.md

If running directly, be sure to update:
 1. the parameters in this file
 2. The .env file with AWS credentials
"""
import logging
import os
import sqlite3
import time
import json
from pathlib import Path
from sqlite3 import Connection
import typing
import dotenv
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log
)

from database_utils import init_db_schema, insert_prompt_to_db, insert_response_to_db, update_response_filename
from base_assistant import BaseAssistant

# logging.basicConfig(filename='log.log', filemode='w', encoding='utf-8', level=logging.DEBUG)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("lca_assistant")

# PARAMETERS
sql_db_name = '../records_bedrock.db'  # Used to store the ids of prompts and responses
root_input_prompt_dir = Path('../prompts')  # Top level directory with sub-directories for each prompt
prompt_id: int = 10
root_output_dir = Path('../outputs')
temperature = 0.0
number_of_responses_per_prompt = 1

# Default model to use
model = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"
# Other available models:
# model = "anthropic.claude-3-5-sonnet-20241022-v2:0"
# model = "anthropic.claude-3-5-haiku-20241022-v1:0"
# model = "us.amazon.nova-pro-v1:0"
# model = "us.amazon.nova-lite-v1:0"
# model = "us.amazon.nova-micro-v1:0"
# model = "us.amazon.nova-premier-v1:0"
# model = "us.meta.llama3-3-70b-instruct-v1:0"
# model = "meta.llama4-maverick-17b-instruct-v1:0"
# model = "meta.llama4-scout-17b-instruct-v1:0"
# model = "us.deepseek.r1-v1:0"
# model = "us.mistral.mistral-large-2407-v1:0"

# AWS region for Bedrock
aws_region = "us-east-1"
max_tokens_response = 4096  # may need to change
# END PARAMETERS


class BedrockAssistant(BaseAssistant):
    def __init__(self, 
                 model_name: str = "us.anthropic.claude-3-7-sonnet-20250219-v1:0",
                 maintain_history: bool = True,
                 **kwargs):
        self.supported_models = [
            "anthropic.claude-3-sonnet-20240229-v1:0",
            "anthropic.claude-3-haiku-20240307-v1:0", 
            "anthropic.claude-3-5-sonnet-20241022-v2:0",
            "us.anthropic.claude-3-7-sonnet-20250219-v1:0",
            "anthropic.claude-3-5-haiku-20241022-v1:0",
            "us.amazon.nova-pro-v1:0",
            "us.amazon.nova-lite-v1:0", 
            "us.amazon.nova-micro-v1:0",
            "us.meta.llama3-3-70b-instruct-v1:0",
            "us.deepseek.r1-v1:0",
            "us.mistral.mistral-large-2407-v1:0"
        ]
        
        if model_name not in self.supported_models:
            raise ValueError(f"Model {model_name} not supported. Supported models: {self.supported_models}")
            
        super().__init__(model_name=model_name, maintain_history=maintain_history)

    def _initialize_model(self, region: str = "us-west-2", **kwargs) -> None:
        """Initialize Bedrock client with retry configuration"""
        try:
            retry_config = Config(
                region_name=region,
                retries={
                    "max_attempts": 10,
                    "mode": "adaptive",
                }
            )

            session_kwargs = {"region_name": region}
            if profile_name := os.environ.get("AWS_PROFILE"):
                logger.info(f"Using AWS profile: {profile_name}")
                session_kwargs["profile_name"] = profile_name

            session = boto3.Session(**session_kwargs)
            self.client = session.client(
                service_name="bedrock-runtime",
                config=retry_config
            )
            
            logger.info(f"Initialized Bedrock client in {region}")
            
        except Exception as e:
            logger.error(f"Error initializing Bedrock client: {str(e)}")
            raise

    def _get_model_type(self) -> str:
        """Determine model type from model name"""
        if "nova" in self.model_name:
            return "nova"
        elif "llama" in self.model_name:
            return "llama"
        elif "deepseek" in self.model_name:
            return "deepseek"
        elif "mistral" in self.model_name:
            return "mistral"
        else:
            return "claude"
    def _prepare_request_body(
        self,
        prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 4096
    ) -> dict:
        """Prepare model-specific request body"""
        model_type = self._get_model_type()
        
        if model_type == "nova":
            return self._prepare_nova_request(prompt, temperature, max_tokens)
        elif model_type == "llama":
            return self._prepare_llama_request(prompt, temperature, max_tokens)
        elif model_type == "deepseek":
            return self._prepare_deepseek_request(prompt, temperature, max_tokens)
        elif model_type == "mistral":
            return self._prepare_mistral_request(prompt, temperature, max_tokens)
        else:
            return self._prepare_claude_request(prompt, temperature, max_tokens)

    def _prepare_nova_request(self, prompt: str, temperature: float, max_tokens: int) -> dict:
        messages = self.conversation_history + [{"role": "user", "content": [{"text": prompt}]}]
        return {
            "messages": messages,
            "inferenceConfig": {
                "temperature": temperature,
                "maxTokens": max_tokens,
                "topP": 1,
                "topK": 1
            }
        }

    def _prepare_llama_request(self, prompt: str, temperature: float, max_tokens: int) -> dict:
        formatted_text = self._format_conversation_history("llama")
        return {
            "prompt": formatted_text,
            "max_gen_len": max_tokens,
            "temperature": temperature
        }
    def _prepare_deepseek_request(self, prompt: str, temperature: float, max_tokens: int) -> dict:
        formatted_text = self._format_conversation_history("deepseek")
        return {
            "prompt": formatted_text,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": 0.9
        }

    def _prepare_mistral_request(self, prompt: str, temperature: float, max_tokens: int) -> dict:
        formatted_text = self._format_conversation_history("mistral")
        return {
            "prompt": formatted_text,
            "max_tokens": max_tokens,
            "temperature": temperature
        }

    def _prepare_claude_request(self, prompt: str, temperature: float, max_tokens: int) -> dict:
        messages = self.conversation_history + [{"role": "user", "content": prompt}]
        return {
            "anthropic_version": "bedrock-2023-05-31",
            "temperature": temperature,
            "max_tokens": max_tokens,
            "messages": messages
        }

    def _format_conversation_history(self, model_type: str) -> str:
        """Format conversation history based on model type"""
        formatters = {
            "llama": self._format_llama_history,
            "deepseek": self._format_deepseek_history,
            "mistral": self._format_mistral_history
        }
        return formatters[model_type]()
    def _format_llama_history(self) -> str:
        formatted = ""
        for msg in self.conversation_history:
            role = "user" if msg["role"] == "user" else "assistant"
            content = msg["content"]
            if isinstance(content, list):
                content = content[0]["text"]
            formatted += f"""
<|begin_of_text|><|start_header_id|>{role}<|end_header_id|>
{content}
<|eot_id|>
"""
        return formatted + "<|start_header_id|>assistant<|end_header_id|>"

    def _format_deepseek_history(self) -> str:
        formatted = ""
        for msg in self.conversation_history:
            role = "User" if msg["role"] == "user" else "Assistant"
            content = msg["content"]
            if isinstance(content, list):
                content = content[0]["text"]
            formatted += f"<｜{role}｜>{content}"
        return formatted + "<｜Assistant｜><think>\n"

    def _format_mistral_history(self) -> str:
        formatted = ""
        for msg in self.conversation_history:
            role = "user" if msg["role"] == "user" else "assistant"
            content = msg["content"]
            if isinstance(content, list):
                content = content[0]["text"]
            formatted += f"<s>[INST] {content} [/INST]" if role == "user" else f"{content}</s>"
        return formatted
    @retry(
        wait=wait_exponential(multiplier=2, min=10, max=120),
        stop=stop_after_attempt(5),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    def generate_response(
        self,
        prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 4096,
        clear_history: bool = False
    ) -> str:
        """Generate response using Bedrock model with retry logic"""
        if clear_history:
            self.clear_history()

        try:
            request_body = self._prepare_request_body(prompt, temperature, max_tokens)
            response = self.client.invoke_model(
                body=json.dumps(request_body),
                modelId=self.model_name
            )
            
            response_body = json.loads(response.get("body").read())
            return self._extract_response(response_body)
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code in ['ThrottlingException', 'ServiceQuotaExceededException']:
                logger.warning(f"Bedrock throttling error: {str(e)}")
                raise
            logger.exception(e)
            return ""
            
        except Exception as e:
            logger.exception(f"Error generating response: {str(e)}")
            return ""
    def _extract_response(self, response_body: dict) -> str:
        """Extract response text based on model type"""
        model_type = self._get_model_type()
        
        try:
            if model_type == "nova":
                return response_body.get("output", {}).get("message", {}).get("content", [{}])[0].get("text", "")
            elif model_type == "llama":
                return response_body.get("generation", "")
            elif model_type == "deepseek":
                text = response_body.get("choices", [{}])[0].get("text", "")
                return text.split("</think>")[-1].strip() if "</think>" in text else text
            elif model_type == "mistral":
                return response_body.get("choices", [{}])[0].get("message", {}).get("content", "")
            else:  # claude
                return response_body.get("content", [{}])[0].get("text", "")
                
        except Exception as e:
            logger.error(f"Error extracting response: {str(e)}")
            return ""


def get_prompt(top_prompt_dir: str, prompt_id: int, conn: Connection) -> str:
    """Finds the prompt text file within a given input directory and returns it as a string"""
    input_dir = Path(top_prompt_dir) / f'prompt_{prompt_id}' if not isinstance(top_prompt_dir, Path) else top_prompt_dir / f'prompt_{prompt_id}'
    assert input_dir.is_dir()
    assert isinstance(prompt_id, int)
    assert prompt_id > 0

    candidate_files = [x for x in input_dir.glob('prompt_*.txt')]
    if len(candidate_files) > 1:
        raise ValueError(f'More than one prompt found in {input_dir}')

    with open(candidate_files[0], encoding='utf-8', mode='r') as f:
        prompt_txt = f.read()
    try:
        insert_prompt_to_db(conn=conn, prompt_text=prompt_txt, prompt_id=prompt_id)
    except ValueError:
        logging.warning(f'Prompt id={prompt_id} is already in the database')

    return prompt_txt
def run_prompt_from_dir_cli(root_input_prompt_dir: str, prompt_id: int, model: str, output_dir: str,
                        temperature: float, number_of_responses_per_prompt: int, sql_db_name: str, naming_system: str = 'response_id') -> None:
    root_input_prompt_dir = Path(root_input_prompt_dir)
    output_dir = Path(output_dir)
    try:
        temperature = float(temperature)
        prompt_id = int(prompt_id)
        with sqlite3.connect(sql_db_name) as conn:
            init_db_schema(conn)
        run_prompt_from_dir(root_input_prompt_dir, prompt_id, model, output_dir,
                        temperature, number_of_responses_per_prompt, conn, naming_system)

    finally:
        conn.close()


def run_prompt_from_dir(root_input_prompt_dir: str, prompt_id: int, model: str, output_dir: str,
                        temperature: float, number_of_responses_per_prompt: int, conn: Connection, naming_system:
                        typing.Optional[typing.Literal['response_id', 'descriptive']] = None,
                        max_tries: int = 2, region: str = "us-west-2") -> None:
    """
    Run a prompt using AWS Bedrock models

    :param root_input_prompt_dir: Directory containing prompt subdirectories
    :param prompt_id: ID of the prompt to run
    :param model: Bedrock model ID to use
    :param output_dir: Directory to save responses
    :param temperature: Temperature parameter for generation
    :param number_of_responses_per_prompt: Maximum 10
    :param conn: SQLite database connection
    :param naming_system: How to name output files
    :param max_tries: Maximum number of retry attempts
    :param region: AWS region for Bedrock
    """
    assert isinstance(prompt_id, int)
    assert isinstance(temperature, float)
    assert 0 <= temperature <= 1
    assert isinstance(number_of_responses_per_prompt, int)
    assert 0 < number_of_responses_per_prompt < 10
    assert isinstance(model, str)
    if naming_system is None:
        naming_system = os.getenv('DEFAULT_RESPONSE_NAMING_SYSTEM')
    assert naming_system in ['descriptive', 'response_id']

    root_input_prompt_dir = Path(root_input_prompt_dir) if not isinstance(root_input_prompt_dir, Path) else root_input_prompt_dir
    output_dir = Path(output_dir) if not isinstance(output_dir, Path) else output_dir
    output_dir.mkdir(exist_ok=True, parents=True)

    # Initialize the Bedrock assistant
    bedrock_assistant = BedrockAssistant(model_name=model)
    
    # Extract model name for logging and filenames
    model_name_parts = model.split('/')
    if len(model_name_parts) > 1:
        provider_name = model_name_parts[0]
        model_name_part = model_name_parts[-1]
    else:
        provider_name = "bedrock"
        model_name_part = model

    logging.info('Loading prompt')
    prompt_txt = get_prompt(root_input_prompt_dir, prompt_id=prompt_id, conn=conn)

    logging.info('Loaded prompt')
    logging.info(prompt_txt)
    logging.info('Writing prompt to output dir')
    with open(output_dir / f'prompt_{prompt_id}.txt', 'w', encoding='utf-8') as fw:
        fw.write(prompt_txt)
    logging.info('Written prompt to output dir')
    
    if temperature == 0 and number_of_responses_per_prompt > 1:
        logging.warning(
            'The temperature parameter is set to 0, but the number of responses per prompt is more than 1. '
            'Setting the number of response to 1, because response will always be the same')
        number_of_responses_per_prompt = 1
    tries = 0
    for n in range(number_of_responses_per_prompt):
        while tries < max_tries:
            try:
                response_text = bedrock_assistant.generate_response(
                    prompt=prompt_txt,
                    temperature=temperature,
                    max_tokens=max_tokens_response
                )
                
                if not response_text:
                    logging.warning("Empty response received, retrying...")
                    tries += 1
                    continue
                    
                break
            except ClientError as e:
                error_code = e.response['Error']['Code']
                if error_code in ['ThrottlingException', 'ServiceQuotaExceededException']:
                    logging.warning(f"Bedrock throttling error: {str(e)}, retrying...")
                    time.sleep(5)  # Simple backoff
                    tries += 1
                    continue
                else:
                    logging.error(f"Bedrock error: {str(e)}")
                    raise
            except Exception as e:
                logging.error(f"Error generating response: {str(e)}")
                tries += 1
                if tries >= max_tries:
                    logging.error("Max retries reached, giving up")
                    return
                continue
        
        # Reset tries for next response
        tries = 0
        
        # Insert response to database
        response_id = insert_response_to_db(
            conn=conn,
            response_text=response_text,
            prompt_id=prompt_id,
            model_name=model,
            temperature=temperature,
            tools='',
            image_path='',
            llm_provider=provider_name
        )
        # Create filename based on naming system
        if naming_system == 'response_id':
            filename = f'response_{response_id}_chat.txt'
        elif naming_system == 'descriptive':
            model_name_part_for_filename = model_name_part.replace(':', '').replace('/', '').replace('\\', '')
            filename = f'prompt_{prompt_id}_run_{n}_temp_{temperature}_model_{model_name_part_for_filename}_chat.txt'
        else:
            raise NotImplementedError(f'naming_system={naming_system} is not implemented. Double check it is one of the options in the type hint')
        
        # Write response to file
        with open(output_dir / filename, encoding='utf-8', mode='w') as fw:
            fw.write(response_text)
        
        # Update response filename in database
        update_response_filename(conn, response_id, filename)
    
    logging.info('Done.')


if __name__ == '__main__':
    try:
        dotenv.load_dotenv('../.env')

        # Find all prompt directories
        prompt_dirs = [d for d in root_input_prompt_dir.glob('prompt_*') if d.is_dir() and not d.name.startswith('old')]
        
        # Extract prompt IDs from directory names
        prompt_ids = []
        for prompt_dir in prompt_dirs:
            try:
                # Extract the numeric part after 'prompt_'
                prompt_id_str = prompt_dir.name.split('_')[1]
                prompt_id_num = int(prompt_id_str)
                prompt_ids.append(prompt_id_num)
            except (IndexError, ValueError):
                logging.warning(f"Could not extract prompt ID from directory: {prompt_dir}")
                continue
        
        # Sort prompt IDs numerically
        prompt_ids.sort()
        
        logging.info(f"Found {len(prompt_ids)} prompts to process: {prompt_ids}")
        
        with sqlite3.connect(sql_db_name) as conn:
            init_db_schema(conn)
            
            # Process each prompt
            for current_prompt_id in prompt_ids:
                logging.info(f"Processing prompt ID: {current_prompt_id}")
                
                # Create output directory for this prompt
                current_output_dir = root_output_dir / f'prompt_{current_prompt_id}'
                current_output_dir.mkdir(exist_ok=True, parents=True)
                
                try:
                    run_prompt_from_dir(
                        root_input_prompt_dir, 
                        current_prompt_id, 
                        model, 
                        current_output_dir, 
                        temperature, 
                        number_of_responses_per_prompt,
                        conn=conn,
                        region=aws_region
                    )
                except Exception as e:
                    logging.error(f"Error processing prompt {current_prompt_id}: {str(e)}")
                    # Continue with next prompt instead of stopping
                    continue
                
                logging.info(f"Completed processing prompt ID: {current_prompt_id}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()