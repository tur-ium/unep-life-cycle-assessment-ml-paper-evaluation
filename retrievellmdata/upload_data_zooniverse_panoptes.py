import csv
import os
import uuid
from pathlib import Path

import dotenv
from panoptes_client import Panoptes, Project, SubjectSet, Subject


def create_subject_set(project:Project, prompt_file_dir:Path, prompt_id:int):
    # Create a new subject set
    assert isinstance(project, Project)
    assert isinstance(prompt_file_dir, Path)
    assert isinstance(prompt_id,int)
    manifest_path = prompt_file_dir / 'manifest.csv'

    subject_set = SubjectSet()
    subject_set.links.project = project
    subject_set.display_name = f'Prompt {prompt_id} Subject Set Auto'
    subject_set.save()

    # Read the manifest CSV file
    with open(manifest_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            # Create a new subject
            subject = Subject()
            subject.links.project = project

            # Add metadata from the CSV row
            subject.metadata.update({
                'response_id': row['response_id'],
                'prompt_id': row['prompt_id'],
                '#llm_model': row['#llm_model'],
                '#temperature': row['#temperature'],
                '#date_run': row['#date_run'],
                '#llm_provider': row['#llm_provider'],
                '#prompt_run_by': row['#prompt_run_by']
            })

            # Add the prompt image
            if row['prompt_image']:
                subject.add_location(str((prompt_file_dir / row['prompt_image']).absolute()))

            # Add images to the subject
            for i in range(1, 6):  # Assuming up to response_image_5
                image_key = f'response_image_{i}'
                if row[image_key]:
                    subject.add_location(str((prompt_file_dir / row[image_key]).absolute()))

            # Save the subject
            subject.save()

            # Add the subject to the subject set
            subject_set.add(subject)

    print(f"Subject set for prompt {prompt_id} uploaded successfully!")

if __name__ == '__main__':
    # Log in to the Panoptes API
    dotenv.load_dotenv('../.env')
    username = os.getenv('ZOONIVERSE_ADMIN_USERNAME')
    pwd = os.getenv('ZOONIVERSE_ADMIN_PASSWORD')
    Panoptes.connect(username=username, password=pwd)

    # Define the path to your manifest CSV file
    base_file_dir = Path(
        r"C:\Users\Artur\Documents\Projects (local)\GLAD AI\llm testing\Zooniverse project\outputs\zooniverse_subject_set_may_all_v3")
    # Create or get your project
    project = Project.find(30120)  # Replace with your project slug or ID

    for prompt_dir in base_file_dir.glob('prompt_*'):
        if not prompt_dir.is_dir():
            continue
        prompt_id = int(prompt_dir.name.replace('prompt_',''))
        create_subject_set(project=project,prompt_file_dir=prompt_dir,prompt_id=prompt_id)
    print('Done')