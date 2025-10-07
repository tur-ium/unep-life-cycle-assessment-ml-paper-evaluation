LCA and AI Benchmark toolkit
============================
This repository contains a collection of scripts to help with creating an expert benchmark of AI responses to LCA tasks,
with a focus on factual knowledge answering.

This repository accompanies the paper __Expert benchmark of LLMs for LCA tasks__ by Artur Donaldson, Bharathan Balaji, Cajetan Oriekezie, Manish Kumar and Laure Patouillard.

# Structure
1. `1_input_prompts`: The input prompts used
2. `retrieval_llm_data` and `retrievellmdata_ollama`: Scripts to retrieve responses from LLMs
3. `2_retrieved_responses`: Retrieved responses
4. `3_survey_creation`: Scripts to create a survey for expert evaluation
5. `4_survey_responses`: Anonymized survey responses collected via the Zooniverse platform
6. `5_analysis`: Analysis of survey responses
7. `tests`: Tests used in development

# Setup
1. Install requirements using `uv sync`
2. If creating your own survey via Zooniverse, 
   2.1 get `poppler` from [here](https://github.com/oschwartz10612/poppler-windows/releases) and unzip to suitable location
   2.2 Set environment variables in `.env`. The POPPLER_PATH should point to the `\Library\bin` sub-directory of extracted poppler file

# Usage Guide

## 1. Retrieving Responses from LLMs

This section covers how to retrieve responses from various LLM providers for your prompts.

### Prerequisites
1. Ensure the setup steps above are complete, filling in the API tokens for the APIs you will use, using LiteLLM syntax. For Ollama you only need the OLLAMA_API_BASE. For more information see here: 
2. Put the prompt you want to run in a text file `prompts/prompt<prompt_id>/prompt_<prompt_id>.txt`

### Running Retrieval

#### For Local Ollama
```shell
ollama run mistral:latest # Or the name of the model you wish to test
nano .env
# Set OLLAMA_API_BASE = 'localhost:11434' in .env
python .\retrieve-llm-data\cli.py .\prompts\ <prompt_id> ollama_chat/mistral:latest .\outputs\ 0 1 records.db
```

#### For Mistral API
```shell
nano .env
# Set MISTRAL_API_KEY in .env
python .\retrieve-llm-data\cli.py .\prompts\ <prompt_id> mistral/mistral-large-latest .\outputs\ 0 1 records.db
```

### Outputs
- A folder containing the chat txt files
- A log file
- Records in a SQLite database

## 2. Creating a Survey

This section covers how to prepare your LLM responses for expert evaluation using Zooniverse.

### Process
Run `make_zooniverse.py`, configuring the parameters in the script file to the folder containing the images and prompt texts from the retrieval script.

See the paper for final analysis

### Outputs
- PNG renders of the prompt and response from each model
- A .csv manifest file necessary for the Zooniverse project
- A SQLite database containing the prompts and metadata for tracing the prompt and image ids to the original ML model and prompt

## 3. Analysis of Reviews

An analysis of the reviews is covered by the Jupyter notebooks in the folder `5_analysis`

# Technical Notes

## Image Generation Process
To compile markdown text (output by LLMs) to an image, we use fpdf and pdf2image to create an HTML document, render it as a PDF and then convert the PDF to an image.

## Poppler Requirements
A requirement of `pdf2image` is a library called `poppler`. You can get this from here: https://github.com/oschwartz10612/poppler-windows/releases/

You must set the absolute path to the bin file of the extracted poppler package in `.env`

For more information see the documentation for `pdf2image`: https://pypi.org/project/pdf2image/
