"""
Auto-generated Python translation of Alteryx workflow 'Demo Claims Volume Extract'.
"""

import pandas as pd


# Alteryx Tool #1: DbFileInput
# Plugin: AlteryxBasePluginsGui.DbFileInput.DbFileInput
# Translation: FULL
# Read CSV file: .\Data\Claims_Volume_Extract_Demo.xlsx|||Sheet1$
# INFO: External file dependency: '.\Data\Claims_Volume_Extract_Demo.xlsx|||Sheet1$' is referenced by Tool #1
df_1 = pd.read_csv('.\\Data\\Claims_Volume_Extract_Demo.xlsx|||Sheet1$')

# Alteryx Tool #101: DbFileInput
# Plugin: AlteryxBasePluginsGui.DbFileInput.DbFileInput
# Translation: FULL
# Read CSV file: .\Data\Policy_Master_Demo.xlsx|||Sheet1$
# INFO: External file dependency: '.\Data\Policy_Master_Demo.xlsx|||Sheet1$' is referenced by Tool #101
df_101 = pd.read_csv('.\\Data\\Policy_Master_Demo.xlsx|||Sheet1$')

# Alteryx Tool #102: DbFileInput
# Plugin: AlteryxBasePluginsGui.DbFileInput.DbFileInput
# Translation: FULL
# Read CSV file: .\Data\Claim_Payments_Demo.xlsx|||Sheet1$
# INFO: External file dependency: '.\Data\Claim_Payments_Demo.xlsx|||Sheet1$' is referenced by Tool #102
df_102 = pd.read_csv('.\\Data\\Claim_Payments_Demo.xlsx|||Sheet1$')

# Alteryx Tool #103: DbFileInput
# Plugin: AlteryxBasePluginsGui.DbFileInput.DbFileInput
# Translation: FULL
# Read CSV file: .\Data\Claim_Diary_Notes_Demo.xlsx|||Sheet1$
# INFO: External file dependency: '.\Data\Claim_Diary_Notes_Demo.xlsx|||Sheet1$' is referenced by Tool #103
df_103 = pd.read_csv('.\\Data\\Claim_Diary_Notes_Demo.xlsx|||Sheet1$')

# Alteryx Tool #2: BlockUntilDone
# Plugin: AlteryxBasePluginsGui.BlockUntilDone.BlockUntilDone
# Translation: PASS_THROUGH
# Pass-through / Inspection tool (BlockUntilDone)
# Tool #2: BlockUntilDone (Pass-through / Inspection)
# Operation does not modify dataset semantics; passes incoming dataframe through.

# Alteryx Tool #104: Summarize
# Plugin: AlteryxSpatialPluginsGui.Summarize.Summarize
# Translation: FULL
# Summarize (empty)
df_104 = df_102.copy()

# Alteryx Tool #3: Summarize
# Plugin: AlteryxSpatialPluginsGui.Summarize.Summarize
# Translation: FULL
# Summarize (empty)
df_3 = df_2.copy()

# Alteryx Tool #8: Summarize
# Plugin: AlteryxSpatialPluginsGui.Summarize.Summarize
# Translation: FULL
# Summarize (empty)
df_8 = df_2.copy()

# Alteryx Tool #15: AlteryxSelect
# Plugin: AlteryxBasePluginsGui.AlteryxSelect.AlteryxSelect
# Translation: FULL
# Select: passthrough (no fields specified)
df_15 = df_2.copy()

# Alteryx Tool #111: Join
# Plugin: AlteryxBasePluginsGui.Join.Join
# Translation: FULL
# Join: Cross join (no join fields specified)
df_111_joined = pd.merge(df_2, df_101, how='cross')
df_111_left_only = df_2.iloc[0:0].copy()
df_111_right_only = df_101.iloc[0:0].copy()

# Alteryx Tool #4: CrossTab
# Plugin: AlteryxBasePluginsGui.CrossTab.CrossTab
# Translation: FULL
# CrossTab: pivot on 'Claim Status' with values='CountDistinct_Claim Number' (sum)
df_4 = pd.pivot_table(
    df_3,
    index=[],
    columns='Claim Status',
    values='CountDistinct_Claim Number',
    aggfunc='sum',
).reset_index()
df_4.columns.name = None

