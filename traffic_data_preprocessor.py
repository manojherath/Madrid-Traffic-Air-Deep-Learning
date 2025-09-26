#!/usr/bin/env python
# coding: utf-8

# In[65]:


import pandas as pd
import json
import random
import os


# ### Read Raw Data

# In[ ]:


# Read data from Excel
tr_jan = pd.read_excel('data/traffic_data/DatosEstacionesEnero2024.xlsx')
tr_feb = pd.read_excel('data/traffic_data/DatosEstacionesFebrero2024.xlsx')
tr_mar = pd.read_excel('data/traffic_data/DatosEstacionesMarzo2024.xlsx')
tr_apr = pd.read_excel('data/traffic_data/DatosEstacionesAbril2024.xlsx')
tr_jan.head(10)


# ### Terminology for Directions
# - Direction 1 data taken from 1h to 12h 1-
# - Direction 1 data taken from 13h to 24h 1=
# - Direction 2 data taken from 1h to 12h 2-
# - Direction 2 data taken from 13h to 24h 2=

# ### Function to convert to the format of |Date|Station|Time|Direction 1|Direction 2|

# In[67]:


def format_to_df(df):
    # Prepare an empty list to store rows in the desired format
    output_data = []

    # Iterate through each date and station
    for date in df['FDIA'].unique():  # Loop over unique dates
        for station in df['FEST'].unique():  # Loop over unique stations
            
            # Filter data for the current date and station
            station_data = df[(df['FDIA'] == date) & (df['FEST'] == station)]
            
            # Create separate direction 1 and direction 2 data
            direction_1_data = station_data[station_data['FSEN'].str.contains('1')]
            direction_2_data = station_data[station_data['FSEN'].str.contains('2')]
            
            for hour in range(1, 13):  # Process hours from 1 to 12
                # Combine 1- and 2- for first 12 hours
                row_1_minus = direction_1_data[direction_1_data['FSEN'] == '1-']
                row_2_minus = direction_2_data[direction_2_data['FSEN'] == '2-']
                
                # Combine 1= and 2= for next 12 hours
                row_1_equals = direction_1_data[direction_1_data['FSEN'] == '1=']
                row_2_equals = direction_2_data[direction_2_data['FSEN'] == '2=']
        
                # First 12 hours for direction 1 and 2
                if not row_1_minus.empty and not row_2_minus.empty:
                    output_data.append({
                        'Date': row_1_minus['FDIA'].values[0],
                        'Station': station,
                        'Time': f'{hour:02}:00',
                        'Direction 1': row_1_minus[f'HOR{hour}'].values[0],
                        'Direction 2': row_2_minus[f'HOR{hour}'].values[0]
                    })
        
                # Hours 13 to 24 for direction 1 and 2
                if not row_1_equals.empty and not row_2_equals.empty:
                    output_data.append({
                        'Date': row_1_equals['FDIA'].values[0],
                        'Station': station,
                        'Time': f'{hour + 12:02}:00',
                        'Direction 1': row_1_equals[f'HOR{hour}'].values[0],
                        'Direction 2': row_2_equals[f'HOR{hour}'].values[0]
                    })

    # Convert the list to a DataFrame
    output_df = pd.DataFrame(output_data)

    # Sort the final DataFrame by 'Date', 'Station', and 'Time' to ensure increasing order of time
    output_df = output_df.sort_values(by=['Date', 'Station', 'Time']).reset_index(drop=True)

    return output_df
    # Show the final rearranged data
    #print(output_df)


# In[ ]:


tr_jan_formatted = format_to_df(tr_jan)
tr_feb_formatted = format_to_df(tr_feb)
tr_mar_formatted = format_to_df(tr_mar)
tr_apr_formatted = format_to_df(tr_apr)
tr_jan_formatted.head(10)


# ### Function to Convert the Data Frame to the NGSI-LD Data Format
# - convert data frame to ngsild format
# - save as json

# In[69]:


def convert_to_ngsild(df, month):
    # Create a list to store the entities
    entities = []

    # Helper function to generate a random 10-digit datasetId
    def generate_dataset_id():
        return f"urn:ngsi-ld:{random.randint(1000000000, 9999999999)}"

    # Iterate over each unique station in the DataFrame
    for station in df['Station'].unique():
        station_df = df[df['Station'] == station]

        # Create flow data for Direction 1
        direction_1_flows = []
        for _, row in station_df.iterrows():
            # Handle the Date and Time formatting
            if isinstance(row['Date'], pd.Timestamp):
                date_value = row['Date']
            else:
                date_value = pd.to_datetime(row['Date'])

            time_str = row['Time'].strip()

            # Check if time is "24:00" and convert to "00:00" of the next day
            if time_str == "24:00":
                date_value += pd.Timedelta(days=1)
                time_str = "00:00"

            # Ensure date is in 'YYYY-MM-DD' format
            date_str = date_value.strftime('%Y-%m-%d')

            observed_at = f"{date_str}T{time_str}:00Z"  # Combine date and time correctly
            direction_1_flows.append({
                "type": "Property",
                "observedAt": observed_at,
                "datasetId": generate_dataset_id(),  # Add the random datasetId
                "value": row['Direction 1'],
                "unitCode": "E50"
            })

        # Create an entity for Direction 1
        entity_1 = {
            "id": f"urn:ngsi-ld:TrafficFlowObserved:{station}_Direction_1",
            "type": "TrafficFlowObserved",
            "refRoad": {
                "type": "Relationship",
                "object": f"urn:ngsi-ld:Road:{station}_Direction_1"
            },
            "temporalResolution": {
                "type": "Property",
                "value": "PT1H"
            },
            "flow": direction_1_flows,
            "@context": [
                "https://easy-global-market.github.io/c2jn-data-models/jsonld-contexts/c2jn-compound.jsonld"
            ]
        }

        entities.append(entity_1)

        # Create flow data for Direction 2
        direction_2_flows = []
        for _, row in station_df.iterrows():
            # Handle the Date and Time formatting
            if isinstance(row['Date'], pd.Timestamp):
                date_value = row['Date']
            else:
                date_value = pd.to_datetime(row['Date'])

            time_str = row['Time'].strip()

            # Check if time is "24:00" and convert to "00:00" of the next day
            if time_str == "24:00":
                date_value += pd.Timedelta(days=1)
                time_str = "00:00"

            # Ensure date is in 'YYYY-MM-DD' format
            date_str = date_value.strftime('%Y-%m-%d')

            observed_at = f"{date_str}T{time_str}:00Z"  # Combine date and time correctly
            direction_2_flows.append({
                "type": "Property",
                "observedAt": observed_at,
                "datasetId": generate_dataset_id(),  # Add the random datasetId
                "value": row['Direction 2'],
                "unitCode": "E50"
            })

        # Create an entity for Direction 2
        entity_2 = {
            "id": f"urn:ngsi-ld:TrafficFlowObserved:{station}_Direction_2",
            "type": "TrafficFlowObserved",
            "refRoad": {
                "type": "Relationship",
                "object": f"urn:ngsi-ld:Road:{station}_Direction_2"
            },
            "temporalResolution": {
                "type": "Property",
                "value": "PT1H"
            },
            "flow": direction_2_flows,
            "@context": [
                "https://easy-global-market.github.io/c2jn-data-models/jsonld-contexts/c2jn-compound.jsonld"
            ]
        }

        entities.append(entity_2)

    # Save the JSON output to a file
    with open(f"data_traffic_json/traffic_flow_observed_{month}.json", 'w') as json_file:
        json.dump(entities, json_file, indent=4)

    return entities


# In[ ]:


convert_to_ngsild(tr_jan_formatted, "jan")
convert_to_ngsild(tr_feb_formatted, "feb")
convert_to_ngsild(tr_mar_formatted, "mar")
convert_to_ngsild(tr_apr_formatted, "apr")


# ### Function to Entity Split and Save Seperate JSON

# In[71]:


def split_entities_to_files(input_file, output_directory):
    """
    Splits entities from a JSON file into separate JSON files, 
    with each entity wrapped in square brackets.

    Parameters:
        input_file (str): Path to the input JSON file containing the entities.
        output_directory (str): Directory to save the individual JSON files.

    Returns:
        None
    """
    # Ensure the output directory exists
    os.makedirs(output_directory, exist_ok=True)

    # Read the input JSON file
    with open(input_file, 'r') as file:
        data = json.load(file)

    # Iterate over each entity in the JSON array
    for entity in data:
        # Use the `id` field as the filename, replacing problematic characters
        entity_id = entity.get('id', 'unknown_id').replace(':', '_').replace('/', '_')
        output_file = os.path.join(output_directory, f"{entity_id}.json")

        # Wrap the entity inside square brackets
        entity_wrapped = [entity]

        # Write the entity to a separate JSON file
        with open(output_file, 'w') as entity_file:
            json.dump(entity_wrapped, entity_file, indent=4)

    print(f"Entities have been saved to {output_directory}.")


# In[72]:


split_entities_to_files("data_traffic_json/traffic_flow_observed_jan.json", "data_json/jan")
split_entities_to_files("data_traffic_json/traffic_flow_observed_feb.json", "data_json/feb")
split_entities_to_files("data_traffic_json/traffic_flow_observed_mar.json", "data_json/mar")
split_entities_to_files("data_traffic_json/traffic_flow_observed_apr.json", "data_json/apr")


