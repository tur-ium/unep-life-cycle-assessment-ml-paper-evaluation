from pathlib import Path

import pandas as pd
from retrievellmdata.utils import save_text_as_img_markdown

# INPUT PARAMETERS
prompt_excel_path = '20250428_Prompts.xlsx'
sheet_name = 'prompt_list'
prompts_dir = 'prompts'
# END INPUT PARAMETERS
expected_columns = ['LCA stage','Task_type','Problem_type','Prompt','Answer','Explanation']
df = pd.read_excel(prompt_excel_path, sheet_name=sheet_name, engine='openpyxl')

prompts_dir = Path(prompts_dir)
# Check that the columns are exactly the same (could be different orders)
assert all([c in expected_columns for c in df.columns])
assert all([c in df.columns for c in expected_columns])

prompt_dict = df.to_dict(orient='index')

for index, prompt in prompt_dict.items():
    prompt_id = index+1
    print(f'{prompt_id}/{len(prompt_dict)}')
    output_prompt_dir = prompts_dir / f'prompt_{prompt_id}'
    output_prompt_path = output_prompt_dir / f'prompt_{prompt_id}.txt'
    output_prompt_dir.mkdir(exist_ok=False)
    prompt_text = prompt['Prompt']
    with open(output_prompt_path, encoding='utf-8',mode='w') as fw:
        fw.write(prompt_text)
    save_text_as_img_markdown(prompt_text, output_path=output_prompt_dir / f'prompt_{prompt_id}.png')
print('Done.')