import pandas as pd
import sqlite3
import os
import typer
import requests
import json
import sys
from pathlib import Path
from tqdm import tqdm
import time

app = typer.Typer()

def check_ollama_available():
    """Check if Ollama API is available"""
    try:
        response = requests.get("http://localhost:11434/api/version", timeout=2)
        return response.status_code == 200
    except requests.RequestException:
        return False

def init_db(db_path):
    """Initialize the database with required tables"""
    db_path = Path(db_path).resolve()
    try:
        db_path.parent.mkdir(exist_ok=True, parents=True)
        with sqlite3.connect(str(db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS prompts (
                prompt_id INTEGER PRIMARY KEY,
                prompt_text TEXT
            )
            ''')
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS responses (
                response_id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt_id INTEGER,
                model_name TEXT,
                temperature REAL,
                response_text TEXT,
                response_filename TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (prompt_id) REFERENCES prompts (prompt_id)
            )
            ''')
            conn.commit()
        return True
    except sqlite3.Error as e:
        typer.echo(f"Database initialization failed: {e}")
        return False

def read_excel_prompts(excel_path, prompt_column='Prompt'):
    """Read prompts from Excel file"""
    excel_path = Path(excel_path).resolve()
    if not excel_path.exists():
        typer.echo(f"Error: Excel file not found at {excel_path}")
        return {}
    
    try:
        df = pd.read_excel(excel_path)
        if prompt_column not in df.columns:
            typer.echo(f"Error: Column '{prompt_column}' not found in Excel file. Available columns: {', '.join(df.columns)}")
            return {}
        return {index + 1: row[prompt_column] for index, row in df.iterrows() if not pd.isna(row[prompt_column])}
    except Exception as e:
        typer.echo(f"Error reading Excel file: {e}")
        return {}

def save_prompt_to_file(prompt_id, prompt_text, input_dir):
    """Save a prompt to a text file"""
    input_dir = Path(input_dir).resolve()
    try:
        prompt_dir = input_dir / f"prompt_{prompt_id}"
        prompt_dir.mkdir(exist_ok=True, parents=True)
        prompt_file = prompt_dir / f"prompt_{prompt_id}.txt"
        with open(prompt_file, "w", encoding="utf-8") as f:
            f.write(prompt_text)
        return prompt_file
    except Exception as e:
        raise IOError(f"Error saving prompt {prompt_id} to file: {e}")

def save_prompt_to_db(prompt_id, prompt_text, db_path):
    """Save a prompt to the database"""
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT prompt_id FROM prompts WHERE prompt_id = ?", (prompt_id,))
            if not cursor.fetchone():
                cursor.execute("INSERT INTO prompts (prompt_id, prompt_text) VALUES (?, ?)", (prompt_id, prompt_text))
            conn.commit()
    except Exception as e:
        raise sqlite3.DatabaseError(f"Error saving prompt {prompt_id} to database: {e}")

def call_model(model, prompt_text, temperature=0.0, max_tokens=2048, timeout=600, max_retries=3):
    """Call the model using Ollama's API directly with streaming to avoid timeouts"""
    endpoint = "http://localhost:11434/api/chat"
    model_name = model.replace("ollama_chat/", "")
    data = {
        "model": model_name,
        "messages": [{"role": "user", "content": prompt_text}],
        "options": {"temperature": temperature, "num_predict": max_tokens},
        "stream": True  # Set to True to use streaming mode
    }
    
    for attempt in range(max_retries):
        try:
            full_response = ""
            with requests.post(endpoint, json=data, timeout=timeout, stream=True) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if line:
                        try:
                            chunk = json.loads(line)
                            if "message" in chunk and "content" in chunk["message"]:
                                content = chunk["message"]["content"]
                                full_response += content
                                # Print a dot to show progress without spamming the console
                                print(".", end="", flush=True)
                        except json.JSONDecodeError:
                            continue
            print()  # New line after the dots
            return full_response
        except (requests.RequestException, ValueError) as e:
            if attempt == max_retries - 1:
                # Last attempt failed, raise the exception
                if isinstance(e, requests.RequestException):
                    raise ConnectionError(f"Error connecting to Ollama API after {max_retries} attempts: {e}")
                raise e
            else:
                # Wait and retry with exponential backoff
                wait_time = 2 ** attempt
                typer.echo(f"Attempt {attempt+1} failed: {e}. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)

def save_response(prompt_id, model, temperature, response_text, output_dir, db_path, naming_system="descriptive", debug=False):
    """Save a response to a file and to the database"""
    output_dir = Path(output_dir).resolve()
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Print debug info about what we're looking for
            if debug:
                typer.echo(f"Checking for existing responses for prompt_id={prompt_id}, model='{model}'")
                cursor.execute("SELECT response_id, model_name FROM responses WHERE prompt_id = ?", (prompt_id,))
                results = cursor.fetchall()
                if results:
                    typer.echo(f"Found responses: {results}")
            
            # Normalize the model name to ensure consistent matching
            normalized_model = model.strip().lower()
            
            # Check if a response for this prompt+model combination already exists
            # Use LIKE for more flexible matching
            cursor.execute(
                "SELECT response_id FROM responses WHERE prompt_id = ? AND LOWER(model_name) = ?",
                (prompt_id, normalized_model)
            )
            existing = cursor.fetchone()
            
            if existing:
                # Update existing response
                response_id = existing[0]
                cursor.execute(
                    "UPDATE responses SET temperature = ?, response_text = ?, created_at = CURRENT_TIMESTAMP WHERE response_id = ?",
                    (temperature, response_text, response_id)
                )
                typer.echo(f"Updated existing response for prompt {prompt_id} with model {model}")
            else:
                # Insert new response
                cursor.execute(
                    "INSERT INTO responses (prompt_id, model_name, temperature, response_text) VALUES (?, ?, ?, ?)",
                    (prompt_id, model, temperature, response_text)
                )
                response_id = cursor.lastrowid
            
            # Generate filename and save to file
            output_path = output_dir / f"prompt_{prompt_id}"
            output_path.mkdir(exist_ok=True, parents=True)
            if naming_system == "descriptive":
                model_name_clean = model.replace(":", "").replace("/", "_").replace("\\", "_")
                filename = f"prompt_{prompt_id}_run_0_temp_{temperature}_model_{model_name_clean}_chat.txt"
            else:
                filename = f"response_{response_id}_chat.txt"
            file_path = output_path / filename
            
            # Write response to file
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(response_text)
            
            # Update filename in database
            cursor.execute(
                "UPDATE responses SET response_filename = ? WHERE response_id = ?",
                (filename, response_id)
            )
            conn.commit()
        return filename
    except Exception as e:
        raise IOError(f"Error saving response for prompt {prompt_id}: {e}")

@app.command()
def process_excel(
    excel_path: str = typer.Option(..., help="Path to Excel file with prompts"),
    model: str = typer.Option(..., help="Model name (e.g., 'gemma3:27b')"),
    temperature: float = typer.Option(0.0, help="Temperature for generation"),
    max_tokens: int = typer.Option(2048, help="Maximum tokens to generate"),
    output_dir: str = typer.Option("../outputs", help="Directory for outputs"),
    input_dir: str = typer.Option("../prompts", help="Directory for prompt files"),
    db_path: str = typer.Option("../records.db", help="Path to SQLite database"),
    prompt_column: str = typer.Option("Prompt", help="Column in Excel containing prompts"),
    naming_system: str = typer.Option("descriptive", help="Naming system (descriptive or response_id)"),
    timeout: int = typer.Option(600, help="Timeout for API calls (seconds)"),  # Increased default
    max_retries: int = typer.Option(3, help="Maximum number of retries for API calls"),
    continue_on_error: bool = typer.Option(False, help="Continue processing other prompts if one fails"),
    debug: bool = typer.Option(False, help="Enable debug mode for more detailed output"),
    resume: bool = typer.Option(False, help="Resume from the last successful prompt")
):
    """Process prompts from Excel file and run them through the model"""
    if debug:
        typer.echo(f"Debug mode enabled")
        typer.echo(f"Current working directory: {os.getcwd()}")
        typer.echo(f"Excel path: {excel_path}")
        typer.echo(f"Database path: {db_path}")
        typer.echo(f"Input directory: {input_dir}")
        typer.echo(f"Output directory: {output_dir}")
    
    # Check if Ollama API is available
    if not check_ollama_available():
        typer.echo("Error: Ollama API is not available. Make sure Ollama is running at http://localhost:11434")
        return
    
    # Initialize database
    if not init_db(db_path):
        typer.echo("Failed to initialize database. Exiting.")
        return
    
    # Ensure model name is formatted correctly
    if not model.startswith("ollama_chat/"):
        model = f"ollama_chat/{model}"
    
    # Read prompts from Excel
    prompts = read_excel_prompts(excel_path, prompt_column)
    if not prompts:
        typer.echo("No prompts found. Exiting.")
        return
    
    # Create directories
    Path(input_dir).resolve().mkdir(exist_ok=True, parents=True)
    Path(output_dir).resolve().mkdir(exist_ok=True, parents=True)
    
    # Check if we should resume from the last processed prompt
    processed_prompts = set()
    if resume:
        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT DISTINCT prompt_id FROM responses WHERE model_name = ?", (model,))
                processed_prompts = {row[0] for row in cursor.fetchall()}
                if processed_prompts:
                    typer.echo(f"Resuming: {len(processed_prompts)} prompts already processed with model {model}")
        except sqlite3.Error as e:
            typer.echo(f"Error checking for processed prompts: {e}")

    # Then only process prompts not already done
    prompts_to_process = {pid: ptext for pid, ptext in prompts.items() if pid not in processed_prompts}
    
    # Process prompts
    typer.echo(f"Processing {len(prompts_to_process)} prompts with model {model}...")
    progress_bar = tqdm(prompts_to_process.items(), total=len(prompts_to_process))
    
    for prompt_id, prompt_text in progress_bar:
        progress_bar.set_description(f"Processing prompt {prompt_id}")
        try:
            if debug:
                typer.echo(f"\nProcessing prompt {prompt_id}: {prompt_text[:50]}...")
            
            save_prompt_to_file(prompt_id, prompt_text, input_dir)
            save_prompt_to_db(prompt_id, prompt_text, db_path)
            
            if debug:
                typer.echo(f"Calling model {model}...")
                
            response_text = call_model(model, prompt_text, temperature, max_tokens, timeout, max_retries)
            
            if debug:
                typer.echo(f"Got response of length {len(response_text)}")
                
            filename = save_response(
                prompt_id, 
                model, 
                temperature, 
                response_text, 
                output_dir, 
                db_path, 
                naming_system,
                debug=debug  # Pass the debug parameter
            )
            progress_bar.set_postfix_str(f"Saved as {filename}")
            
            if debug:
                typer.echo(f"Saved response as {filename}")
                
        except Exception as e:
            typer.echo(f"Error processing prompt {prompt_id}: {e}")
            if debug:
                import traceback
                typer.echo(traceback.format_exc())
            
            if not continue_on_error:
                typer.echo("Stopping due to error. Use --continue-on-error to process remaining prompts.")
                return
    
    typer.echo(f"Completed processing {len(prompts_to_process)} prompts.")

if __name__ == "__main__":
    app()