import time
from pathlib import Path

import dotenv
import os
import tqdm

from mistralai import Mistral
import numpy as np
import faiss

from utils import save_text_as_img, save_text_as_img_markdown

# PARAMETERS
input_list_of_processes = '../lookup_strings_list.csv'
model = "mistral-large-latest"
embedding_model = "mistral-embed"
rate_limit = 0.4 #  requests per second max
mistral_model_name = "mistral-large-latest"
k_matches_from_embedding = 5
prompt_id: int = 10
root_output_dir = Path('../outputs')
# END PARAMETERS

output_dir = root_output_dir / f'prompt_{prompt_id}'
output_dir.mkdir(exist_ok=True,parents=True)

dotenv.load_dotenv('../.env')
mistral_api_key = os.getenv('MISTRAL_API_KEY')
poppler_path = os.getenv('POPPLER_PATH') # For rendering markdown to image

client = Mistral(api_key=mistral_api_key)

with open(input_list_of_processes,'r') as f:
    lca_model_lookup_list = [x.strip() for x in f.readlines()[1:]]

print(lca_model_lookup_list)

def get_text_embedding(input,embedding_model):
    embeddings_batch_response = client.embeddings.create(
          model=embedding_model,
          inputs=input,
      )
    return embeddings_batch_response.data[0].embedding
# Create an embedding for each process-product lookup
text_embeddings = []
wait_time_embedding_requests = 1. / rate_limit

print(f'Embedding LCA model lookups (rate limit: {rate_limit} requests/s)')
progbar_embed = tqdm.tqdm(lca_model_lookup_list)
for chunk in progbar_embed:
    text_embeddings.append(get_text_embedding(chunk,embedding_model=embedding_model))
    time.sleep(wait_time_embedding_requests)

text_embeddings = np.array(text_embeddings)
d = text_embeddings.shape[1]
print(f'Got {text_embeddings.shape[0]} text embeddings with dimension {d}')

print('Indexing the embeddings with faiss')
index = faiss.IndexFlatL2(d)
index.add(text_embeddings)
print('Done indexing')

question = """Your task is to match items in a bill of materials to the best matching description of the item from a list of available models of the production of products in the excel file attached.
The look up string, in the column 'lookup_string' in the excel, consists of four parts – the reference product, the region from which the product is supplied, the manufacturing activity that produces it, and a suffix 'Cut-off, U', that does not change in this database. There can be different models for different geographical regions, where most are ISO 2-letter code e.g. 'AT' for Austria. If the region is not known the region 'GLO' standing for 'Global', or 'RoW', standing for 'Rest of the World' is used. In this database a unique 'lookup string' is created following the pattern '<product name> {<2-letter ISO Code for region>} | <activity name> | Cut-off, U'. Give your answer in json format {'best_lookup_string': <lookup_string>}. If there is no suitable match, return {'best_lookup_string: null}. Provide an explanation
Example 1: 'raw bauxite ore' -> {'best_lookup_string': 'bauxite {GLO}| bauxite mine operation | Cut-off, U'}
Example 2: 'shelled cashews' -> {'best_lookup_string': 'cashew {IN}| cashew production | Cut-off, U'}
Following these examples match the following dataset: 'Maize starch, citric acid' sourced from China.
"""
print('Embedding the question')
question_embeddings = np.array([get_text_embedding(question,embedding_model=embedding_model)])
print('Done embedding the question')
print('question embeddings',question_embeddings)

D, I = index.search(question_embeddings, k=k_matches_from_embedding) # distance, index
retrieved_chunk = [lca_model_lookup_list[i] for i in I.tolist()[0]]

prompt = f"""
Context information is below.
---------------------
{retrieved_chunk}
---------------------
Given the context information and not prior knowledge, answer the query.
Query: {question}
Answer:
"""

def run_mistral(user_message, model):
    messages = [
        {
            "role": "user", "content": user_message
        }
    ]
    chat_response = client.chat.complete(
        model=model,
        messages=messages
    )
    return (chat_response.choices[0].message.content)

print('Running prompt')
print(prompt)
save_text_as_img_markdown(prompt, output_dir / f'prompt.png', poppler_path=poppler_path)

response = run_mistral(prompt,model=mistral_model_name)
print(f'Done, the answer is\n{response}')

with open(output_dir / f'{mistral_model_name}_chat.md', 'w') as fw:
    fw.write(response)

save_text_as_img_markdown(md_text=response, output_path = str(output_dir / f'{mistral_model_name}_response.png'),poppler_path = poppler_path)
