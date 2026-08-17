import pandas as pd
from pathlib import Path

# Load XAUUSD.csv
# Structure: <DATE>\t<TIME>\t<OPEN>\t<HIGH>\t<LOW>\t<CLOSE>\t<TICKVOL>\t<VOL>\t<SPREAD>
csv_path = "XAUUSD.csv"
df = pd.read_csv(csv_path, sep='\t')

# Convert <DATE> to datetime
df['<DATE>'] = pd.to_datetime(df['<DATE>'], format='%Y.%m.%d')

# Iterate through months and save separate CSVs
# Required by bot: XAUUSD_2025_10, 11, 12 and 2026_01
months_to_extract = [
    (2025, 10), (2025, 11), (2025, 12), (2026, 1), (2026, 2), (2026, 3)
]

for year, month in months_to_extract:
    month_df = df[(df['<DATE>'].dt.year == year) & (df['<DATE>'].dt.month == month)]
    if not month_df.empty:
        output_name = f"XAUUSD_{year}_{month:02d}.csv"
        # Bot expects tab-separated with specific headers?
        # Actually, let's keep it as is, but save it.
        month_df.to_csv(output_name, sep='\t', index=False)
        print(f"Generated {output_name}")
    else:
        print(f"No data found for {year}-{month:02d}")
