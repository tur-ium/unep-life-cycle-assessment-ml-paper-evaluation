import typer
import pandas as pd
from pathlib import Path

from get_data_litellm import run_prompt_from_dir, run_prompt_from_dir_cli

# Create Typer app and add the original command
app = typer.Typer()
app.command()(run_prompt_from_dir_cli)

def convert_excel_to_csv(excel_path, csv_path):
    """
    Converts an Excel file to CSV format
    """
    try:
        # Read the Excel file
        df = pd.read_excel(excel_path)
        
        # Save as CSV
        df.to_csv(csv_path, index=False)
        
        print(f"Excel file converted to CSV: {csv_path}")
        return True
    
    except Exception as e:
        print(f"Error converting Excel to CSV: {e}")
        return False

def read_prompts_from_csv(csv_path, prompt_column='Prompt'):
    """
    Reads prompts from a CSV file and returns a dictionary of prompt_id: prompt_text
    """
    try:
        # Read the CSV file
        df = pd.read_csv(csv_path)
        
        # Map to store prompt_id and corresponding prompt_text
        prompts_dict = {}
        
        # Loop through each row in the dataframe
        for index, row in df.iterrows():
            # Create a prompt ID (you might want to use a different logic)
            prompt_id = index + 1
            
            # Extract the prompt text from the specified column
            prompt_text = row[prompt_column]
            
            # Store in the dictionary
            prompts_dict[prompt_id] = prompt_text
            
        return prompts_dict
    
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return {}

def save_prompts_to_files(prompts_dict, root_input_prompt_dir):
    """
    Saves prompts from dictionary to text files in the prompt directory structure
    """
    root_dir = Path(root_input_prompt_dir)
    
    for prompt_id, prompt_text in prompts_dict.items():
        # Create the prompt directory
        prompt_dir = root_dir / f'prompt_{prompt_id}'
        prompt_dir.mkdir(exist_ok=True, parents=True)
        
        # Create the prompt file
        prompt_file = prompt_dir / f'prompt_{prompt_id}.txt'
        with open(prompt_file, 'w', encoding='utf-8') as f:
            f.write(prompt_text)
            
    print(f"Saved {len(prompts_dict)} prompts to files in {root_input_prompt_dir}")
    return True

# Add the new Excel command
@app.command()
def from_excel(
    excel_path: str = typer.Option(..., help="Path to Excel file containing prompts"),
    root_input_prompt_dir: str = typer.Option(..., help="Root directory for prompt files"),
    model: str = typer.Option(..., help="Model identifier"),
    output_dir: str = typer.Option(..., help="Output directory for responses"),
    temperature: float = typer.Option(0.7, help="Temperature parameter for model"),
    number_of_responses_per_prompt: int = typer.Option(1, help="Number of responses per prompt"),
    sql_db_name: str = typer.Option("../records.db", help="SQLite database file name"),
    naming_system: str = typer.Option("response_id", help="Naming system for responses"),
    prompt_column: str = typer.Option("Prompt", help="Column name containing prompts in Excel file")
):
    """Process prompts from Excel file and run them through LLM models"""
    # Create CSV in the same directory as Excel
    excel_path = Path(excel_path)
    csv_path = excel_path.parent / f"{excel_path.stem}.csv"
    
    # Convert Excel to CSV
    convert_excel_to_csv(excel_path, csv_path)
    
    # Read prompts from CSV
    prompts_dict = read_prompts_from_csv(csv_path, prompt_column)
    
    # Save prompts to files
    save_prompts_to_files(prompts_dict, root_input_prompt_dir)
    
    # Run each prompt through the model
    for prompt_id in prompts_dict.keys():
        typer.echo(f"Running prompt {prompt_id}")
        run_prompt_from_dir_cli(
            root_input_prompt_dir=root_input_prompt_dir,
            prompt_id=prompt_id,
            model=model,
            output_dir=output_dir,
            temperature=temperature,
            number_of_responses_per_prompt=number_of_responses_per_prompt,
            sql_db_name=sql_db_name,
            naming_system=naming_system
        )

if __name__ == "__main__":
    app()