import sqlite3
import pandas as pd
import typer
from pathlib import Path

app = typer.Typer()

@app.command()
def view_full_responses(
    db_path: str = "records.db",
    prompt_id: int = None,
    response_id: int = None
):
    """View full response text for prompts in the database"""
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            if response_id:
                # Get specific response by ID
                query = """
                    SELECT p.prompt_id, r.response_id, p.prompt_text, r.model_name, r.response_text
                    FROM responses r
                    JOIN prompts p ON p.prompt_id = r.prompt_id
                    WHERE r.response_id = ?
                """
                cursor.execute(query, (response_id,))
                results = cursor.fetchall()
            elif prompt_id:
                # Get all responses for a specific prompt
                query = """
                    SELECT p.prompt_id, r.response_id, p.prompt_text, r.model_name, r.response_text
                    FROM responses r
                    JOIN prompts p ON p.prompt_id = r.prompt_id
                    WHERE p.prompt_id = ?
                    ORDER BY r.created_at DESC
                """
                cursor.execute(query, (prompt_id,))
                results = cursor.fetchall()
            else:
                # Get all responses, most recent first for each prompt
                query = """
                    SELECT p.prompt_id, r.response_id, p.prompt_text, r.model_name, r.response_text
                    FROM responses r
                    JOIN prompts p ON p.prompt_id = r.prompt_id
                    ORDER BY p.prompt_id, r.created_at DESC
                """
                cursor.execute(query)
                results = cursor.fetchall()
                
                # Keep only the most recent response for each prompt
                seen_prompts = set()
                filtered_results = []
                for result in results:
                    prompt_id = result[0]
                    if prompt_id not in seen_prompts:
                        seen_prompts.add(prompt_id)
                        filtered_results.append(result)
                results = filtered_results
            
            if not results:
                typer.echo("No responses found.")
                return
                
            # Display the results
            for prompt_id, response_id, prompt_text, model_name, response_text in results:
                typer.echo(f"\n{'='*80}")
                typer.echo(f"PROMPT {prompt_id} (Response ID: {response_id}, Model: {model_name})")
                typer.echo(f"{'-'*80}")
                typer.echo(f"PROMPT TEXT:\n{prompt_text}")
                typer.echo(f"{'-'*80}")
                typer.echo(f"RESPONSE TEXT:\n{response_text}")
                typer.echo(f"{'='*80}\n")
                
    except sqlite3.Error as e:
        typer.echo(f"Error accessing database: {e}")

if __name__ == "__main__":
    app()