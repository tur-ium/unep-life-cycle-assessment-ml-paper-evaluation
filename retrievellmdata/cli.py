import typer

# from get_data_litellm import run_prompt_from_dir, run_prompt_from_dir_cli
from get_data_bedrock import run_prompt_from_dir, run_prompt_from_dir_cli

app = typer.Typer()
app.command()(run_prompt_from_dir_cli)


if __name__ == "__main__":
    app()