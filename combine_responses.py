import sqlite3
import pandas as pd

def combine_sqlite_databases(db1_path, db2_path, output_db_path,table_name):
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
    conn_output = sqlite3.connect(output_db_path)

    # Write the combined dataframe to the output database
    combined_df.to_sql(table_name, conn_output, if_exists='replace', index=False)

    # Close the connection to the output database
    conn_output.close()

if __name__ == '__main__':
    combine_sqlite_databases('records_artur_20250505.db', 'records_bedrock.db', 'records_artur_bharath.db', table_name='responses')
