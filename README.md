
# Setup
1. Install using uv
2. Get `poppler` and unzip
3. Set environment variables in `.env`
4. 
# Notes
To compile markdown text (output by LLMs) to an image, we use fpdf and pdf2image to create an HTML document, 
render it as a PDF and then convert the PDF to an image

A requirement of pdf2image is a library called `poppler`, you can get this from here: https://github.com/oschwartz10612/poppler-windows/releases/

You must set the absolute path to the bin file of the extracted poppler package in `.env`

For more information see the documentation for pdf2image https://pypi.org/project/pdf2image/