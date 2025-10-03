"""Analysis helper functions for processing model evaluation data."""
import json
import logging
import sys
import textwrap
from pathlib import Path
from typing import Optional, List

try:
    import pandas as pd
except ImportError:
    pd = None
    logging.error("pandas is not installed. Please install it with: pip install pandas")
    sys.exit(1)

model_name_abbreviations = {
    'gemini/gemini-2.0-flash-001': 'gemini-2.0-flash',
    'openai/gpt-4.1': 'openai-gpt-4.1',
    'us.meta.llama4-scout-17b-instruct-v1:0': 'llama4-scout',
    'ollama_chat/qwen3:30b': 'qwen3',
    'us.amazon.nova-premier-v1:0': 'nova-premier-v1',
    'ollama_chat/phi4:latest': 'microsoft-phi4',
    'us.meta.llama4-maverick-17b-instruct-v1:0': 'llama4-maverick',
    'mistral/mistral-large-2411': 'mistral-large',
    'us.deepseek.r1-v1:0': 'deepseek-r1',
    'us.anthropic.claude-3-7-sonnet-20250219-v1:0': 'claude-3.7-sonnet',
    'ollama_chat/gemma3:27b': 'google-gemma3'
}

open_models = {
    'google-gemma3',
    'llama4-maverick',
    'llama4-scout',
    'mistral-large',
    'microsoft-phi4',
    'qwen3'
}

citation_prompts = [2, 3, 7, 8, 9, 11, 13, 14, 18]

# map ratings to numerical values
rating_description_to_number = {
    "3 - good": 3,
    "2 - average": 2,
    "1 - poor": 1,
    "4 - expert / better than human": 4
}

yes_no_to_number = {"Yes": 1, "No": 0}


def shorten_model_names(model_name):
    """Return abbreviated model name for the given model name."""
    if model_name not in model_name_abbreviations:
        raise ValueError(
            f'No known abbreviation for `{model_name}`. '
            'Please add to the model_name_abbreviations'
        )
    return model_name_abbreviations[model_name]


def _validate_paths(classifications_csv_path, prompts_json_path):
    """Validate input file paths."""
    prompts_json_path = (
        Path(prompts_json_path) 
        if not isinstance(prompts_json_path, Path) 
        else prompts_json_path
    )
    assert prompts_json_path.is_file(), "prompts json file does not exist"
    assert (
        prompts_json_path.suffix.lower() == '.json'
    ), "Prompts json file must be a json file"

    classifications_csv_path = (
        Path(classifications_csv_path) 
        if not isinstance(classifications_csv_path, Path) 
        else classifications_csv_path
    )
    assert classifications_csv_path.is_file(), "classifications csv file does not exist"
    assert (
        classifications_csv_path.suffix.lower() == '.csv'
    ), "Classifications csv file must be a csv file"
    
    return classifications_csv_path, prompts_json_path


def _filter_by_models(subjects_df, exclude_models):
    """Filter subjects dataframe by excluding specified models."""
    if exclude_models and isinstance(exclude_models, list):
        assert all(isinstance(x, str) for x in exclude_models)
        count_reviews_on_excluded_models = (
            subjects_df['prompt_id'].isin(exclude_models).sum()
        )
        if count_reviews_on_excluded_models > 0:
            logging.warning(
                "%d reviews were of models later excluded. "
                "These reviews have been removed from analysis",
                count_reviews_on_excluded_models
            )
        subjects_df = subjects_df.loc[~subjects_df['#llm_model'].isin(exclude_models)]
    return subjects_df


def _filter_by_prompt_ids(subjects_df, exclude_prompt_ids):
    """Filter subjects dataframe by excluding specified prompt IDs."""
    if exclude_prompt_ids and isinstance(exclude_prompt_ids, list):
        assert all(isinstance(x, int) for x in exclude_prompt_ids)
        count_reviews_on_excluded_subjects = (
            subjects_df['prompt_id'].isin(exclude_prompt_ids).sum()
        )
        if count_reviews_on_excluded_subjects > 0:
            logging.warning(
                "%d reviews were of prompts later excluded. "
                "These reviews have been removed from analysis",
                count_reviews_on_excluded_subjects
            )
        subjects_df = subjects_df.loc[~subjects_df['prompt_id'].isin(exclude_prompt_ids)]
    return subjects_df


def _filter_logged_in_users(classifications_df):
    """Filter classifications to exclude non-logged-in users."""
    not_logged_in_classifications = classifications_df.user_name.str.match('not-logged-in')
    if not_logged_in_classifications.any():
        logging.warning(
            "%d classifications were performed by users who were not logged in. "
            "These reviews have been excluded from analysis",
            not_logged_in_classifications.sum()
        )
    return classifications_df.loc[~not_logged_in_classifications]


def _process_annotations(classifications_df, subjects_df):
    """Process annotations and merge with subject data."""
    exploded_dfs = classifications_df['annotations'].apply(explode_tasks)
    exploded_df = pd.concat(
        exploded_dfs.values, 
        keys=exploded_dfs.index,
        names=['original_index', 'task_index']
    ).reset_index(level='task_index', drop=True)
    
    # Pivot the DataFrame to have one column per task
    pivoted_df = exploded_df.pivot(columns='task', values='value').reset_index()
    # Re-insert the classification_ids
    pivoted_df['subject_id'] = classifications_df.loc[
        pivoted_df['original_index'], 'subject_ids'
    ].values
    
    # Merge and set dtype of prompt_id
    combined_df = pivoted_df.merge(subjects_df, on='subject_id', how='inner')
    combined_df.prompt_id = combined_df.prompt_id.astype(int)
    
    return combined_df


