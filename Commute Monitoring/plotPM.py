import pandas as pd
import datetime as dt
import numpy as np
import matplotlib.pyplot as plt

import gpxpy.gpx

# ----- PARAMS
subject = 'D'
raw_data_file = 'input.csv'

# populate the dataframe with the raw commute data
df = pd.read_csv(subject+'/'+raw_data_file)
date = pd.to_datetime(df.iloc[0]['WriteTime'], format="%d/%m/%Y", exact='False').date()
df.drop(index=0, inplace=True)
start_len = len(df)

# populate missing DateTime values
df['WriteTime'] = pd.to_datetime(str(date) + ' ' + df['WriteTime'])
for i in range(1, len(df)):
    if df.loc[len(df)-i, 'WriteTime'] == dt.datetime(year=date.year, month=date.month, day=date.day, hour=0, minute=0, second=0):
        df.loc[len(df)-i, 'WriteTime'] = df.loc[len(df)-i+1, 'WriteTime'] - dt.timedelta(seconds=3)

# adjust for BST
df['WriteTime'] = df['WriteTime'].apply(lambda x: x + dt.timedelta(hours=1))

# clean and set index
df.drop_duplicates(subset='WriteTime', inplace=True)
df.set_index('WriteTime', inplace=True)

# replace invalid measurements with adjacent data
df.loc[df['Temp'] >= 50, 'Temp'] = np.nan
df.loc[df['RH'] >= 0.999, 'RH'] = np.nan
df.fillna(method='ffill', inplace=True)
df.fillna(method='bfill', inplace=True) # fill first value in case of NaN row 0

# format lat and lng values correctly
df['1000Lat'] = df['1000Lat']/1000
df['1000Lng'] = df['1000Lng']/1000
df.rename(columns={'1000Lat': 'Lat', '1000Lng': 'Lng'}, inplace=True)

df = df.sort_index()
print(df)

df['PM2.5'].plot()
plt.show()