# ### Function to Read JSON Data

# In[73]:


# Read traffic flow data
def read_traffic_flow_data(json_file_path):
    # Step 1: Read the JSON data from the file
    with open(json_file_path, 'r') as json_file:
        data = json.load(json_file)

    # Step 2: Find the entity data for the specified direction
    flow_data = None
    for entity in data:
        flow_data = entity.get("flow",[])

    # Step 3: Convert the flow data to a pandas DataFrame
    df = pd.DataFrame(flow_data)
    df['observedAt'] = pd.to_datetime(df['observedAt'])
    df = df.sort_values('observedAt')

    return df


# ### Training Data Set

# In[ ]:


#print data read code
for e in range(1, 61):  # Loop for entity numbers 1 to 60
    for d in range(1, 3):  # Loop for directions 1 and 2
        print(f'df_mar_e{e:02}_dir_{d}_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES{e:02}_Direction_{d}.json")')


# ### January

# In[74]:


df_jan_e01_dir_1_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES01_Direction_1.json")
df_jan_e01_dir_2_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES01_Direction_2.json")
df_jan_e02_dir_1_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES02_Direction_1.json")
df_jan_e02_dir_2_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES02_Direction_2.json")
df_jan_e03_dir_1_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES03_Direction_1.json")
df_jan_e03_dir_2_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES03_Direction_2.json")
df_jan_e04_dir_1_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES04_Direction_1.json")
df_jan_e04_dir_2_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES04_Direction_2.json")
df_jan_e05_dir_1_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES05_Direction_1.json")
df_jan_e05_dir_2_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES05_Direction_2.json")
df_jan_e06_dir_1_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES06_Direction_1.json")
df_jan_e06_dir_2_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES06_Direction_2.json")
df_jan_e07_dir_1_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES07_Direction_1.json")
df_jan_e07_dir_2_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES07_Direction_2.json")
df_jan_e08_dir_1_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES08_Direction_1.json")
df_jan_e08_dir_2_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES08_Direction_2.json")
df_jan_e09_dir_1_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES09_Direction_1.json")
df_jan_e09_dir_2_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES09_Direction_2.json")
df_jan_e10_dir_1_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES10_Direction_1.json")
df_jan_e10_dir_2_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES10_Direction_2.json")
df_jan_e11_dir_1_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES11_Direction_1.json")
df_jan_e11_dir_2_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES11_Direction_2.json")
df_jan_e12_dir_1_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES12_Direction_1.json")
df_jan_e12_dir_2_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES12_Direction_2.json")
df_jan_e13_dir_1_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES13_Direction_1.json")
df_jan_e13_dir_2_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES13_Direction_2.json")
df_jan_e14_dir_1_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES14_Direction_1.json")
df_jan_e14_dir_2_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES14_Direction_2.json")
df_jan_e15_dir_1_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES15_Direction_1.json")
df_jan_e15_dir_2_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES15_Direction_2.json")
df_jan_e16_dir_1_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES16_Direction_1.json")
df_jan_e16_dir_2_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES16_Direction_2.json")
df_jan_e17_dir_1_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES17_Direction_1.json")
df_jan_e17_dir_2_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES17_Direction_2.json")
df_jan_e18_dir_1_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES18_Direction_1.json")
df_jan_e18_dir_2_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES18_Direction_2.json")
df_jan_e19_dir_1_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES19_Direction_1.json")
df_jan_e19_dir_2_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES19_Direction_2.json")
df_jan_e20_dir_1_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES20_Direction_1.json")
df_jan_e20_dir_2_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES20_Direction_2.json")
df_jan_e21_dir_1_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES21_Direction_1.json")
df_jan_e21_dir_2_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES21_Direction_2.json")
df_jan_e22_dir_1_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES22_Direction_1.json")
df_jan_e22_dir_2_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES22_Direction_2.json")
df_jan_e23_dir_1_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES23_Direction_1.json")
df_jan_e23_dir_2_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES23_Direction_2.json")
df_jan_e24_dir_1_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES24_Direction_1.json")
df_jan_e24_dir_2_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES24_Direction_2.json")
df_jan_e25_dir_1_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES25_Direction_1.json")
df_jan_e25_dir_2_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES25_Direction_2.json")
df_jan_e26_dir_1_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES26_Direction_1.json")
df_jan_e26_dir_2_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES26_Direction_2.json")
df_jan_e27_dir_1_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES27_Direction_1.json")
df_jan_e27_dir_2_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES27_Direction_2.json")
df_jan_e28_dir_1_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES28_Direction_1.json")
df_jan_e28_dir_2_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES28_Direction_2.json")
df_jan_e29_dir_1_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES29_Direction_1.json")
df_jan_e29_dir_2_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES29_Direction_2.json")
df_jan_e30_dir_1_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES30_Direction_1.json")
df_jan_e30_dir_2_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES30_Direction_2.json")
df_jan_e31_dir_1_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES31_Direction_1.json")
df_jan_e31_dir_2_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES31_Direction_2.json")
df_jan_e32_dir_1_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES32_Direction_1.json")
df_jan_e32_dir_2_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES32_Direction_2.json")
df_jan_e33_dir_1_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES33_Direction_1.json")
df_jan_e33_dir_2_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES33_Direction_2.json")
df_jan_e34_dir_1_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES34_Direction_1.json")
df_jan_e34_dir_2_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES34_Direction_2.json")
#df_jan_e35_dir_1_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES35_Direction_1.json")
#df_jan_e35_dir_2_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES35_Direction_2.json")
df_jan_e36_dir_1_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES36_Direction_1.json")
df_jan_e36_dir_2_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES36_Direction_2.json")
df_jan_e37_dir_1_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES37_Direction_1.json")
df_jan_e37_dir_2_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES37_Direction_2.json")
df_jan_e38_dir_1_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES38_Direction_1.json")
df_jan_e38_dir_2_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES38_Direction_2.json")
df_jan_e39_dir_1_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES39_Direction_1.json")
df_jan_e39_dir_2_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES39_Direction_2.json")
df_jan_e40_dir_1_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES40_Direction_1.json")
df_jan_e40_dir_2_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES40_Direction_2.json")
df_jan_e41_dir_1_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES41_Direction_1.json")
df_jan_e41_dir_2_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES41_Direction_2.json")
df_jan_e42_dir_1_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES42_Direction_1.json")
df_jan_e42_dir_2_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES42_Direction_2.json")
df_jan_e43_dir_1_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES43_Direction_1.json")
df_jan_e43_dir_2_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES43_Direction_2.json")
df_jan_e44_dir_1_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES44_Direction_1.json")
df_jan_e44_dir_2_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES44_Direction_2.json")
df_jan_e45_dir_1_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES45_Direction_1.json")
df_jan_e45_dir_2_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES45_Direction_2.json")
df_jan_e46_dir_1_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES46_Direction_1.json")
df_jan_e46_dir_2_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES46_Direction_2.json")
df_jan_e47_dir_1_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES47_Direction_1.json")
df_jan_e47_dir_2_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES47_Direction_2.json")
df_jan_e48_dir_1_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES48_Direction_1.json")
df_jan_e48_dir_2_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES48_Direction_2.json")
df_jan_e49_dir_1_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES49_Direction_1.json")
df_jan_e49_dir_2_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES49_Direction_2.json")
df_jan_e50_dir_1_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES50_Direction_1.json")
df_jan_e50_dir_2_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES50_Direction_2.json")
df_jan_e51_dir_1_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES51_Direction_1.json")
df_jan_e51_dir_2_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES51_Direction_2.json")
df_jan_e52_dir_1_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES52_Direction_1.json")
df_jan_e52_dir_2_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES52_Direction_2.json")
df_jan_e53_dir_1_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES53_Direction_1.json")
df_jan_e53_dir_2_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES53_Direction_2.json")
df_jan_e54_dir_1_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES54_Direction_1.json")
df_jan_e54_dir_2_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES54_Direction_2.json")
df_jan_e55_dir_1_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES55_Direction_1.json")
df_jan_e55_dir_2_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES55_Direction_2.json")
df_jan_e56_dir_1_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES56_Direction_1.json")
df_jan_e56_dir_2_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES56_Direction_2.json")
df_jan_e57_dir_1_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES57_Direction_1.json")
df_jan_e57_dir_2_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES57_Direction_2.json")
df_jan_e58_dir_1_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES58_Direction_1.json")
df_jan_e58_dir_2_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES58_Direction_2.json")
df_jan_e59_dir_1_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES59_Direction_1.json")
df_jan_e59_dir_2_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES59_Direction_2.json")
df_jan_e60_dir_1_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES60_Direction_1.json")
df_jan_e60_dir_2_train = read_traffic_flow_data("data_traffic_json/jan/urn_ngsi-ld_TrafficFlowObserved_ES60_Direction_2.json")


# ### February

# In[75]:


df_feb_e01_dir_1_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES01_Direction_1.json")
df_feb_e01_dir_2_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES01_Direction_2.json")
df_feb_e02_dir_1_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES02_Direction_1.json")
df_feb_e02_dir_2_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES02_Direction_2.json")
df_feb_e03_dir_1_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES03_Direction_1.json")
df_feb_e03_dir_2_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES03_Direction_2.json")
df_feb_e04_dir_1_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES04_Direction_1.json")
df_feb_e04_dir_2_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES04_Direction_2.json")
df_feb_e05_dir_1_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES05_Direction_1.json")
df_feb_e05_dir_2_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES05_Direction_2.json")
df_feb_e06_dir_1_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES06_Direction_1.json")
df_feb_e06_dir_2_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES06_Direction_2.json")
df_feb_e07_dir_1_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES07_Direction_1.json")
df_feb_e07_dir_2_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES07_Direction_2.json")
df_feb_e08_dir_1_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES08_Direction_1.json")
df_feb_e08_dir_2_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES08_Direction_2.json")
df_feb_e09_dir_1_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES09_Direction_1.json")
df_feb_e09_dir_2_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES09_Direction_2.json")
df_feb_e10_dir_1_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES10_Direction_1.json")
df_feb_e10_dir_2_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES10_Direction_2.json")
df_feb_e11_dir_1_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES11_Direction_1.json")
df_feb_e11_dir_2_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES11_Direction_2.json")
df_feb_e12_dir_1_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES12_Direction_1.json")
df_feb_e12_dir_2_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES12_Direction_2.json")
df_feb_e13_dir_1_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES13_Direction_1.json")
df_feb_e13_dir_2_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES13_Direction_2.json")
df_feb_e14_dir_1_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES14_Direction_1.json")
df_feb_e14_dir_2_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES14_Direction_2.json")
df_feb_e15_dir_1_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES15_Direction_1.json")
df_feb_e15_dir_2_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES15_Direction_2.json")
df_feb_e16_dir_1_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES16_Direction_1.json")
df_feb_e16_dir_2_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES16_Direction_2.json")
df_feb_e17_dir_1_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES17_Direction_1.json")
df_feb_e17_dir_2_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES17_Direction_2.json")
df_feb_e18_dir_1_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES18_Direction_1.json")
df_feb_e18_dir_2_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES18_Direction_2.json")
df_feb_e19_dir_1_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES19_Direction_1.json")
df_feb_e19_dir_2_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES19_Direction_2.json")
df_feb_e20_dir_1_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES20_Direction_1.json")
df_feb_e20_dir_2_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES20_Direction_2.json")
df_feb_e21_dir_1_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES21_Direction_1.json")
df_feb_e21_dir_2_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES21_Direction_2.json")
df_feb_e22_dir_1_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES22_Direction_1.json")
df_feb_e22_dir_2_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES22_Direction_2.json")
df_feb_e23_dir_1_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES23_Direction_1.json")
df_feb_e23_dir_2_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES23_Direction_2.json")
df_feb_e24_dir_1_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES24_Direction_1.json")
df_feb_e24_dir_2_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES24_Direction_2.json")
df_feb_e25_dir_1_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES25_Direction_1.json")
df_feb_e25_dir_2_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES25_Direction_2.json")
df_feb_e26_dir_1_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES26_Direction_1.json")
df_feb_e26_dir_2_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES26_Direction_2.json")
df_feb_e27_dir_1_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES27_Direction_1.json")
df_feb_e27_dir_2_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES27_Direction_2.json")
df_feb_e28_dir_1_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES28_Direction_1.json")
df_feb_e28_dir_2_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES28_Direction_2.json")
df_feb_e29_dir_1_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES29_Direction_1.json")
df_feb_e29_dir_2_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES29_Direction_2.json")
df_feb_e30_dir_1_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES30_Direction_1.json")
df_feb_e30_dir_2_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES30_Direction_2.json")
df_feb_e31_dir_1_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES31_Direction_1.json")
df_feb_e31_dir_2_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES31_Direction_2.json")
df_feb_e32_dir_1_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES32_Direction_1.json")
df_feb_e32_dir_2_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES32_Direction_2.json")
df_feb_e33_dir_1_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES33_Direction_1.json")
df_feb_e33_dir_2_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES33_Direction_2.json")
df_feb_e34_dir_1_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES34_Direction_1.json")
df_feb_e34_dir_2_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES34_Direction_2.json")
#df_feb_e35_dir_1_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES35_Direction_1.json")
#df_feb_e35_dir_2_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES35_Direction_2.json")
df_feb_e36_dir_1_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES36_Direction_1.json")
df_feb_e36_dir_2_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES36_Direction_2.json")
df_feb_e37_dir_1_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES37_Direction_1.json")
df_feb_e37_dir_2_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES37_Direction_2.json")
df_feb_e38_dir_1_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES38_Direction_1.json")
df_feb_e38_dir_2_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES38_Direction_2.json")
df_feb_e39_dir_1_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES39_Direction_1.json")
df_feb_e39_dir_2_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES39_Direction_2.json")
df_feb_e40_dir_1_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES40_Direction_1.json")
df_feb_e40_dir_2_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES40_Direction_2.json")
df_feb_e41_dir_1_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES41_Direction_1.json")
df_feb_e41_dir_2_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES41_Direction_2.json")
df_feb_e42_dir_1_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES42_Direction_1.json")
df_feb_e42_dir_2_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES42_Direction_2.json")
df_feb_e43_dir_1_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES43_Direction_1.json")
df_feb_e43_dir_2_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES43_Direction_2.json")
df_feb_e44_dir_1_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES44_Direction_1.json")
df_feb_e44_dir_2_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES44_Direction_2.json")
df_feb_e45_dir_1_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES45_Direction_1.json")
df_feb_e45_dir_2_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES45_Direction_2.json")
df_feb_e46_dir_1_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES46_Direction_1.json")
df_feb_e46_dir_2_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES46_Direction_2.json")
df_feb_e47_dir_1_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES47_Direction_1.json")
df_feb_e47_dir_2_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES47_Direction_2.json")
df_feb_e48_dir_1_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES48_Direction_1.json")
df_feb_e48_dir_2_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES48_Direction_2.json")
df_feb_e49_dir_1_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES49_Direction_1.json")
df_feb_e49_dir_2_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES49_Direction_2.json")
df_feb_e50_dir_1_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES50_Direction_1.json")
df_feb_e50_dir_2_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES50_Direction_2.json")
df_feb_e51_dir_1_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES51_Direction_1.json")
df_feb_e51_dir_2_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES51_Direction_2.json")
df_feb_e52_dir_1_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES52_Direction_1.json")
df_feb_e52_dir_2_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES52_Direction_2.json")
df_feb_e53_dir_1_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES53_Direction_1.json")
df_feb_e53_dir_2_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES53_Direction_2.json")
df_feb_e54_dir_1_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES54_Direction_1.json")
df_feb_e54_dir_2_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES54_Direction_2.json")
df_feb_e55_dir_1_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES55_Direction_1.json")
df_feb_e55_dir_2_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES55_Direction_2.json")
df_feb_e56_dir_1_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES56_Direction_1.json")
df_feb_e56_dir_2_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES56_Direction_2.json")
df_feb_e57_dir_1_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES57_Direction_1.json")
df_feb_e57_dir_2_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES57_Direction_2.json")
df_feb_e58_dir_1_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES58_Direction_1.json")
df_feb_e58_dir_2_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES58_Direction_2.json")
df_feb_e59_dir_1_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES59_Direction_1.json")
df_feb_e59_dir_2_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES59_Direction_2.json")
df_feb_e60_dir_1_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES60_Direction_1.json")
df_feb_e60_dir_2_train = read_traffic_flow_data("data_traffic_json/feb/urn_ngsi-ld_TrafficFlowObserved_ES60_Direction_2.json")


# ### March

# In[76]:


