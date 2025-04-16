import typer

from get_data_litellm import run_prompt_from_dir


app = typer.Typer()
app.command()(run_prompt_from_dir)


if __name__ == "__main__":
    app()