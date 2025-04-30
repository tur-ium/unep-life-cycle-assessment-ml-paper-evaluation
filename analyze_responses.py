"""
This script loads in responses from classification csv file output by Zooniverse,
and normalizes them into a table with one row per task answered
"""
import json
from pathlib import Path

import pandas as pd

classifications_csv_path = 'survey_responses/review-llm-responses-on-lca-tasks-classifications.csv'
output_dir = 'survey_responses/analysis'

output_dir = Path(output_dir)
output_dir.mkdir(parents=True,exist_ok=True)

classifications_df = pd.read_csv(classifications_csv_path)

annotations_df_list = []
workflow_ids = classifications_df.value_counts('workflow_id')
assert workflow_ids.shape[0] == 1
workflow_id = workflow_ids.iloc[0]

classification_id = classifications_df.classification_id

classification_records = classifications_df.to_dict(orient='index')
for index, row in classification_records.items():
    classification_id = row['classification_id']
    user_id = row['user_id']
    annotation = row['annotations']
    json_obj = json.loads('{"annotations":' + annotation + '}')
    annotation_df = pd.json_normalize(json_obj,record_path='annotations')
    annotation_df['classification_id']=classification_id
    annotation_df['user_id']=user_id
    annotations_df_list.append(annotation_df)
    print(annotation_df)

all_annotations = pd.concat(annotations_df_list)
all_annotations.to_excel(output_dir / 'annotations.xlsx')
print(all_annotations.columns)
print('Done')