# Alteryx Tool #9: Summarize
# Plugin: AlteryxSpatialPluginsGui.Summarize.Summarize
# Translation: FULL
# Summarize (empty)
df_9 = df_8.copy()

# Alteryx Tool #16: Sort
# Plugin: AlteryxBasePluginsGui.Sort.Sort
# Translation: FULL
# Sort: passthrough
df_16 = df_15.copy()

# Alteryx Tool #112: Join
# Plugin: AlteryxBasePluginsGui.Join.Join
# Translation: FULL
# Join: Cross join (no join fields specified)
df_112_joined = pd.merge(df_111_joined, df_104, how='cross')
df_112_left_only = df_111_joined.iloc[0:0].copy()
df_112_right_only = df_104.iloc[0:0].copy()

# Alteryx Tool #5: AlteryxSelect
# Plugin: AlteryxBasePluginsGui.AlteryxSelect.AlteryxSelect
# Translation: FULL
# Select: passthrough (no fields specified)
df_5 = df_4.copy()

# Alteryx Tool #10: Join
# Plugin: AlteryxBasePluginsGui.Join.Join
# Translation: FULL
# Join: Cross join (no join fields specified)
df_10_joined = pd.merge(df_8, df_9, how='cross')
df_10_left_only = df_8.iloc[0:0].copy()
df_10_right_only = df_9.iloc[0:0].copy()

# Alteryx Tool #17: DbFileOutput
# Plugin: AlteryxBasePluginsGui.DbFileOutput.DbFileOutput
# Translation: FULL
# Write CSV file: Claims_Historical_Extract_Demo_Output.xlsx|||Detail
# INFO: External file destination: 'Claims_Historical_Extract_Demo_Output.xlsx|||Detail' is referenced by Tool #17
df_16.to_csv('Claims_Historical_Extract_Demo_Output.xlsx|||Detail', index=False)

# Alteryx Tool #113: Union
# Plugin: AlteryxBasePluginsGui.Union.Union
# Translation: FULL
# Union 2 stream(s)
df_113 = pd.concat([df_112_joined, df_112_left_only], ignore_index=True, sort=False)

# Alteryx Tool #6: Sort
# Plugin: AlteryxBasePluginsGui.Sort.Sort
# Translation: FULL
# Sort: passthrough
df_6 = df_5.copy()

# Alteryx Tool #11: CrossTab
# Plugin: AlteryxBasePluginsGui.CrossTab.CrossTab
# Translation: FULL
# CrossTab: pivot on 'Claim Status' with values='CountDistinct_Claim Number' (sum)
df_11 = pd.pivot_table(
    df_10_joined,
    index=[],
    columns='Claim Status',
    values='CountDistinct_Claim Number',
    aggfunc='sum',
).reset_index()
df_11.columns.name = None

# Alteryx Tool #114: Formula
# Plugin: AlteryxBasePluginsGui.Formula.Formula
# Translation: FULL
# Formula with 0 field(s)
# WARNING: Formula has no formula fields
df_114 = df_113.copy()

# Alteryx Tool #7: BrowseV2
# Plugin: AlteryxBasePluginsGui.BrowseV2.BrowseV2
# Translation: PASS_THROUGH
# Pass-through / Inspection tool (BrowseV2)
# Tool #7: BrowseV2 (Pass-through / Inspection)
# Operation does not modify dataset semantics; passes incoming dataframe through.

# Alteryx Tool #18: DbFileOutput
# Plugin: AlteryxBasePluginsGui.DbFileOutput.DbFileOutput
# Translation: FULL
# Write CSV file: Claims_Historical_Extract_Demo_Output.xlsx|||QuarterSummary
# INFO: External file destination: 'Claims_Historical_Extract_Demo_Output.xlsx|||QuarterSummary' is referenced by Tool #18
df_6.to_csv('Claims_Historical_Extract_Demo_Output.xlsx|||QuarterSummary', index=False)

# Alteryx Tool #12: AlteryxSelect
# Plugin: AlteryxBasePluginsGui.AlteryxSelect.AlteryxSelect
# Translation: FULL
# Select: passthrough (no fields specified)
df_12 = df_11.copy()