df_mar_e01_dir_1_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES01_Direction_1.json")
df_mar_e01_dir_2_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES01_Direction_2.json")
df_mar_e02_dir_1_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES02_Direction_1.json")
df_mar_e02_dir_2_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES02_Direction_2.json")
df_mar_e03_dir_1_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES03_Direction_1.json")
df_mar_e03_dir_2_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES03_Direction_2.json")
df_mar_e04_dir_1_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES04_Direction_1.json")
df_mar_e04_dir_2_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES04_Direction_2.json")
df_mar_e05_dir_1_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES05_Direction_1.json")
df_mar_e05_dir_2_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES05_Direction_2.json")
df_mar_e06_dir_1_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES06_Direction_1.json")
df_mar_e06_dir_2_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES06_Direction_2.json")
df_mar_e07_dir_1_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES07_Direction_1.json")
df_mar_e07_dir_2_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES07_Direction_2.json")
df_mar_e08_dir_1_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES08_Direction_1.json")
df_mar_e08_dir_2_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES08_Direction_2.json")
df_mar_e09_dir_1_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES09_Direction_1.json")
df_mar_e09_dir_2_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES09_Direction_2.json")
df_mar_e10_dir_1_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES10_Direction_1.json")
df_mar_e10_dir_2_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES10_Direction_2.json")
df_mar_e11_dir_1_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES11_Direction_1.json")
df_mar_e11_dir_2_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES11_Direction_2.json")
df_mar_e12_dir_1_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES12_Direction_1.json")
df_mar_e12_dir_2_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES12_Direction_2.json")
df_mar_e13_dir_1_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES13_Direction_1.json")
df_mar_e13_dir_2_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES13_Direction_2.json")
df_mar_e14_dir_1_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES14_Direction_1.json")
df_mar_e14_dir_2_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES14_Direction_2.json")
df_mar_e15_dir_1_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES15_Direction_1.json")
df_mar_e15_dir_2_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES15_Direction_2.json")
df_mar_e16_dir_1_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES16_Direction_1.json")
df_mar_e16_dir_2_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES16_Direction_2.json")
df_mar_e17_dir_1_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES17_Direction_1.json")
df_mar_e17_dir_2_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES17_Direction_2.json")
df_mar_e18_dir_1_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES18_Direction_1.json")
df_mar_e18_dir_2_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES18_Direction_2.json")
df_mar_e19_dir_1_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES19_Direction_1.json")
df_mar_e19_dir_2_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES19_Direction_2.json")
df_mar_e20_dir_1_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES20_Direction_1.json")
df_mar_e20_dir_2_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES20_Direction_2.json")
df_mar_e21_dir_1_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES21_Direction_1.json")
df_mar_e21_dir_2_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES21_Direction_2.json")
df_mar_e22_dir_1_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES22_Direction_1.json")
df_mar_e22_dir_2_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES22_Direction_2.json")
df_mar_e23_dir_1_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES23_Direction_1.json")
df_mar_e23_dir_2_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES23_Direction_2.json")
df_mar_e24_dir_1_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES24_Direction_1.json")
df_mar_e24_dir_2_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES24_Direction_2.json")
df_mar_e25_dir_1_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES25_Direction_1.json")
df_mar_e25_dir_2_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES25_Direction_2.json")
df_mar_e26_dir_1_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES26_Direction_1.json")
df_mar_e26_dir_2_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES26_Direction_2.json")
df_mar_e27_dir_1_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES27_Direction_1.json")
df_mar_e27_dir_2_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES27_Direction_2.json")
df_mar_e28_dir_1_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES28_Direction_1.json")
df_mar_e28_dir_2_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES28_Direction_2.json")
df_mar_e29_dir_1_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES29_Direction_1.json")
df_mar_e29_dir_2_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES29_Direction_2.json")
df_mar_e30_dir_1_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES30_Direction_1.json")
df_mar_e30_dir_2_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES30_Direction_2.json")
df_mar_e31_dir_1_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES31_Direction_1.json")
df_mar_e31_dir_2_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES31_Direction_2.json")
df_mar_e32_dir_1_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES32_Direction_1.json")
df_mar_e32_dir_2_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES32_Direction_2.json")
df_mar_e33_dir_1_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES33_Direction_1.json")
df_mar_e33_dir_2_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES33_Direction_2.json")
df_mar_e34_dir_1_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES34_Direction_1.json")
df_mar_e34_dir_2_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES34_Direction_2.json")
#df_mar_e35_dir_1_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES35_Direction_1.json")
#df_mar_e35_dir_2_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES35_Direction_2.json")
df_mar_e36_dir_1_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES36_Direction_1.json")
df_mar_e36_dir_2_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES36_Direction_2.json")
df_mar_e37_dir_1_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES37_Direction_1.json")
df_mar_e37_dir_2_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES37_Direction_2.json")
df_mar_e38_dir_1_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES38_Direction_1.json")
df_mar_e38_dir_2_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES38_Direction_2.json")
df_mar_e39_dir_1_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES39_Direction_1.json")
df_mar_e39_dir_2_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES39_Direction_2.json")
df_mar_e40_dir_1_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES40_Direction_1.json")
df_mar_e40_dir_2_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES40_Direction_2.json")
df_mar_e41_dir_1_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES41_Direction_1.json")
df_mar_e41_dir_2_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES41_Direction_2.json")
df_mar_e42_dir_1_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES42_Direction_1.json")
df_mar_e42_dir_2_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES42_Direction_2.json")
df_mar_e43_dir_1_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES43_Direction_1.json")
df_mar_e43_dir_2_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES43_Direction_2.json")
df_mar_e44_dir_1_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES44_Direction_1.json")
df_mar_e44_dir_2_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES44_Direction_2.json")
df_mar_e45_dir_1_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES45_Direction_1.json")
df_mar_e45_dir_2_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES45_Direction_2.json")
df_mar_e46_dir_1_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES46_Direction_1.json")
df_mar_e46_dir_2_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES46_Direction_2.json")
df_mar_e47_dir_1_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES47_Direction_1.json")
df_mar_e47_dir_2_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES47_Direction_2.json")
df_mar_e48_dir_1_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES48_Direction_1.json")
df_mar_e48_dir_2_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES48_Direction_2.json")
df_mar_e49_dir_1_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES49_Direction_1.json")
df_mar_e49_dir_2_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES49_Direction_2.json")
df_mar_e50_dir_1_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES50_Direction_1.json")
df_mar_e50_dir_2_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES50_Direction_2.json")
df_mar_e51_dir_1_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES51_Direction_1.json")
df_mar_e51_dir_2_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES51_Direction_2.json")
df_mar_e52_dir_1_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES52_Direction_1.json")
df_mar_e52_dir_2_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES52_Direction_2.json")
df_mar_e53_dir_1_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES53_Direction_1.json")
df_mar_e53_dir_2_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES53_Direction_2.json")
df_mar_e54_dir_1_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES54_Direction_1.json")
df_mar_e54_dir_2_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES54_Direction_2.json")
df_mar_e55_dir_1_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES55_Direction_1.json")
df_mar_e55_dir_2_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES55_Direction_2.json")
df_mar_e56_dir_1_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES56_Direction_1.json")
df_mar_e56_dir_2_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES56_Direction_2.json")
df_mar_e57_dir_1_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES57_Direction_1.json")
df_mar_e57_dir_2_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES57_Direction_2.json")
df_mar_e58_dir_1_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES58_Direction_1.json")
df_mar_e58_dir_2_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES58_Direction_2.json")
df_mar_e59_dir_1_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES59_Direction_1.json")
df_mar_e59_dir_2_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES59_Direction_2.json")
df_mar_e60_dir_1_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES60_Direction_1.json")
df_mar_e60_dir_2_train = read_traffic_flow_data("data_traffic_json/mar/urn_ngsi-ld_TrafficFlowObserved_ES60_Direction_2.json")


# ### Training Data Set

# In[ ]:


#print data read code
for e in range(1, 61):  # Loop for entity numbers 1 to 60
    for d in range(1, 3):  # Loop for directions 1 and 2
        print(f'df_e{e:02}_dir_{d}_train = pd.concat([df_jan_e{e:02}_dir_{d}_train, df_feb_e{e:02}_dir_{d}_train, df_mar_e{e:02}_dir_{d}_train], axis = 0, ignore_index=True)')


# In[77]:


df_e01_dir_1_train = pd.concat([df_jan_e01_dir_1_train, df_feb_e01_dir_1_train, df_mar_e01_dir_1_train], axis = 0, ignore_index=True)
df_e01_dir_2_train = pd.concat([df_jan_e01_dir_2_train, df_feb_e01_dir_2_train, df_mar_e01_dir_2_train], axis = 0, ignore_index=True)
df_e02_dir_1_train = pd.concat([df_jan_e02_dir_1_train, df_feb_e02_dir_1_train, df_mar_e02_dir_1_train], axis = 0, ignore_index=True)
df_e02_dir_2_train = pd.concat([df_jan_e02_dir_2_train, df_feb_e02_dir_2_train, df_mar_e02_dir_2_train], axis = 0, ignore_index=True)
df_e03_dir_1_train = pd.concat([df_jan_e03_dir_1_train, df_feb_e03_dir_1_train, df_mar_e03_dir_1_train], axis = 0, ignore_index=True)
df_e03_dir_2_train = pd.concat([df_jan_e03_dir_2_train, df_feb_e03_dir_2_train, df_mar_e03_dir_2_train], axis = 0, ignore_index=True)
df_e04_dir_1_train = pd.concat([df_jan_e04_dir_1_train, df_feb_e04_dir_1_train, df_mar_e04_dir_1_train], axis = 0, ignore_index=True)
df_e04_dir_2_train = pd.concat([df_jan_e04_dir_2_train, df_feb_e04_dir_2_train, df_mar_e04_dir_2_train], axis = 0, ignore_index=True)
df_e05_dir_1_train = pd.concat([df_jan_e05_dir_1_train, df_feb_e05_dir_1_train, df_mar_e05_dir_1_train], axis = 0, ignore_index=True)
df_e05_dir_2_train = pd.concat([df_jan_e05_dir_2_train, df_feb_e05_dir_2_train, df_mar_e05_dir_2_train], axis = 0, ignore_index=True)
df_e06_dir_1_train = pd.concat([df_jan_e06_dir_1_train, df_feb_e06_dir_1_train, df_mar_e06_dir_1_train], axis = 0, ignore_index=True)
df_e06_dir_2_train = pd.concat([df_jan_e06_dir_2_train, df_feb_e06_dir_2_train, df_mar_e06_dir_2_train], axis = 0, ignore_index=True)
df_e07_dir_1_train = pd.concat([df_jan_e07_dir_1_train, df_feb_e07_dir_1_train, df_mar_e07_dir_1_train], axis = 0, ignore_index=True)
df_e07_dir_2_train = pd.concat([df_jan_e07_dir_2_train, df_feb_e07_dir_2_train, df_mar_e07_dir_2_train], axis = 0, ignore_index=True)
df_e08_dir_1_train = pd.concat([df_jan_e08_dir_1_train, df_feb_e08_dir_1_train, df_mar_e08_dir_1_train], axis = 0, ignore_index=True)
df_e08_dir_2_train = pd.concat([df_jan_e08_dir_2_train, df_feb_e08_dir_2_train, df_mar_e08_dir_2_train], axis = 0, ignore_index=True)
df_e09_dir_1_train = pd.concat([df_jan_e09_dir_1_train, df_feb_e09_dir_1_train, df_mar_e09_dir_1_train], axis = 0, ignore_index=True)
df_e09_dir_2_train = pd.concat([df_jan_e09_dir_2_train, df_feb_e09_dir_2_train, df_mar_e09_dir_2_train], axis = 0, ignore_index=True)
df_e10_dir_1_train = pd.concat([df_jan_e10_dir_1_train, df_feb_e10_dir_1_train, df_mar_e10_dir_1_train], axis = 0, ignore_index=True)
df_e10_dir_2_train = pd.concat([df_jan_e10_dir_2_train, df_feb_e10_dir_2_train, df_mar_e10_dir_2_train], axis = 0, ignore_index=True)
df_e11_dir_1_train = pd.concat([df_jan_e11_dir_1_train, df_feb_e11_dir_1_train, df_mar_e11_dir_1_train], axis = 0, ignore_index=True)
df_e11_dir_2_train = pd.concat([df_jan_e11_dir_2_train, df_feb_e11_dir_2_train, df_mar_e11_dir_2_train], axis = 0, ignore_index=True)
df_e12_dir_1_train = pd.concat([df_jan_e12_dir_1_train, df_feb_e12_dir_1_train, df_mar_e12_dir_1_train], axis = 0, ignore_index=True)
df_e12_dir_2_train = pd.concat([df_jan_e12_dir_2_train, df_feb_e12_dir_2_train, df_mar_e12_dir_2_train], axis = 0, ignore_index=True)
df_e13_dir_1_train = pd.concat([df_jan_e13_dir_1_train, df_feb_e13_dir_1_train, df_mar_e13_dir_1_train], axis = 0, ignore_index=True)
df_e13_dir_2_train = pd.concat([df_jan_e13_dir_2_train, df_feb_e13_dir_2_train, df_mar_e13_dir_2_train], axis = 0, ignore_index=True)
df_e14_dir_1_train = pd.concat([df_jan_e14_dir_1_train, df_feb_e14_dir_1_train, df_mar_e14_dir_1_train], axis = 0, ignore_index=True)
df_e14_dir_2_train = pd.concat([df_jan_e14_dir_2_train, df_feb_e14_dir_2_train, df_mar_e14_dir_2_train], axis = 0, ignore_index=True)
df_e15_dir_1_train = pd.concat([df_jan_e15_dir_1_train, df_feb_e15_dir_1_train, df_mar_e15_dir_1_train], axis = 0, ignore_index=True)
df_e15_dir_2_train = pd.concat([df_jan_e15_dir_2_train, df_feb_e15_dir_2_train, df_mar_e15_dir_2_train], axis = 0, ignore_index=True)
df_e16_dir_1_train = pd.concat([df_jan_e16_dir_1_train, df_feb_e16_dir_1_train, df_mar_e16_dir_1_train], axis = 0, ignore_index=True)
df_e16_dir_2_train = pd.concat([df_jan_e16_dir_2_train, df_feb_e16_dir_2_train, df_mar_e16_dir_2_train], axis = 0, ignore_index=True)
df_e17_dir_1_train = pd.concat([df_jan_e17_dir_1_train, df_feb_e17_dir_1_train, df_mar_e17_dir_1_train], axis = 0, ignore_index=True)
df_e17_dir_2_train = pd.concat([df_jan_e17_dir_2_train, df_feb_e17_dir_2_train, df_mar_e17_dir_2_train], axis = 0, ignore_index=True)
df_e18_dir_1_train = pd.concat([df_jan_e18_dir_1_train, df_feb_e18_dir_1_train, df_mar_e18_dir_1_train], axis = 0, ignore_index=True)
df_e18_dir_2_train = pd.concat([df_jan_e18_dir_2_train, df_feb_e18_dir_2_train, df_mar_e18_dir_2_train], axis = 0, ignore_index=True)
df_e19_dir_1_train = pd.concat([df_jan_e19_dir_1_train, df_feb_e19_dir_1_train, df_mar_e19_dir_1_train], axis = 0, ignore_index=True)
df_e19_dir_2_train = pd.concat([df_jan_e19_dir_2_train, df_feb_e19_dir_2_train, df_mar_e19_dir_2_train], axis = 0, ignore_index=True)
df_e20_dir_1_train = pd.concat([df_jan_e20_dir_1_train, df_feb_e20_dir_1_train, df_mar_e20_dir_1_train], axis = 0, ignore_index=True)
df_e20_dir_2_train = pd.concat([df_jan_e20_dir_2_train, df_feb_e20_dir_2_train, df_mar_e20_dir_2_train], axis = 0, ignore_index=True)
df_e21_dir_1_train = pd.concat([df_jan_e21_dir_1_train, df_feb_e21_dir_1_train, df_mar_e21_dir_1_train], axis = 0, ignore_index=True)
df_e21_dir_2_train = pd.concat([df_jan_e21_dir_2_train, df_feb_e21_dir_2_train, df_mar_e21_dir_2_train], axis = 0, ignore_index=True)
df_e22_dir_1_train = pd.concat([df_jan_e22_dir_1_train, df_feb_e22_dir_1_train, df_mar_e22_dir_1_train], axis = 0, ignore_index=True)
df_e22_dir_2_train = pd.concat([df_jan_e22_dir_2_train, df_feb_e22_dir_2_train, df_mar_e22_dir_2_train], axis = 0, ignore_index=True)
df_e23_dir_1_train = pd.concat([df_jan_e23_dir_1_train, df_feb_e23_dir_1_train, df_mar_e23_dir_1_train], axis = 0, ignore_index=True)
df_e23_dir_2_train = pd.concat([df_jan_e23_dir_2_train, df_feb_e23_dir_2_train, df_mar_e23_dir_2_train], axis = 0, ignore_index=True)
df_e24_dir_1_train = pd.concat([df_jan_e24_dir_1_train, df_feb_e24_dir_1_train, df_mar_e24_dir_1_train], axis = 0, ignore_index=True)
df_e24_dir_2_train = pd.concat([df_jan_e24_dir_2_train, df_feb_e24_dir_2_train, df_mar_e24_dir_2_train], axis = 0, ignore_index=True)
df_e25_dir_1_train = pd.concat([df_jan_e25_dir_1_train, df_feb_e25_dir_1_train, df_mar_e25_dir_1_train], axis = 0, ignore_index=True)
df_e25_dir_2_train = pd.concat([df_jan_e25_dir_2_train, df_feb_e25_dir_2_train, df_mar_e25_dir_2_train], axis = 0, ignore_index=True)
df_e26_dir_1_train = pd.concat([df_jan_e26_dir_1_train, df_feb_e26_dir_1_train, df_mar_e26_dir_1_train], axis = 0, ignore_index=True)
df_e26_dir_2_train = pd.concat([df_jan_e26_dir_2_train, df_feb_e26_dir_2_train, df_mar_e26_dir_2_train], axis = 0, ignore_index=True)
df_e27_dir_1_train = pd.concat([df_jan_e27_dir_1_train, df_feb_e27_dir_1_train, df_mar_e27_dir_1_train], axis = 0, ignore_index=True)
df_e27_dir_2_train = pd.concat([df_jan_e27_dir_2_train, df_feb_e27_dir_2_train, df_mar_e27_dir_2_train], axis = 0, ignore_index=True)
df_e28_dir_1_train = pd.concat([df_jan_e28_dir_1_train, df_feb_e28_dir_1_train, df_mar_e28_dir_1_train], axis = 0, ignore_index=True)
df_e28_dir_2_train = pd.concat([df_jan_e28_dir_2_train, df_feb_e28_dir_2_train, df_mar_e28_dir_2_train], axis = 0, ignore_index=True)
df_e29_dir_1_train = pd.concat([df_jan_e29_dir_1_train, df_feb_e29_dir_1_train, df_mar_e29_dir_1_train], axis = 0, ignore_index=True)
df_e29_dir_2_train = pd.concat([df_jan_e29_dir_2_train, df_feb_e29_dir_2_train, df_mar_e29_dir_2_train], axis = 0, ignore_index=True)
df_e30_dir_1_train = pd.concat([df_jan_e30_dir_1_train, df_feb_e30_dir_1_train, df_mar_e30_dir_1_train], axis = 0, ignore_index=True)
df_e30_dir_2_train = pd.concat([df_jan_e30_dir_2_train, df_feb_e30_dir_2_train, df_mar_e30_dir_2_train], axis = 0, ignore_index=True)
df_e31_dir_1_train = pd.concat([df_jan_e31_dir_1_train, df_feb_e31_dir_1_train, df_mar_e31_dir_1_train], axis = 0, ignore_index=True)
df_e31_dir_2_train = pd.concat([df_jan_e31_dir_2_train, df_feb_e31_dir_2_train, df_mar_e31_dir_2_train], axis = 0, ignore_index=True)
df_e32_dir_1_train = pd.concat([df_jan_e32_dir_1_train, df_feb_e32_dir_1_train, df_mar_e32_dir_1_train], axis = 0, ignore_index=True)
df_e32_dir_2_train = pd.concat([df_jan_e32_dir_2_train, df_feb_e32_dir_2_train, df_mar_e32_dir_2_train], axis = 0, ignore_index=True)
df_e33_dir_1_train = pd.concat([df_jan_e33_dir_1_train, df_feb_e33_dir_1_train, df_mar_e33_dir_1_train], axis = 0, ignore_index=True)
df_e33_dir_2_train = pd.concat([df_jan_e33_dir_2_train, df_feb_e33_dir_2_train, df_mar_e33_dir_2_train], axis = 0, ignore_index=True)
df_e34_dir_1_train = pd.concat([df_jan_e34_dir_1_train, df_feb_e34_dir_1_train, df_mar_e34_dir_1_train], axis = 0, ignore_index=True)
df_e34_dir_2_train = pd.concat([df_jan_e34_dir_2_train, df_feb_e34_dir_2_train, df_mar_e34_dir_2_train], axis = 0, ignore_index=True)
#df_e35_dir_1_train = pd.concat([df_jan_e35_dir_1_train, df_feb_e35_dir_1_train, df_mar_e35_dir_1_train], axis = 0, ignore_index=True)
#df_e35_dir_2_train = pd.concat([df_jan_e35_dir_2_train, df_feb_e35_dir_2_train, df_mar_e35_dir_2_train], axis = 0, ignore_index=True)
df_e36_dir_1_train = pd.concat([df_jan_e36_dir_1_train, df_feb_e36_dir_1_train, df_mar_e36_dir_1_train], axis = 0, ignore_index=True)
df_e36_dir_2_train = pd.concat([df_jan_e36_dir_2_train, df_feb_e36_dir_2_train, df_mar_e36_dir_2_train], axis = 0, ignore_index=True)
df_e37_dir_1_train = pd.concat([df_jan_e37_dir_1_train, df_feb_e37_dir_1_train, df_mar_e37_dir_1_train], axis = 0, ignore_index=True)
df_e37_dir_2_train = pd.concat([df_jan_e37_dir_2_train, df_feb_e37_dir_2_train, df_mar_e37_dir_2_train], axis = 0, ignore_index=True)
df_e38_dir_1_train = pd.concat([df_jan_e38_dir_1_train, df_feb_e38_dir_1_train, df_mar_e38_dir_1_train], axis = 0, ignore_index=True)
df_e38_dir_2_train = pd.concat([df_jan_e38_dir_2_train, df_feb_e38_dir_2_train, df_mar_e38_dir_2_train], axis = 0, ignore_index=True)
df_e39_dir_1_train = pd.concat([df_jan_e39_dir_1_train, df_feb_e39_dir_1_train, df_mar_e39_dir_1_train], axis = 0, ignore_index=True)
df_e39_dir_2_train = pd.concat([df_jan_e39_dir_2_train, df_feb_e39_dir_2_train, df_mar_e39_dir_2_train], axis = 0, ignore_index=True)
df_e40_dir_1_train = pd.concat([df_jan_e40_dir_1_train, df_feb_e40_dir_1_train, df_mar_e40_dir_1_train], axis = 0, ignore_index=True)
df_e40_dir_2_train = pd.concat([df_jan_e40_dir_2_train, df_feb_e40_dir_2_train, df_mar_e40_dir_2_train], axis = 0, ignore_index=True)
df_e41_dir_1_train = pd.concat([df_jan_e41_dir_1_train, df_feb_e41_dir_1_train, df_mar_e41_dir_1_train], axis = 0, ignore_index=True)
df_e41_dir_2_train = pd.concat([df_jan_e41_dir_2_train, df_feb_e41_dir_2_train, df_mar_e41_dir_2_train], axis = 0, ignore_index=True)
df_e42_dir_1_train = pd.concat([df_jan_e42_dir_1_train, df_feb_e42_dir_1_train, df_mar_e42_dir_1_train], axis = 0, ignore_index=True)
df_e42_dir_2_train = pd.concat([df_jan_e42_dir_2_train, df_feb_e42_dir_2_train, df_mar_e42_dir_2_train], axis = 0, ignore_index=True)
df_e43_dir_1_train = pd.concat([df_jan_e43_dir_1_train, df_feb_e43_dir_1_train, df_mar_e43_dir_1_train], axis = 0, ignore_index=True)
df_e43_dir_2_train = pd.concat([df_jan_e43_dir_2_train, df_feb_e43_dir_2_train, df_mar_e43_dir_2_train], axis = 0, ignore_index=True)
df_e44_dir_1_train = pd.concat([df_jan_e44_dir_1_train, df_feb_e44_dir_1_train, df_mar_e44_dir_1_train], axis = 0, ignore_index=True)
df_e44_dir_2_train = pd.concat([df_jan_e44_dir_2_train, df_feb_e44_dir_2_train, df_mar_e44_dir_2_train], axis = 0, ignore_index=True)
df_e45_dir_1_train = pd.concat([df_jan_e45_dir_1_train, df_feb_e45_dir_1_train, df_mar_e45_dir_1_train], axis = 0, ignore_index=True)
df_e45_dir_2_train = pd.concat([df_jan_e45_dir_2_train, df_feb_e45_dir_2_train, df_mar_e45_dir_2_train], axis = 0, ignore_index=True)
df_e46_dir_1_train = pd.concat([df_jan_e46_dir_1_train, df_feb_e46_dir_1_train, df_mar_e46_dir_1_train], axis = 0, ignore_index=True)
df_e46_dir_2_train = pd.concat([df_jan_e46_dir_2_train, df_feb_e46_dir_2_train, df_mar_e46_dir_2_train], axis = 0, ignore_index=True)
df_e47_dir_1_train = pd.concat([df_jan_e47_dir_1_train, df_feb_e47_dir_1_train, df_mar_e47_dir_1_train], axis = 0, ignore_index=True)
df_e47_dir_2_train = pd.concat([df_jan_e47_dir_2_train, df_feb_e47_dir_2_train, df_mar_e47_dir_2_train], axis = 0, ignore_index=True)
df_e48_dir_1_train = pd.concat([df_jan_e48_dir_1_train, df_feb_e48_dir_1_train, df_mar_e48_dir_1_train], axis = 0, ignore_index=True)
df_e48_dir_2_train = pd.concat([df_jan_e48_dir_2_train, df_feb_e48_dir_2_train, df_mar_e48_dir_2_train], axis = 0, ignore_index=True)
df_e49_dir_1_train = pd.concat([df_jan_e49_dir_1_train, df_feb_e49_dir_1_train, df_mar_e49_dir_1_train], axis = 0, ignore_index=True)
df_e49_dir_2_train = pd.concat([df_jan_e49_dir_2_train, df_feb_e49_dir_2_train, df_mar_e49_dir_2_train], axis = 0, ignore_index=True)
df_e50_dir_1_train = pd.concat([df_jan_e50_dir_1_train, df_feb_e50_dir_1_train, df_mar_e50_dir_1_train], axis = 0, ignore_index=True)
df_e50_dir_2_train = pd.concat([df_jan_e50_dir_2_train, df_feb_e50_dir_2_train, df_mar_e50_dir_2_train], axis = 0, ignore_index=True)
df_e51_dir_1_train = pd.concat([df_jan_e51_dir_1_train, df_feb_e51_dir_1_train, df_mar_e51_dir_1_train], axis = 0, ignore_index=True)
df_e51_dir_2_train = pd.concat([df_jan_e51_dir_2_train, df_feb_e51_dir_2_train, df_mar_e51_dir_2_train], axis = 0, ignore_index=True)
df_e52_dir_1_train = pd.concat([df_jan_e52_dir_1_train, df_feb_e52_dir_1_train, df_mar_e52_dir_1_train], axis = 0, ignore_index=True)
df_e52_dir_2_train = pd.concat([df_jan_e52_dir_2_train, df_feb_e52_dir_2_train, df_mar_e52_dir_2_train], axis = 0, ignore_index=True)
df_e53_dir_1_train = pd.concat([df_jan_e53_dir_1_train, df_feb_e53_dir_1_train, df_mar_e53_dir_1_train], axis = 0, ignore_index=True)
df_e53_dir_2_train = pd.concat([df_jan_e53_dir_2_train, df_feb_e53_dir_2_train, df_mar_e53_dir_2_train], axis = 0, ignore_index=True)
df_e54_dir_1_train = pd.concat([df_jan_e54_dir_1_train, df_feb_e54_dir_1_train, df_mar_e54_dir_1_train], axis = 0, ignore_index=True)
df_e54_dir_2_train = pd.concat([df_jan_e54_dir_2_train, df_feb_e54_dir_2_train, df_mar_e54_dir_2_train], axis = 0, ignore_index=True)
df_e55_dir_1_train = pd.concat([df_jan_e55_dir_1_train, df_feb_e55_dir_1_train, df_mar_e55_dir_1_train], axis = 0, ignore_index=True)
df_e55_dir_2_train = pd.concat([df_jan_e55_dir_2_train, df_feb_e55_dir_2_train, df_mar_e55_dir_2_train], axis = 0, ignore_index=True)
df_e56_dir_1_train = pd.concat([df_jan_e56_dir_1_train, df_feb_e56_dir_1_train, df_mar_e56_dir_1_train], axis = 0, ignore_index=True)
df_e56_dir_2_train = pd.concat([df_jan_e56_dir_2_train, df_feb_e56_dir_2_train, df_mar_e56_dir_2_train], axis = 0, ignore_index=True)
df_e57_dir_1_train = pd.concat([df_jan_e57_dir_1_train, df_feb_e57_dir_1_train, df_mar_e57_dir_1_train], axis = 0, ignore_index=True)
df_e57_dir_2_train = pd.concat([df_jan_e57_dir_2_train, df_feb_e57_dir_2_train, df_mar_e57_dir_2_train], axis = 0, ignore_index=True)
df_e58_dir_1_train = pd.concat([df_jan_e58_dir_1_train, df_feb_e58_dir_1_train, df_mar_e58_dir_1_train], axis = 0, ignore_index=True)
df_e58_dir_2_train = pd.concat([df_jan_e58_dir_2_train, df_feb_e58_dir_2_train, df_mar_e58_dir_2_train], axis = 0, ignore_index=True)
df_e59_dir_1_train = pd.concat([df_jan_e59_dir_1_train, df_feb_e59_dir_1_train, df_mar_e59_dir_1_train], axis = 0, ignore_index=True)
df_e59_dir_2_train = pd.concat([df_jan_e59_dir_2_train, df_feb_e59_dir_2_train, df_mar_e59_dir_2_train], axis = 0, ignore_index=True)
df_e60_dir_1_train = pd.concat([df_jan_e60_dir_1_train, df_feb_e60_dir_1_train, df_mar_e60_dir_1_train], axis = 0, ignore_index=True)
df_e60_dir_2_train = pd.concat([df_jan_e60_dir_2_train, df_feb_e60_dir_2_train, df_mar_e60_dir_2_train], axis = 0, ignore_index=True)


