from pathlib import Path
from typing import Tuple

from fpdf.errors import FPDFUnicodeEncodingException
from pdf2image import convert_from_bytes
from fpdf import FPDF
import markdown

from PIL import ImageFont


def save_text_as_img(text: str, output_path: Path | str, dimensions: Tuple[int, int],
                     background_colour: Tuple[int, int, int] = (255, 255, 255),
                     text_colour: Tuple[int, int, int] = (0, 0, 0), text_pos: Tuple[int, int] = (0, 0),
                     text_img_width_fraction=0.95,text_font_name:str = "arial.ttf"):
    from PIL import Image, ImageDraw

    assert isinstance(text,str)
    assert isinstance(dimensions,tuple)
    assert len(dimensions)==2
    assert all([isinstance(x,int) for x in dimensions])

    img = Image.new('RGB', dimensions,color=background_colour)
    d = ImageDraw.Draw(img)

    text_size = 1
    font = ImageFont.truetype(text_font_name, text_size)

    while font.font.getsize(text)[0][0] < text_img_width_fraction * img.size[0]:
        # iterate until the text size is just larger than the criteria
        text_size += 1
        font = ImageFont.truetype(text_font_name, text_size)

    d.text(text_pos, text, fill=text_colour,font=font)
    with open(output_path,'wb') as fw:
        img.save(fw, 'png')


def save_text_as_img_markdown(md_text:str,output_path:str|Path,font_family:str="dejavusans",font_size:int=16,poppler_path='poppler/poppler-24.08.0/Library/bin'):

    # Parse Markdown to HTML
    html = markdown.markdown(md_text)

    # Create a PDF object
    pdf = FPDF()
    try:
        # Add the HTML to the PDF
        pdf.add_page()
        pdf.add_font("dejavusans", fname=r"C:\Users\Artur\Documents\Projects (local)\GLAD AI\llm testing\Zooniverse project\media\fonts\dejavu-sans\DejaVuSans.ttf")
        pdf.add_font("dejavusans",style="B",
                     fname=r"C:\Users\Artur\Documents\Projects (local)\GLAD AI\llm testing\Zooniverse project\media\fonts\dejavu-sans\DejaVuSans-Bold.ttf")
        pdf.set_font("dejavusans", style='', size=font_size)
        pdf.set_text_color(0,0,0)
        pdf.write_html(html,font_family=font_family)
    except FPDFUnicodeEncodingException as e:
        raise e
    # Save the PDF to a bytes buffer
    pdf_buffer = pdf.output(dest='S')
    pdf.output(f'output_path.pdf')

    # Convert the PDF to an image
    images = convert_from_bytes(pdf_buffer,poppler_path=poppler_path)

    # Save the image to a file
    images[0].save(output_path)
