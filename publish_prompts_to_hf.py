"""
Objective: given prompts in an excel file,
check them for the use of non-standard characters, and store them as a csv file that can be stored on Hugging Face

This allows loading the datasets as HuggingFace datasets
"""

input_filepath = ""

output_parquet_path = "prompts/prompts.parquet"
