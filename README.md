
The focus of this repository is preparing responses from a ML model for use in the Zooniverse platform for review


# Setup
1. Install using uv
2. Get `poppler` and unzip
3. Set environment variables in `.env`

# How to use:
1. Ensure the setup steps above are complete, including the poppler and api tokens
2. Run `get_data_mistral.py` to get data from the Mistral API for an example query, and compile the markdown of the prompt and response into an image (required for Zooniverse)
3. Run `make_manifest_for_each_subject_set.py`, configuring the parameters in the script file to the folder containing the images and prompt texts from the RAG script

# Outputs
1. A folder containing the images and a .csv manifest file necessary for the Zooniverse project
2. A SQLite database containing the prompts and metadata for tracing the prompt and image ids to the original ML model and prompt

# Notes
To compile markdown text (output by LLMs) to an image, we use fpdf and pdf2image to create an HTML document, 
render it as a PDF and then convert the PDF to an image

A requirement of `pdf2image` is a library called `poppler`, you can get this from here: https://github.com/oschwartz10612/poppler-windows/releases/

You must set the absolute path to the bin file of the extracted poppler package in `.env`

For more information see the documentation for `pdf2image` https://pypi.org/project/pdf2image/

Please note there is an open issue with 