# ### Testing Data Set

# In[ ]:


#print the code below
for e in range(1, 61):  # Loop for entity numbers 1 to 60
    for d in range(1, 3):  # Loop for directions 1 and 2
        print(f'df_e{e:02}_dir_{d}_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES{e:02}_Direction_{d}.json").loc[0:191, :]')


# In[78]:


df_e01_dir_1_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES01_Direction_1.json").loc[0:191, :]
df_e01_dir_2_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES01_Direction_2.json").loc[0:191, :]
df_e02_dir_1_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES02_Direction_1.json").loc[0:191, :]
df_e02_dir_2_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES02_Direction_2.json").loc[0:191, :]
df_e03_dir_1_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES03_Direction_1.json").loc[0:191, :]
df_e03_dir_2_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES03_Direction_2.json").loc[0:191, :]
df_e04_dir_1_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES04_Direction_1.json").loc[0:191, :]
df_e04_dir_2_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES04_Direction_2.json").loc[0:191, :]
df_e05_dir_1_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES05_Direction_1.json").loc[0:191, :]
df_e05_dir_2_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES05_Direction_2.json").loc[0:191, :]
df_e06_dir_1_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES06_Direction_1.json").loc[0:191, :]
df_e06_dir_2_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES06_Direction_2.json").loc[0:191, :]
df_e07_dir_1_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES07_Direction_1.json").loc[0:191, :]
df_e07_dir_2_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES07_Direction_2.json").loc[0:191, :]
df_e08_dir_1_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES08_Direction_1.json").loc[0:191, :]
df_e08_dir_2_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES08_Direction_2.json").loc[0:191, :]
df_e09_dir_1_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES09_Direction_1.json").loc[0:191, :]
df_e09_dir_2_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES09_Direction_2.json").loc[0:191, :]
df_e10_dir_1_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES10_Direction_1.json").loc[0:191, :]
df_e10_dir_2_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES10_Direction_2.json").loc[0:191, :]
df_e11_dir_1_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES11_Direction_1.json").loc[0:191, :]
df_e11_dir_2_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES11_Direction_2.json").loc[0:191, :]
df_e12_dir_1_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES12_Direction_1.json").loc[0:191, :]
df_e12_dir_2_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES12_Direction_2.json").loc[0:191, :]
df_e13_dir_1_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES13_Direction_1.json").loc[0:191, :]
df_e13_dir_2_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES13_Direction_2.json").loc[0:191, :]
df_e14_dir_1_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES14_Direction_1.json").loc[0:191, :]
df_e14_dir_2_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES14_Direction_2.json").loc[0:191, :]
df_e15_dir_1_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES15_Direction_1.json").loc[0:191, :]
df_e15_dir_2_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES15_Direction_2.json").loc[0:191, :]
df_e16_dir_1_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES16_Direction_1.json").loc[0:191, :]
df_e16_dir_2_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES16_Direction_2.json").loc[0:191, :]
df_e17_dir_1_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES17_Direction_1.json").loc[0:191, :]
df_e17_dir_2_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES17_Direction_2.json").loc[0:191, :]
df_e18_dir_1_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES18_Direction_1.json").loc[0:191, :]
df_e18_dir_2_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES18_Direction_2.json").loc[0:191, :]
df_e19_dir_1_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES19_Direction_1.json").loc[0:191, :]
df_e19_dir_2_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES19_Direction_2.json").loc[0:191, :]
df_e20_dir_1_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES20_Direction_1.json").loc[0:191, :]
df_e20_dir_2_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES20_Direction_2.json").loc[0:191, :]
df_e21_dir_1_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES21_Direction_1.json").loc[0:191, :]
df_e21_dir_2_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES21_Direction_2.json").loc[0:191, :]
df_e22_dir_1_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES22_Direction_1.json").loc[0:191, :]
df_e22_dir_2_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES22_Direction_2.json").loc[0:191, :]
df_e23_dir_1_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES23_Direction_1.json").loc[0:191, :]
df_e23_dir_2_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES23_Direction_2.json").loc[0:191, :]
df_e24_dir_1_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES24_Direction_1.json").loc[0:191, :]
df_e24_dir_2_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES24_Direction_2.json").loc[0:191, :]
df_e25_dir_1_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES25_Direction_1.json").loc[0:191, :]
df_e25_dir_2_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES25_Direction_2.json").loc[0:191, :]
df_e26_dir_1_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES26_Direction_1.json").loc[0:191, :]
df_e26_dir_2_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES26_Direction_2.json").loc[0:191, :]
df_e27_dir_1_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES27_Direction_1.json").loc[0:191, :]
df_e27_dir_2_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES27_Direction_2.json").loc[0:191, :]
df_e28_dir_1_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES28_Direction_1.json").loc[0:191, :]
df_e28_dir_2_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES28_Direction_2.json").loc[0:191, :]
df_e29_dir_1_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES29_Direction_1.json").loc[0:191, :]
df_e29_dir_2_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES29_Direction_2.json").loc[0:191, :]
df_e30_dir_1_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES30_Direction_1.json").loc[0:191, :]
df_e30_dir_2_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES30_Direction_2.json").loc[0:191, :]
df_e31_dir_1_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES31_Direction_1.json").loc[0:191, :]
df_e31_dir_2_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES31_Direction_2.json").loc[0:191, :]
df_e32_dir_1_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES32_Direction_1.json").loc[0:191, :]
df_e32_dir_2_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES32_Direction_2.json").loc[0:191, :]
df_e33_dir_1_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES33_Direction_1.json").loc[0:191, :]
df_e33_dir_2_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES33_Direction_2.json").loc[0:191, :]
df_e34_dir_1_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES34_Direction_1.json").loc[0:191, :]
df_e34_dir_2_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES34_Direction_2.json").loc[0:191, :]
#df_e35_dir_1_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES35_Direction_1.json").loc[0:191, :]
#df_e35_dir_2_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES35_Direction_2.json").loc[0:191, :]
df_e36_dir_1_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES36_Direction_1.json").loc[0:191, :]
df_e36_dir_2_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES36_Direction_2.json").loc[0:191, :]
df_e37_dir_1_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES37_Direction_1.json").loc[0:191, :]
df_e37_dir_2_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES37_Direction_2.json").loc[0:191, :]
df_e38_dir_1_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES38_Direction_1.json").loc[0:191, :]
df_e38_dir_2_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES38_Direction_2.json").loc[0:191, :]
df_e39_dir_1_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES39_Direction_1.json").loc[0:191, :]
df_e39_dir_2_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES39_Direction_2.json").loc[0:191, :]
df_e40_dir_1_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES40_Direction_1.json").loc[0:191, :]
df_e40_dir_2_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES40_Direction_2.json").loc[0:191, :]
df_e41_dir_1_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES41_Direction_1.json").loc[0:191, :]
df_e41_dir_2_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES41_Direction_2.json").loc[0:191, :]
df_e42_dir_1_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES42_Direction_1.json").loc[0:191, :]
df_e42_dir_2_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES42_Direction_2.json").loc[0:191, :]
df_e43_dir_1_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES43_Direction_1.json").loc[0:191, :]
df_e43_dir_2_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES43_Direction_2.json").loc[0:191, :]
df_e44_dir_1_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES44_Direction_1.json").loc[0:191, :]
df_e44_dir_2_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES44_Direction_2.json").loc[0:191, :]
df_e45_dir_1_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES45_Direction_1.json").loc[0:191, :]
df_e45_dir_2_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES45_Direction_2.json").loc[0:191, :]
df_e46_dir_1_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES46_Direction_1.json").loc[0:191, :]
df_e46_dir_2_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES46_Direction_2.json").loc[0:191, :]
df_e47_dir_1_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES47_Direction_1.json").loc[0:191, :]
df_e47_dir_2_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES47_Direction_2.json").loc[0:191, :]
df_e48_dir_1_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES48_Direction_1.json").loc[0:191, :]
df_e48_dir_2_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES48_Direction_2.json").loc[0:191, :]
df_e49_dir_1_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES49_Direction_1.json").loc[0:191, :]
df_e49_dir_2_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES49_Direction_2.json").loc[0:191, :]
df_e50_dir_1_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES50_Direction_1.json").loc[0:191, :]
df_e50_dir_2_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES50_Direction_2.json").loc[0:191, :]
df_e51_dir_1_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES51_Direction_1.json").loc[0:191, :]
df_e51_dir_2_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES51_Direction_2.json").loc[0:191, :]
df_e52_dir_1_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES52_Direction_1.json").loc[0:191, :]
df_e52_dir_2_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES52_Direction_2.json").loc[0:191, :]
df_e53_dir_1_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES53_Direction_1.json").loc[0:191, :]
df_e53_dir_2_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES53_Direction_2.json").loc[0:191, :]
df_e54_dir_1_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES54_Direction_1.json").loc[0:191, :]
df_e54_dir_2_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES54_Direction_2.json").loc[0:191, :]
df_e55_dir_1_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES55_Direction_1.json").loc[0:191, :]
df_e55_dir_2_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES55_Direction_2.json").loc[0:191, :]
df_e56_dir_1_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES56_Direction_1.json").loc[0:191, :]
df_e56_dir_2_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES56_Direction_2.json").loc[0:191, :]
df_e57_dir_1_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES57_Direction_1.json").loc[0:191, :]
df_e57_dir_2_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES57_Direction_2.json").loc[0:191, :]
df_e58_dir_1_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES58_Direction_1.json").loc[0:191, :]
df_e58_dir_2_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES58_Direction_2.json").loc[0:191, :]
df_e59_dir_1_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES59_Direction_1.json").loc[0:191, :]
df_e59_dir_2_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES59_Direction_2.json").loc[0:191, :]
df_e60_dir_1_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES60_Direction_1.json").loc[0:191, :]
df_e60_dir_2_test = read_traffic_flow_data("data_traffic_json/apr/urn_ngsi-ld_TrafficFlowObserved_ES60_Direction_2.json").loc[0:191, :]


