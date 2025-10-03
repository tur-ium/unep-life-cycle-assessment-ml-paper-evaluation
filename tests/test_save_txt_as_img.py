from pathlib import Path

import pytest
from PIL import Image, ImageChops

from utils import save_text_as_img

expected_outputs_dir = Path('expected_outputs')
output_test_dir = Path('test_outputs/txt_to_img_tests')

output_test_dir.mkdir(exist_ok=True,parents=True)
@pytest.mark.parametrize('text,dimensions,benchmark_img_path',
                         [('Hello world!',(1024,256),expected_outputs_dir / 'hello_world.png'),])
def test_save_text_as_img(text,dimensions,benchmark_img_path):
    # We're dealing with pngs, so we need to convert to RGB so we don't compare transparency
    benchmark_img = Image.open(benchmark_img_path).convert('RGB')
    output_image_path = output_test_dir / 'text.png'

    save_text_as_img(text=text, output_path=output_image_path, dimensions=dimensions, text_colour=(0, 0, 0))
    output_image = Image.open(output_image_path).convert('RGB')
    # Compare images using ImageChops
    diff = ImageChops.difference(benchmark_img,output_image)

    assert diff.getbbox() is None
