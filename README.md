
The focus of this repository is preparing responses from a ML model for use in the Zooniverse platform for review


# Setup
1. Install requirements using `uv sync`
2. Get `poppler` from [here](https://github.com/oschwartz10612/poppler-windows/releases) and unzip to suitable location
3. Set environment variables in `.env`. The POPPLER_PATH should point to the `\Library\bin` sub-directory of extracted poppler file

# How to use:
1. Ensure the setup steps above are complete, filling in the api tokens for the api's you will use, using LiteLLM syntax. For Ollama you only need the OLLAMA_API_BASE. For more information see here: 
2. Put the prompt you want to run in a text file prompts/prompt<prompt_id>/prompt_<prompt_id>.txt
3. Run prompt retrieval from the cli for local ollama
```shell
ollama run mistral:latest
nano .env
# Set OLLAMA_API_BASE = 'localhost:11434' in .env
python .\retrieve-llm-data\cli.py .\prompts\ <prompt_id> ollama_chat/mistral:latest .\outputs\ 0 1 records.db
```
3. Run prompt retrieval from the cli for mistral 
```shell
nano .env
# Set MISTRAL_API_KEY in .env
python .\retrieve-llm-data\cli.py .\prompts\ <prompt_id> mistral/mistral-large-latest .\outputs\ 0 1 records.db
````
### Outputs
1. A folder containing the chat txt
2. A log file
3. Records in a sqlite database

## How to use to collate results for Zooniverse
Run `make_manifest_for_each_subject_set.py`, configuring the parameters in the script file to the folder containing the images and prompt texts from the RAG script

###  Outputs
2. Png renders of the prompt and response from each model
3. A .csv manifest file necessary for the Zooniverse project
4. A SQLite database containing the prompts and metadata for tracing the prompt and image ids to the original ML model and prompt

# Notes
To compile markdown text (output by LLMs) to an image, we use fpdf and pdf2image to create an HTML document, 
render it as a PDF and then convert the PDF to an image

A requirement of `pdf2image` is a library called `poppler`, you can get this from here: https://github.com/oschwartz10612/poppler-windows/releases/

You must set the absolute path to the bin file of the extracted poppler package in `.env`

For more information see the documentation for `pdf2image` https://pypi.org/project/pdf2image/

Please note there is an open issue with 