# ### Scaling

# In[79]:


column_names = ["TS1",  "TS2",  "TS3",  "TS4",  "TS5",  "TS6",
                "TS7",  "TS8",  "TS9",  "TS11", "TS12",
                "TS13", "TS14", "TS15", "TS16", "TS17", "TS18",
                "TS19", "TS20", "TS21", "TS22", "TS23", "TS24",
                "TS25", "TS26", "TS27", "TS28", "TS29", "TS30",
                "TS31", "TS32", "TS33", "TS34", "TS36",
                "TS37", "TS38", "TS39", "TS40", "TS41", "TS42",
                "TS43", "TS44", "TS45", "TS46", "TS47", "TS48",
                "TS49", "TS50", "TS51", "TS52", "TS53", "TS54",
                "TS55", "TS56", "TS57", "TS58", "TS59", "TS60"
                ]


# ### Train all

# In[81]:


df_all_train_value = pd.concat([
    df_e01_dir_1_train['value'], df_e02_dir_1_train['value'], df_e03_dir_1_train['value'], df_e04_dir_1_train['value'], df_e05_dir_1_train['value'], df_e06_dir_1_train['value'],
    df_e07_dir_1_train['value'], df_e08_dir_1_train['value'], df_e09_dir_1_train['value'], df_e11_dir_1_train['value'], df_e12_dir_1_train['value'],
    df_e13_dir_1_train['value'], df_e14_dir_1_train['value'], df_e15_dir_1_train['value'], df_e16_dir_1_train['value'], df_e17_dir_1_train['value'], df_e18_dir_1_train['value'],
    df_e19_dir_1_train['value'], df_e20_dir_1_train['value'], df_e21_dir_1_train['value'], df_e22_dir_1_train['value'], df_e23_dir_1_train['value'], df_e24_dir_1_train['value'],
    df_e25_dir_1_train['value'], df_e26_dir_1_train['value'], df_e27_dir_1_train['value'], df_e28_dir_1_train['value'], df_e29_dir_1_train['value'], df_e30_dir_1_train['value'],
    df_e31_dir_1_train['value'], df_e32_dir_1_train['value'], df_e33_dir_1_train['value'], df_e34_dir_1_train['value'], df_e36_dir_1_train['value'],
    df_e37_dir_1_train['value'], df_e38_dir_1_train['value'], df_e39_dir_1_train['value'], df_e40_dir_1_train['value'], df_e41_dir_1_train['value'], df_e42_dir_1_train['value'],
    df_e43_dir_1_train['value'], df_e44_dir_1_train['value'], df_e45_dir_1_train['value'], df_e46_dir_1_train['value'], df_e47_dir_1_train['value'], df_e48_dir_1_train['value'],
    df_e49_dir_1_train['value'], df_e50_dir_1_train['value'], df_e51_dir_1_train['value'], df_e52_dir_1_train['value'], df_e53_dir_1_train['value'], df_e54_dir_1_train['value'],
    df_e55_dir_1_train['value'], df_e56_dir_1_train['value'], df_e57_dir_1_train['value'], df_e58_dir_1_train['value'], df_e59_dir_1_train['value'], df_e60_dir_1_train['value']]
, axis=1)

