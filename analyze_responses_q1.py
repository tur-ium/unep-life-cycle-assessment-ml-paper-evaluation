"""
This script loads in responses from classification csv file output by Zooniverse,
and normalizes them into a table with one row per task answered
"""
import json
import logging
import sqlite3
from pathlib import Path
from datetime import datetime

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from analysis_helpers import get_count_completed_tasks, explode_tasks

# PARAMETERS
classifications_csv_path = 'survey_responses/may-survey-classifications_2025-05-19.csv'
output_dir = 'survey_responses/analysis/may'
ml_responses_database_path = 'records_bedrock.db'
subjects_path = 'survey_responses/review-llm-responses-on-lca-tasks-subjects.csv'
workflow_id = 28845


def plot_responses_over_time(classifications_df: pd.DataFrame,output_dir: Path):

    annotations_df_list = []
    workflow_ids = classifications_df.value_counts('workflow_id')
    assert workflow_ids.shape[0] == 1
    workflow_id = workflow_ids.iloc[0]

    classification_id = classifications_df.classification_id

    # Group the data by date and count the number of responses
    classifications_df['created_at'] = pd.to_datetime(classifications_df['created_at'])
    classifications_df['date'] = classifications_df['created_at'].dt.date
    responses_per_day = classifications_df.groupby('date').size()

    # Plot the time series
    plt.figure(figsize=(12, 6))
    responses_per_day.plot()
    plt.title('Number of Responses per Day')
    plt.xlabel('Date')
    plt.ylabel('Number of Responses')
    plt.grid(True)
    plt.savefig(output_dir/'responses_timeline.png')

    # Calculate the cumulative sum of responses
    cumulative_responses = responses_per_day.cumsum()

    # Plot the cumulative time series
    plt.figure(figsize=(12, 6))
    sns.lineplot(data=cumulative_responses, drawstyle='steps-post')
    plt.title('Cumulative Responses')
    plt.xlabel('Date')
    plt.ylabel('Number of Responses')
    plt.grid(True)
    plt.savefig(output_dir/'responses_timeline_cum.png')

    # Create a new column indicating whether 'user_id' is null or not
    classifications_df['user_id_null'] = classifications_df['user_id'].isnull()

    # Group the data by date and 'user_id_null', then count the number of responses
    responses_per_day = classifications_df.groupby(['date', 'user_id_null']).size().unstack(fill_value=0)

    # Plot the stacked area chart
    plt.figure(figsize=(12, 6))
    plt.stackplot(responses_per_day.index, responses_per_day.T, labels=['User ID Not Null', 'User ID Null'])
    plt.title('Stacked Area Chart of Responses per Day')
    plt.xlabel('Date')
    plt.ylabel('Number of Responses')
    plt.legend(loc='upper left')
    plt.grid(True)
    plt.savefig(output_dir/'responses_timeline_stacked.png')
    plt.show()

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

def get_q1_count_citations(prompts_df,ml_responses_df,classifications_df):
    # Which questions ask for citations?
    classifications_df.columns
    prompts_df['expect_citation'] = prompts_df.prompt_text.str.contains('citation')
    # convert annotations into json object
    classifications_df.annotations = classifications_df.annotations.apply(json.loads)
    # How many citations are there per model per task that requires citations?

def analayse_q2():
    """
    How scientifically accurate is this response - on a scale from 1-4?
        1. 1 = Poor accuracy / scientific accuracy. The answer is incorrect or fails to provide any reasonable evidence
        2. 2 = Average, this is the level one might expect of a non-expert or someone with limited experience of LCA. It is generally scientifically correct, but may omit relevant points
        3. 3 = Good, this is level one might expect of a LCA expert. It is scientifically correct, and makes strong points. However, it may not be the most comprehensive or accurate response
        4. 4 = Exceptional response, on-par or above the level one might expect of an LCA expert. Shows exceptional accuracy and understanding of the topic.
        Evaluate this independent of whether the output is well formatted or is the best explanation
        You can optionally justify your answer in the next task
    :return:
    """
    pass


# Function to count the length of the list in the 'T1' column
def count_citations_task_1(value):
    json_val = json.loads(value)
    if isinstance(json_val, list):
        return len(json_val)
    return None

def count_tool_items(value):
    """Used for analysing questions with tools that allow drawing rectangles. e.g. highlighting citation.
    Each tool refers to a different colour box, which represents e.g. different types of citation"""
    if isinstance(value, list):
        tool_counts = {}
        for item in value:
            tool = item.get('tool')
            if tool is not None:
                tool_counts[tool] = tool_counts.get(tool, 0) + 1
        return tool_counts
    return {}

def extract_prompt_id_from_subject_metadata(subject_metadata):
    try:
        metadata_list = json.loads(subject_metadata)
        return pd.DataFrame(metadata_list)
    except (json.JSONDecodeError, TypeError):
        return pd.DataFrame()

def plot_hallucination_rate(df,output_img_path):
    import matplotlib.pyplot as plt
    import seaborn as sns


    # Create the scatter plot with bubble sizes using seaborn
    plt.figure(figsize=(12, 8))
    scatter = sns.scatterplot(
        data=df,
        x=df.index,
        y="Hallucination rate",
        size="Usable data points",
        sizes=(100, 1000),  # Scale the bubble size for visibility
        hue="Usable data points",
        palette="Purples",  # Use a purple color palette
        alpha=0.6,
        edgecolor="w",
        linewidth=2
    )

    # Add titles and labels
    plt.title("Hallucination Rate by Model with Number of Usable Data Points")
    plt.xlabel("Model Name")
    plt.ylabel("Hallucination Rate (%)")
    plt.xticks(rotation=45, ha='right')
    plt.grid(True)

    # Annotate each point with the number of usable data points
    for i, row in df.iterrows():
        plt.annotate(
            f"Data: {row['Usable data points']}",
            (row.name, row['Hallucination rate']),
            textcoords="offset points",
            xytext=(0, 10),
            ha='center'
        )

    plt.tight_layout()
    plt.savefig(output_img_path)
    plt.show()