def _validate_merge(final_df, combined_df):
    """Validate that merge operation preserved all rows."""
    if final_df.shape[0] != combined_df.shape[0]:
        logging.error(
            "The number of rows in the merged dataframe (%d) when merging "
            "combined_df on prompts_df differs from the number of rows in "
            "the left dataframe (%d).",
            final_df.shape[0],
            combined_df.shape[0]
        )
        sys.exit(1)


def _map_scores(final_df):
    """Map rating options to numerical values."""
    try:
        final_df['T2_score'] = final_df['T2'].apply(
            lambda x: rating_description_to_number[x]
        )
        final_df['T3_score'] = final_df['T3'].apply(
            lambda x: rating_description_to_number[x]
        )
        final_df['T4_score'] = final_df['T4'].apply(
            lambda x: yes_no_to_number[x]
        )
        final_df['T12_score'] = final_df['T12'].apply(
            lambda x: yes_no_to_number[x]
        )
    except KeyError as e:
        logging.error("Error mapping rating options: %s", e)
        sys.exit(1)
    except Exception as e:
        raise e


def load_raw(classifications_csv_path, subjects_path, prompts_json_path, 
             workflow_id, exclude_models: Optional[List[str]] = None, 
             exclude_prompt_ids: Optional[List[int]] = None) -> pd.DataFrame:
    """Load raw data and merge into a single dataframe.
    
    Args:
        classifications_csv_path: Path to classifications CSV file
        subjects_path: Path to subjects CSV file  
        prompts_json_path: Path to prompts JSON file
        workflow_id: Workflow ID to filter subjects
        exclude_models: Optional list of model names to exclude
        exclude_prompt_ids: Optional list of prompt IDs to exclude
        
    Returns:
        Combined dataframe with all data merged
    """
    # Validate paths
    classifications_csv_path, prompts_json_path = _validate_paths(
        classifications_csv_path, prompts_json_path
    )

    # Read classifications
    classifications_df = pd.read_csv(classifications_csv_path)
    classifications_df.set_index('classification_id', inplace=True)
    subjects_df = pd.read_csv(subjects_path)
    
    # Extract the prompt_id, llm model and other data from the metadata column
    subjects_df = subjects_df.loc[subjects_df.workflow_id == workflow_id]
    metadata_df = subjects_df['metadata'].apply(json.loads).apply(pd.Series)
    subjects_df = pd.concat([subjects_df, metadata_df], axis=1)

    # Apply filters
    subjects_df = _filter_by_models(subjects_df, exclude_models)
    subjects_df = _filter_by_prompt_ids(subjects_df, exclude_prompt_ids)
    classifications_df = _filter_logged_in_users(classifications_df)

    # Load prompts
    prompts_df = pd.read_json(prompts_json_path)

    # Process annotations and merge
    combined_df = _process_annotations(classifications_df, subjects_df)
    
    # Merge with prompts
    final_df = combined_df.merge(prompts_df, on='prompt_id')
    final_df['#llm_model'] = final_df['#llm_model'].map(shorten_model_names)

    # Validate merge
    _validate_merge(final_df, combined_df)
    
    # Map scores
    _map_scores(final_df)

    # Get number of citations in response to citation prompts
    final_df.loc[
        final_df.prompt_id.isin(citation_prompts), 'count_citations'
    ] = final_df.T1.apply(len)

    return final_df


def get_count_completed_tasks(tasks):
    """Get count of completed tasks and highest completed task number.
    
    Args:
        tasks: JSON string containing task data
        
    Returns:
        pandas Series with count and highest completed task number
    """
    try:
        tasks_list = json.loads(tasks)
        count_completed_tasks = sum(
            1 for task in tasks_list
            if task['value'] is not None and task['value'] != ''
        )
        highest_completed_task_number = 0
        for i in reversed(range(len(tasks_list))):
            if tasks_list[i]['value'] is not None and tasks_list[i]['value'] != '':
                highest_completed_task_number = i
                break
        return pd.Series([count_completed_tasks, highest_completed_task_number])
    except (json.JSONDecodeError, TypeError):
        return pd.Series([None, None])


def explode_tasks(tasks):
    """Convert JSON tasks string to DataFrame.
    
    Args:
        tasks: JSON string containing task data
        
    Returns:
        DataFrame with task data or empty DataFrame if parsing fails
    """
    try:
        tasks_list = json.loads(tasks)
        return pd.DataFrame(tasks_list)
    except (json.JSONDecodeError, TypeError):
        return pd.DataFrame()


def wrap_labels(ax, width, break_long_words=True):
    """Wrap axis labels to specified width.
    
    Args:
        ax: Matplotlib axis object
        width: Maximum width for wrapped text
        break_long_words: Whether to break long words
    """
    xlabels = []
    for label in ax.get_xticklabels():
        text = label.get_text()
        parts = text.split('-')
        wrapped_parts = [
            textwrap.fill(part, width=width, break_long_words=break_long_words) 
            for part in parts
        ]
        wrapped_text = ' '.join(wrapped_parts)
        xlabels.append(wrapped_text)
    ax.set_xticks(ax.get_xticks())  # Set ticks explicitly
    ax.set_xticklabels(xlabels, rotation=45, ha='right')
    
    ylabels = []
    for label in ax.get_yticklabels():
        text = label.get_text()
        ylabels.append(
            textwrap.fill(text, width=width, break_long_words=break_long_words)
        )
    ax.set_yticks(ax.get_yticks())  # Set ticks explicitly
    ax.set_yticklabels(ylabels, rotation=45, ha='right')