# Rename the columns
df_all_train_value.columns = column_names


# ### Test all

# In[82]:


df_all_test_value = pd.concat([
    df_e01_dir_1_test['value'], df_e02_dir_1_test['value'], df_e03_dir_1_test['value'], df_e04_dir_1_test['value'], df_e05_dir_1_test['value'], df_e06_dir_1_test['value'],
    df_e07_dir_1_test['value'], df_e08_dir_1_test['value'], df_e09_dir_1_test['value'], df_e11_dir_1_test['value'], df_e12_dir_1_test['value'],
    df_e13_dir_1_test['value'], df_e14_dir_1_test['value'], df_e15_dir_1_test['value'], df_e16_dir_1_test['value'], df_e17_dir_1_test['value'], df_e18_dir_1_test['value'],
    df_e19_dir_1_test['value'], df_e20_dir_1_test['value'], df_e21_dir_1_test['value'], df_e22_dir_1_test['value'], df_e23_dir_1_test['value'], df_e24_dir_1_test['value'],
    df_e25_dir_1_test['value'], df_e26_dir_1_test['value'], df_e27_dir_1_test['value'], df_e28_dir_1_test['value'], df_e29_dir_1_test['value'], df_e30_dir_1_test['value'],
    df_e31_dir_1_test['value'], df_e32_dir_1_test['value'], df_e33_dir_1_test['value'], df_e34_dir_1_test['value'], df_e36_dir_1_test['value'],
    df_e37_dir_1_test['value'], df_e38_dir_1_test['value'], df_e39_dir_1_test['value'], df_e40_dir_1_test['value'], df_e41_dir_1_test['value'], df_e42_dir_1_test['value'],
    df_e43_dir_1_test['value'], df_e44_dir_1_test['value'], df_e45_dir_1_test['value'], df_e46_dir_1_test['value'], df_e47_dir_1_test['value'], df_e48_dir_1_test['value'],
    df_e49_dir_1_test['value'], df_e50_dir_1_test['value'], df_e51_dir_1_test['value'], df_e52_dir_1_test['value'], df_e53_dir_1_test['value'], df_e54_dir_1_test['value'],
    df_e55_dir_1_test['value'], df_e56_dir_1_test['value'], df_e57_dir_1_test['value'], df_e58_dir_1_test['value'], df_e59_dir_1_test['value'], df_e60_dir_1_test['value']]
, axis=1 )
# Rename the columns
df_all_test_value.columns = column_names


# In[84]:


df_all_value = pd.concat([df_all_train_value, df_all_test_value], axis = 0, ignore_index=True)
df_all_value


# In[85]:


df_all_test_value_scaled = (df_all_test_value - df_all_value.min(axis=0)) / (df_all_value.max(axis=0) - df_all_value.min(axis=0))
df_all_test_value_scaled


# In[86]:


df_all_train_value_scaled = (df_all_train_value - df_all_value.min(axis=0)) / (df_all_value.max(axis=0) - df_all_value.min(axis=0))
df_all_train_value_scaled