if __name__ == '__main__':
    current_date = datetime.now().strftime('%Y%m%d')

    logging.basicConfig(level=logging.INFO)

    # Read classifications
    classifications_df = pd.read_csv(classifications_csv_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    subjects_df = pd.read_csv(subjects_path)
    # Extract the prompt_id, llm model and other data from the metadata column
    subjects_df = subjects_df.loc[subjects_df.workflow_id==workflow_id]
    metadata_df = subjects_df['metadata'].apply(json.loads).apply(pd.Series)
    subjects_df = pd.concat([subjects_df, metadata_df], axis=1)

    # TODO: Prompts and responses in one database
    # TODO: filter out questions that were withdrawn
    prompts_database_path = 'records_cajetan.db'
    conn = sqlite3.connect(prompts_database_path)
    prompts_df = pd.read_sql('''select * from prompts''', conn)
    ml_responses_database_path = 'records_may_all.db'
    conn = sqlite3.connect(ml_responses_database_path)
    ml_responses_df = pd.read_sql('select * from responses', conn)

    ## Plot responses over time
    # plot_responses_over_time(classifications_df,output_dir)

    # Count complete answers
    classifications_df[['count_completed_tasks', 'final_completed_task_no']] = classifications_df.annotations.apply(
        get_count_completed_tasks)
    print('Count completed tasks (note some tasks are optional)')
    print(classifications_df.count_completed_tasks.value_counts())
    print('Final completed task number')
    print(classifications_df.final_completed_task_no.value_counts())

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
    combined_df = pivoted_df.merge(subjects_df,on='subject_id',how='inner')
    combined_df.prompt_id = combined_df.prompt_id.astype(int)

    # Merge with prompts
    combined_final = combined_df.merge(prompts_df, on='prompt_id')

    # Check if the number of rows in the merged dataframe differs from the number of rows in the left dataframe
    if combined_final.shape[0] != combined_df.shape[0]:
        logging.error(
            f"The number of rows in the merged dataframe ({combined_final.shape[0]}) when merging combined_df on prompts_df differs from the number of rows in the left dataframe ({combined_df.shape[0]}).")
        exit()

    ##############################################################
    # Analyse Q1 - Citations
    ##############################################################
    # Filter on questions that ask for citations
    combined_final.loc[:,'expect_citation'] = combined_final.prompt_text.str.contains('citation')
    filtered_q1 = combined_final.loc[combined_final.expect_citation==1]
    filtered_q1.loc[:,'count_citations'] = filtered_q1.T1.apply(len)

    # Apply the function to the 'T1' column
    citation_types = filtered_q1['T1'].apply(count_tool_items)

    # Aggregate the counts for each tool
    count_citation_types_agg = {}
    for counts in citation_types:
        for tool, count in counts.items():
            count_citation_types_agg[tool] = count_citation_types_agg.get(tool, 0) + count

    # Map the tool values to the corresponding results
    tool_number_to_citation_type = {0: 'correct', 1: 'not_exist', 2: 'not_relevant', 3: 'no_access'}

    # Summarize number of correct citations across models
    summary_citation_types_across_models = pd.Series({
        f'T1_{tool_number_to_citation_type.get(tool, "unknown")}': count_citation_types_agg.get(tool, 0)
        for tool in tool_number_to_citation_type
    })

    # Summarize citations per model
    # Summarize the results by type of citation, aggregating on the column '#llm_model'
    summary_by_model_dict = combined_df.groupby('#llm_model', group_keys=False).apply(lambda x: {
        f'T1_{tool_number_to_citation_type.get(tool, "unknown")}': x['T1'].apply(count_tool_items).apply(
            lambda y: y.get(tool, 0)).sum()
        for tool in tool_number_to_citation_type
    }).to_dict()

    summary_citations_by_model = pd.DataFrame.from_dict(summary_by_model_dict).T
    usable_data_points = summary_citations_by_model[['T1_correct','T1_not_exist','T1_not_relevant']].agg('sum',axis=1)
    hallucination_rate = 1- (summary_citations_by_model.T1_correct/usable_data_points)
    summary_citations_by_model['Usable data points'] = usable_data_points
    summary_citations_by_model.loc[usable_data_points>=7,['Hallucination rate']] = hallucination_rate
    summary_citations_by_model.loc[usable_data_points<7,['Hallucination rate']]=None # not enough evidence
    summary_citations_by_model.sort_values(by='Hallucination rate',ascending=True,inplace=True)
    summary_citations_by_model.index.name = 'Model name'

    output_img_path = output_dir / f'{current_date}_q1_citations_per_model.png'
    plot_hallucination_rate(summary_citations_by_model,output_img_path)
    with pd.ExcelWriter(output_dir / f'{current_date}_q1_analysis.xlsx') as wb:
        summary_citation_types_across_models.to_excel(wb,sheet_name='CitationsAllModels')
        summary_citations_by_model.to_excel(wb,sheet_name='CitationsPerModel')
        worksheet = wb.sheets['CitationsPerModel']
        worksheet.insert_image('K1', str(output_img_path.absolute()))

    # TODO: store the comments on citations, and analyse
