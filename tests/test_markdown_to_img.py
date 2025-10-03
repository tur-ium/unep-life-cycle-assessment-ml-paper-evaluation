from pathlib import Path

import pytest

from retrievellmdata.utils import save_text_as_img_markdown

expected_outputs_dir = Path('expected_outputs')
output_test_dir = Path('test_outputs/txt_to_img_tests')

poppler_path = r"C:\windows\path\to\llm testing\Zooniverse project\poppler\poppler-24.08.0\Library\bin"
@pytest.mark.parametrize('md_text,output_path,expected_output_path',
                         [(r'# Hello __world__',str(output_test_dir/'test_markdown.png'),expected_outputs_dir / 'test_utf8_markdown_expected.png'),
                          ("""Your task is to match items in a bill of materials to the best matching description of the item from a list of available models of the production of products in the excel file attached.
                          
The look up string, in the column 'lookup_string' in the excel, consists of four parts – the reference product, the region from which the product is supplied, the manufacturing activity that produces it, and a suffix 'Cut-off, U', that does not change in this database. There can be different models for different geographical regions, where most are ISO 2-letter code e.g. 'AT' for Austria. If the region is not known the region 'GLO' standing for 'Global', or 'RoW', standing for 'Rest of the World' is used. In this database a unique 'lookup string' is created following the pattern '<product name> {<2-letter ISO Code for region>} | <activity name> | Cut-off, U'. Give your answer in json format {'best_lookup_string': <lookup_string>}. 

If there is no suitable match, return {'best_lookup_string: null}. Provide an explanation

Example 1: 'raw bauxite ore' -> {'best_lookup_string': 'bauxite {GLO}| bauxite mine operation | Cut-off, U'}

Example 2: 'shelled cashews' -> {'best_lookup_string': 'cashew {IN}| cashew production | Cut-off, U'}

Following these examples match the following dataset: 'Maize starch, citric acid' sourced from China.
""",output_test_dir/'test_utf8_markdown.png',expected_outputs_dir / 'hello_world.png')])
def test_markdown_to_img(md_text: str,output_path:str,expected_output_path:str):
    save_text_as_img_markdown(md_text=md_text, output_path = output_path,font_family='arial',font_size=16,poppler_path=poppler_path)
