import pandas as pd

df = pd.read_csv('csvread.csv')

date = pd.to_datetime(df.iloc[0]['WriteTime'], format="%d/%m/%y").date()
df = df.drop(index=0)

# df['WriteTime'] = pd.to_datetime(df['WriteTime'], format="%H:%M:%S").dt.time
df['WriteTime'] = pd.to_datetime(str(date) + ' ' + df['WriteTime'])
df['1000Lat'] = df['1000Lat']/1000
df['1000Lng'] = df['1000Lng']/1000
df.rename(columns={'1000Lat': 'Lat', '1000Lng': 'Lng'}, inplace=True)

print(date)
print(df.head())