# Alteryx Tool #115: Join
# Plugin: AlteryxBasePluginsGui.Join.Join
# Translation: FULL
# Join: Cross join (no join fields specified)
df_115_joined = pd.merge(df_114, df_103, how='cross')
df_115_left_only = df_114.iloc[0:0].copy()
df_115_right_only = df_103.iloc[0:0].copy()

# Alteryx Tool #13: Sort
# Plugin: AlteryxBasePluginsGui.Sort.Sort
# Translation: FULL
# Sort: passthrough
df_13 = df_12.copy()

# Alteryx Tool #116: Union
# Plugin: AlteryxBasePluginsGui.Union.Union
# Translation: FULL
# Union 2 stream(s)
df_116 = pd.concat([df_115_joined, df_115_left_only], ignore_index=True, sort=False)

# Alteryx Tool #14: BrowseV2
# Plugin: AlteryxBasePluginsGui.BrowseV2.BrowseV2
# Translation: PASS_THROUGH
# Pass-through / Inspection tool (BrowseV2)
# Tool #14: BrowseV2 (Pass-through / Inspection)
# Operation does not modify dataset semantics; passes incoming dataframe through.

# Alteryx Tool #117: Formula
# Plugin: AlteryxBasePluginsGui.Formula.Formula
# Translation: FULL
# Formula with 0 field(s)
# WARNING: Formula has no formula fields
df_117 = df_116.copy()

# Alteryx Tool #118: Formula
# Plugin: AlteryxBasePluginsGui.Formula.Formula
# Translation: FULL
# Formula with 0 field(s)
# WARNING: Formula has no formula fields
df_118 = df_117.copy()

# Alteryx Tool #130: Summarize
# Plugin: AlteryxSpatialPluginsGui.Summarize.Summarize
# Translation: FULL
# Summarize (empty)
df_130 = df_118.copy()

# Alteryx Tool #140: Summarize
# Plugin: AlteryxSpatialPluginsGui.Summarize.Summarize
# Translation: FULL
# Summarize (empty)
df_140 = df_118.copy()

# Alteryx Tool #150: Summarize
# Plugin: AlteryxSpatialPluginsGui.Summarize.Summarize
# Translation: FULL
# Summarize (empty)
df_150 = df_118.copy()

# Alteryx Tool #131: Sort
# Plugin: AlteryxBasePluginsGui.Sort.Sort
# Translation: FULL
# Sort: passthrough
df_131 = df_130.copy()

# Alteryx Tool #141: Sort
# Plugin: AlteryxBasePluginsGui.Sort.Sort
# Translation: FULL
# Sort: passthrough
df_141 = df_140.copy()

# Alteryx Tool #151: Sort
# Plugin: AlteryxBasePluginsGui.Sort.Sort
# Translation: FULL
# Sort: passthrough
df_151 = df_150.copy()

# Alteryx Tool #132: DbFileOutput
# Plugin: AlteryxBasePluginsGui.DbFileOutput.DbFileOutput
# Translation: FULL
# Write CSV file: Claims_By_Product_Type_Demo_Output.xlsx|||ProductTypeSummary
# INFO: External file destination: 'Claims_By_Product_Type_Demo_Output.xlsx|||ProductTypeSummary' is referenced by Tool #132
df_131.to_csv('Claims_By_Product_Type_Demo_Output.xlsx|||ProductTypeSummary', index=False)

# Alteryx Tool #142: DbFileOutput
# Plugin: AlteryxBasePluginsGui.DbFileOutput.DbFileOutput
# Translation: FULL
# Write CSV file: Claims_By_State_Demo_Output.xlsx|||StateSummary
# INFO: External file destination: 'Claims_By_State_Demo_Output.xlsx|||StateSummary' is referenced by Tool #142
df_141.to_csv('Claims_By_State_Demo_Output.xlsx|||StateSummary', index=False)

# Alteryx Tool #152: DbFileOutput
# Plugin: AlteryxBasePluginsGui.DbFileOutput.DbFileOutput
# Translation: FULL
# Write CSV file: Claims_Aging_Risk_Demo_Output.xlsx|||AgingRiskSummary
# INFO: External file destination: 'Claims_Aging_Risk_Demo_Output.xlsx|||AgingRiskSummary' is referenced by Tool #152
df_151.to_csv('Claims_Aging_Risk_Demo_Output.xlsx|||AgingRiskSummary', index=False)
