import json
import logging
import sqlite3
import textwrap
from typing import Optional, List

import pandas as pd

model_name_abbreviations = {
    'gemini/gemini-2.0-flash-001': 'gemini-2.0-flash',
    'openai/gpt-4.1': 'openai-gpt-4.1',
    'us.meta.llama4-scout-17b-instruct-v1:0': 'llama4-scout',
    'ollama_chat/qwen3:30b':'qwen3',
    'us.amazon.nova-premier-v1:0':'nova-premier-v1',
    'ollama_chat/phi4:latest':'microsoft-phi4',
    'us.meta.llama4-maverick-17b-instruct-v1:0':'llama4-maverick',
    'mistral/mistral-large-2411':'mistral-large',
    'us.deepseek.r1-v1:0':'deepseek-r1',
    'us.anthropic.claude-3-7-sonnet-20250219-v1:0':'claude-3.7-sonnet',
    'ollama_chat/gemma3:27b':'google-gemma3'
    }

def shorten_model_names(model_name):
    if model_name not in model_name_abbreviations:
        raise ValueError(f'No known abbreviation for `{model_name}`. Please add to the model_name_abbreviations')
    return model_name_abbreviations[model_name]

def load_raw(classifications_csv_path, subjects_path, prompts_database_path, workflow_id,
             exclude_models: Optional[List[str]] = None, exclude_prompt_ids: Optional[List[int]] = None):
    # Read classifications
    classifications_df = pd.read_csv(classifications_csv_path)
    classifications_df.set_index('classification_id',inplace=True)
    subjects_df = pd.read_csv(subjects_path)
    # Extract the prompt_id, llm model and other data from the metadata column
    subjects_df = subjects_df.loc[subjects_df.workflow_id == workflow_id]
    metadata_df = subjects_df['metadata'].apply(json.loads).apply(pd.Series)
    subjects_df = pd.concat([subjects_df, metadata_df], axis=1)

    if exclude_models and isinstance(exclude_models,list):
        assert all([isinstance(x,str) for x in exclude_models])
        count_reviews_on_excluded_models = subjects_df['prompt_id'].isin(exclude_models).sum()
        if count_reviews_on_excluded_models> 0:
            logging.warning(f"{count_reviews_on_excluded_models} reviews were of models later excluded."
                         "These reviews have been removed from analysis")
        subjects_df = subjects_df.loc[~subjects_df['#llm_model'].isin(exclude_models)]
    if exclude_prompt_ids and isinstance(exclude_prompt_ids, list):
        assert all([isinstance(x,int) for x in exclude_prompt_ids])
        count_reviews_on_excluded_subjects = subjects_df['prompt_id'].isin(exclude_prompt_ids).sum()
        if count_reviews_on_excluded_subjects > 0:
            logging.warning(f"{count_reviews_on_excluded_subjects} reviews were of prompts later excluded."
                         "These reviews have been removed from analysis")
        subjects_df = subjects_df.loc[~subjects_df['prompt_id'].isin(exclude_prompt_ids)]

    # Exclude classifications from users who are not logged in

    not_logged_in_classifications = classifications_df.user_name.str.match('not-logged-in')
    if not_logged_in_classifications.any():
        logging.warning(f"{not_logged_in_classifications.sum()} classifications were performed by users who were not logged in. "
                     f"These reviews have been excluded from analysis")
    classifications_df = classifications_df.loc[~not_logged_in_classifications]


    conn = sqlite3.connect(prompts_database_path)
    prompts_df = pd.read_sql('''select * from prompts''', conn)

    # Combine with the subject data, to get the llm name, the prompt text, etc
    # Explode the annotations column
    exploded_dfs = classifications_df['annotations'].apply(explode_tasks)
    exploded_df = pd.concat(exploded_dfs.values, keys=exploded_dfs.index,
                            names=['original_index', 'task_index']).reset_index(level='task_index', drop=True)
    # Pivot the DataFrame to have one column per task
    pivoted_df = exploded_df.pivot(columns='task', values='value').reset_index()
    # Re-insert the classification_ids
    pivoted_df['subject_id'] = classifications_df.loc[pivoted_df['original_index'], 'subject_ids'].values
    # Merge and set dtype of prompt_id
    combined_df = pivoted_df.merge(subjects_df, on='subject_id', how='inner')
    combined_df.prompt_id = combined_df.prompt_id.astype(int)

    # Merge with prompts
    final_df = combined_df.merge(prompts_df, on='prompt_id')

    final_df['#llm_model'] = final_df['#llm_model'].map(shorten_model_names)

    # Check if the number of rows in the merged dataframe differs from the number of rows in the left dataframe
    if final_df.shape[0] != combined_df.shape[0]:
        logging.error(
            f"The number of rows in the merged dataframe ({final_df.shape[0]}) when merging combined_df on prompts_df differs from the number of rows in the left dataframe ({combined_df.shape[0]}).")
        exit()
    return final_df


def get_count_completed_tasks(tasks):
    try:
        tasks_list = json.loads(tasks)
        count_completed_tasks = sum(1 for task in tasks_list if task['value'] is not None and task['value'] != '')
        highest_completed_task_number = 0
        for i in reversed(range(len(tasks_list))):
            if tasks_list[i]['value'] is not None and tasks_list[i]['value'] != '':
                highest_completed_task_number = i
                break
        return pd.Series([count_completed_tasks, highest_completed_task_number])
    except (json.JSONDecodeError, TypeError):
        return pd.Series([None,None])


def explode_tasks(tasks):
    try:
        tasks_list = json.loads(tasks)
        return pd.DataFrame(tasks_list)
    except (json.JSONDecodeError, TypeError):
        return pd.DataFrame()


def wrap_labels(ax, width, break_long_words=True):
    xlabels = []
    for label in ax.get_xticklabels():
        text = label.get_text()
        parts = text.split('-')
        wrapped_parts = [textwrap.fill(part, width=width, break_long_words=break_long_words) for part in parts]
        wrapped_text = ' '.join(wrapped_parts)
        xlabels.append(wrapped_text)
    ax.set_xticks(ax.get_xticks())  # Set ticks explicitly
    ax.set_xticklabels(xlabels, rotation=45, ha='right')
    ylabels=[]
    for label in ax.get_yticklabels():
        text = label.get_text()
        ylabels.append(textwrap.fill(text, width=width, break_long_words=break_long_words))
    ax.set_yticks(ax.get_yticks())  # Set ticks explicitly
    ax.set_yticklabels(ylabels, rotation=45, ha='right')
