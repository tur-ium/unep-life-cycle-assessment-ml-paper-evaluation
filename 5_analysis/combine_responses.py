"""Module for combining and deduplicating SQLite database responses."""
import sqlite3

import pandas as pd


def remove_duplicates(database_path):
    """Remove duplicate responses from database, keeping latest by execution_datestamp."""
    # Connect to the SQLite database
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()

    # Step 1: Identify duplicate rows and keep the latest one based on execution_datestamp
    cursor.execute('''
        DELETE FROM responses
        WHERE id NOT IN (
            SELECT id FROM (
                SELECT id,model_name,prompt_id
                FROM responses
                ORDER BY model_name, prompt_id, execution_datestamp DESC
            ) AS temp
            GROUP BY model_name, prompt_id
        )
    ''')

    # Commit the changes and close the connection
    conn.commit()
    conn.close()


def combine_sqlite_databases(db1_path, db2_path, output_path, table_name):
    """Combine data from two SQLite databases into a single output database."""
    # Connect to the first database
    conn1 = sqlite3.connect(db1_path)
    # Connect to the second database
    conn2 = sqlite3.connect(db2_path)

    # Read the data from the first database
    df1 = pd.read_sql_query(f"SELECT * FROM {table_name}", conn1)
    # Read the data from the second database
    df2 = pd.read_sql_query(f"SELECT * FROM {table_name}", conn2)

    # Close the connections to the databases
    conn1.close()
    conn2.close()

    # Merge the dataframes
    combined_df = pd.concat([df1, df2], ignore_index=True)

    # Reset the index column
    combined_df['id'] = range(1, len(combined_df) + 1)

    # Connect to the output database
    conn_output = sqlite3.connect(output_path)

    # Drop duplicates
    # Write the combined dataframe to the output database
    combined_df.to_sql(table_name, conn_output, if_exists='replace',
                       index=False)

    # Close the connection to the output database
    conn_output.close()

if __name__ == '__main__':
    OUTPUT_DB_PATH = '../2_retrieved_responses/records.db'
    # combine_sqlite_databases('records_artur_bharath.db', 'records_cajetan.db',
    #                         OUTPUT_DB_PATH, table_name='responses')
    remove_duplicates(OUTPUT_DB_PATH)
