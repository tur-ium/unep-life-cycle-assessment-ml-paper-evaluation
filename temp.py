import seaborn as sns
import matplotlib.pyplot as plt
import geopandas as gpd
import pandas as pd

# Data
data = {
    'Country': ['United States of America', 'Germany', 'The Netherlands', 'Canada', 'Switzerland', 'Czech Republic', 'Singapore', 'Sweden', 'India', 'Chile', 'United Kingdom', 'Italy', 'Mexico','China'],
    'Value': [5, 3, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,1]
}

url = "https://naciscdn.org/naturalearth/110m/cultural/ne_110m_admin_0_countries.zip"

# Create a DataFrame
df = pd.DataFrame(data)

# Load the world map
world = gpd.read_file(url)

# Merge the data with the world map
merged = world.set_index('NAME').join(df.set_index('Country'))
# Fill NaN values with 0 for countries with no data
merged['Value'] = merged['Value'].fillna(0)

# Plot the map
fig, ax = plt.subplots(1, 1, figsize=(15, 10))

# Plot continents with data in green
continents_with_data = merged[merged['Value'] > 0].dissolve(by='CONTINENT')
continents_with_data.plot(ax=ax, color='green', edgecolor='black', linewidth=0.5)

continents_without_data = merged[merged['Value'] == 0].dissolve(by='CONTINENT')
continents_without_data.plot(ax=ax, color='#ccc', edgecolor='black', linewidth=0.5)

# Plot the map by country
# fig, ax = plt.subplots(1, 1, figsize=(15, 10))
# merged[merged['Value'] > 0].plot(column='Value', ax=ax, color='green', legend_kwds={'label': "Value", 'orientation': "horizontal"},edgecolor='black',linewidth=0.2)
# merged[merged['Value'] == 0].plot(ax=ax, color='#ccc', edgecolor='black', linewidth=0.5)

# Add titles and labels
ax.set_title('Participation by country', fontdict={'fontsize': '25', 'fontweight': '3'})
ax.set_xlabel('Longitude')
ax.set_ylabel('Latitude')

# Show the plot
plt.show()


import geopandas as gpd
import matplotlib.pyplot as plt

# Load Natural Earth cultural vectors
# world = gpd.read_file(gpd.datasets.get_path('naturalearth_lowres'))

# Data
data = {
    'Continent': ['Asia', 'Central America', 'Europe', 'North America', 'South America'],
    'Value': [3, 1, 10, 6, 1]
}

# Create DataFrame
df = pd.DataFrame(data)

# Merge data with world map
world = world.merge(df, how='left', left_on='CONTINENT', right_on='Continent')

# Plot
fig, ax = plt.subplots(1, 1, figsize=(15, 10))
# world.boundary.plot(ax=ax)
world[world['Value'] > 0].plot(color='green', legend=True, ax=ax, linewidth=0)
world[world['Value'].isna()].plot(color='grey', legend=True, ax=ax, linewidth=0)
plt.title('Participation by continent')
plt.show()