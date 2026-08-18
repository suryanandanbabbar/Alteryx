# AWA Top-100 Alteryx Tool Support Matrix

This matrix outlines the analysis, parsing, Python code generation, and support classification for the **top 100 Alteryx tools**.

| # | Category | Tool Name | XML Tool Name | Config Parsing | Python Translation | Support Level |
|---|---|---|---|---|---|---|
| 1 | Connectors | Amazon S3 Download | `AmazonS3Download.yxmc` | Yes | No | `external_execution` |
| 2 | Connectors | Amazon S3 Upload | `AmazonS3Upload.yxmc` | Yes | No | `external_execution` |
| 3 | Connectors | MongoDB Input | `AlteryxConnectorGui.MongoInput.MongoInput` | Yes | No | `external_execution` |
| 4 | Connectors | MongoDB Output | `AlteryxConnectorGui.MongoOutput.MongoOutput` | Yes | No | `external_execution` |
| 5 | Connectors | Salesforce Input | `SalesforceInput.yxmc` | Yes | No | `external_execution` |
| 6 | Connectors | Salesforce Output (New) | `SalesforceOutput.yxmc` | Yes | No | `external_execution` |
| 7 | Connectors | SharePoint Files Input | `SharePointFilesInput.yxmc` | Yes | No | `external_execution` |
| 8 | Connectors | SharePoint Files Output | `SharePointFilesOutput.yxmc` | Yes | No | `external_execution` |
| 9 | Connectors | Tableau Output | `TableauOutput.yxmc` | Yes | No | `external_execution` |
| 10 | Developer | Block Until Done | `AlteryxBasePluginsGui.BlockUntilDone.BlockUntilDone` | Yes | No | `pass_through` |
| 11 | Developer | Detour | `AlteryxBasePluginsGui.Detour.Detour` | Yes | No | `partial` |
| 12 | Developer | Detour End | `AlteryxBasePluginsGui.DetourEnd.DetourEnd` | Yes | No | `pass_through` |
| 13 | Developer | Download | `AlteryxConnectorGui.Download.Download` | Yes | No | `external_execution` |
| 14 | Developer | Dynamic Input | `AlteryxBasePluginsGui.DynamicInput.DynamicInput` | Yes | No | `partial` |
| 15 | Developer | Dynamic Rename | `AlteryxBasePluginsGui.DynamicRename.DynamicRename` | Yes | Yes | `full` |
| 16 | Developer | Dynamic Replace | `AlteryxBasePluginsGui.DynamicReplace.DynamicReplace` | Yes | No | `partial` |
| 17 | Developer | Dynamic Select | `AlteryxBasePluginsGui.DynamicSelect.DynamicSelect` | Yes | Yes | `full` |
| 18 | Developer | Field Info | `AlteryxBasePluginsGui.FieldInfo.FieldInfo` | Yes | Yes | `full` |
| 19 | Developer | JSON Build | `AlteryxBasePluginsGui.JSONBuild.JSONBuild` | Yes | Yes | `full` |
| 20 | Developer | JSON Parse | `AlteryxBasePluginsGui.JSONParse.JSONParse` | Yes | Yes | `full` |
| 21 | Developer | Message | `AlteryxBasePluginsGui.Message.Message` | Yes | No | `pass_through` |
| 22 | Developer | Python | `Python` | Yes | No | `external_execution` |
| 23 | Developer | R | `AlteryxRPluginGui.R.R` | Yes | No | `external_execution` |
| 24 | Developer | Run Command | `AlteryxBasePluginsGui.RunCommand.RunCommand` | Yes | No | `external_execution` |
| 25 | Documentation | Comment | `AlteryxGuiToolkit.TextBox.TextBox` | Yes | No | `documentation_only` |
| 26 | Documentation | Tool Container | `AlteryxGuiToolkit.ToolContainer.ToolContainer` | Yes | No | `documentation_only` |
| 27 | In-Database | Connect In-DB | `LockInGui.LockInInput.LockInInput` | Yes | No | `external_execution` |
| 28 | In-Database | Data Stream In | `LockInGui.LockInStreamIn.LockInStreamIn` | Yes | No | `external_execution` |
| 29 | In-Database | Data Stream Out | `LockInGui.LockInStreamOut.LockInStreamOut` | Yes | No | `external_execution` |
| 30 | In-Database | Filter In-DB | `LockInGui.LockInFilter.LockInFilter` | Yes | No | `external_execution` |
| 31 | In-Database | Formula In-DB | `LockInGui.LockInFormula.LockInFormula` | Yes | No | `external_execution` |
| 32 | In-Database | Join In-DB | `LockInGui.LockInJoin.LockInJoin` | Yes | No | `external_execution` |
| 33 | In-Database | Select In-DB | `LockInGui.LockInSelect.LockInSelect` | Yes | No | `external_execution` |
| 34 | In/Out | Browse | `AlteryxBasePluginsGui.BrowseV2.BrowseV2` | Yes | No | `pass_through` |
| 35 | In/Out | Date Time Now | `DateTimeNow` | Yes | Yes | `full` |
| 36 | In/Out | Directory | `AlteryxBasePluginsGui.Directory.Directory` | Yes | No | `partial` |
| 37 | In/Out | Input Data | `AlteryxBasePluginsGui.DbFileInput.DbFileInput` | Yes | Yes | `full` |
| 38 | In/Out | Output Data | `AlteryxBasePluginsGui.DbFileOutput.DbFileOutput` | Yes | Yes | `full` |
| 39 | In/Out | Text Input | `AlteryxBasePluginsGui.TextInput.TextInput` | Yes | Yes | `full` |
| 40 | Join | Append Fields | `AlteryxBasePluginsGui.AppendFields.AppendFields` | Yes | Yes | `full` |
| 41 | Join | Find Replace | `AlteryxBasePluginsGui.FindReplace.FindReplace` | Yes | Yes | `full` |
| 42 | Join | Fuzzy Match | `AlteryxBasePluginsGui.FuzzyMatch.FuzzyMatch` | Yes | No | `partial` |
| 43 | Join | Join | `AlteryxBasePluginsGui.Join.Join` | Yes | Yes | `full` |
| 44 | Join | Join Multiple | `AlteryxBasePluginsGui.JoinMultiple.JoinMultiple` | Yes | Yes | `full` |
| 45 | Join | Make Group | `AlteryxBasePluginsGui.MakeGroup.MakeGroup` | Yes | No | `partial` |
| 46 | Join | Union | `AlteryxBasePluginsGui.Union.Union` | Yes | Yes | `full` |
| 47 | Parse | DateTime | `AlteryxBasePluginsGui.DateTime.DateTime` | Yes | Yes | `full` |
| 48 | Parse | RegEx | `AlteryxBasePluginsGui.RegEx.RegEx` | Yes | Yes | `full` |
| 49 | Parse | Text To Columns | `AlteryxBasePluginsGui.TextToColumns.TextToColumns` | Yes | Yes | `full` |
| 50 | Parse | XML Parse | `AlteryxBasePluginsGui.XMLParse.XMLParse` | Yes | No | `partial` |
| 51 | Preparation | Auto Field | `AlteryxBasePluginsGui.AutoField.AutoField` | Yes | Yes | `full` |
| 52 | Preparation | Create Samples | `CreateSamples.yxmc` | Yes | Yes | `full` |
| 53 | Preparation | Data Cleanse Pro | `DataCleansePro` | Yes | No | `partial` |
| 54 | Preparation | Data Cleansing | `Cleanse.yxmc` | Yes | Yes | `full` |
| 55 | Preparation | Filter | `AlteryxBasePluginsGui.Filter.Filter` | Yes | Yes | `full` |
| 56 | Preparation | Formula | `AlteryxBasePluginsGui.Formula.Formula` | Yes | Yes | `full` |
| 57 | Preparation | Generate Rows | `AlteryxBasePluginsGui.GenerateRows.GenerateRows` | Yes | Yes | `full` |
| 58 | Preparation | Multi-Field Binning | `MultiFieldBinning.yxmc` | Yes | No | `partial` |
| 59 | Preparation | Multi-Field Formula | `AlteryxBasePluginsGui.MultiFieldFormula.MultiFieldFormula` | Yes | Yes | `full` |
| 60 | Preparation | Multi-Row Formula | `AlteryxBasePluginsGui.MultiRowFormula.MultiRowFormula` | Yes | Yes | `full` |
| 61 | Preparation | Random % Sample | `RandomSampleSize.yxmc` | Yes | Yes | `full` |
| 62 | Preparation | Rank | `AlteryxBasePluginsGui.Rank.Rank` | Yes | Yes | `full` |
| 63 | Preparation | Record ID | `AlteryxBasePluginsGui.RecordID.RecordID` | Yes | Yes | `full` |
| 64 | Preparation | Sample | `AlteryxBasePluginsGui.Sample.Sample` | Yes | Yes | `full` |
| 65 | Preparation | Select | `AlteryxBasePluginsGui.AlteryxSelect.AlteryxSelect` | Yes | Yes | `full` |
| 66 | Preparation | Select Records | `AlteryxBasePluginsGui.SelectRecords.SelectRecords` | Yes | Yes | `full` |
| 67 | Preparation | Sort | `AlteryxBasePluginsGui.Sort.Sort` | Yes | Yes | `full` |
| 68 | Preparation | Tile | `AlteryxBasePluginsGui.Tile.Tile` | Yes | No | `partial` |
| 69 | Preparation | Unique | `AlteryxBasePluginsGui.Unique.Unique` | Yes | Yes | `full` |
| 70 | Reporting | Email | `AlteryxReportPluginsGui.Email.Email` | Yes | No | `external_execution` |
| 71 | Reporting | Image | `AlteryxReportPluginsGui.Image.Image` | Yes | No | `documentation_only` |
| 72 | Reporting | Interactive Chart | `AlteryxReportPluginsGui.InteractiveChart.InteractiveChart` | Yes | No | `documentation_only` |
| 73 | Reporting | Layout | `AlteryxReportPluginsGui.Layout.Layout` | Yes | No | `documentation_only` |
| 74 | Reporting | Render | `AlteryxReportPluginsGui.Render.Render` | Yes | No | `documentation_only` |
| 75 | Reporting | Report Footer | `ReportFooter.yxmc` | Yes | No | `documentation_only` |
| 76 | Reporting | Report Header | `ReportHeader.yxmc` | Yes | No | `documentation_only` |
| 77 | Reporting | Report Map | `AlteryxReportPluginsGui.ReportMap.ReportMap` | Yes | No | `documentation_only` |
| 78 | Reporting | Report Text | `AlteryxReportPluginsGui.ReportText.ReportText` | Yes | No | `documentation_only` |
| 79 | Reporting | Table | `AlteryxReportPluginsGui.Table.Table` | Yes | No | `documentation_only` |
| 80 | Spatial | Buffer | `AlteryxSpatialPluginsGui.Buffer.Buffer` | Yes | No | `partial` |
| 81 | Spatial | Create Points | `AlteryxSpatialPluginsGui.CreatePoints.CreatePoints` | Yes | No | `partial` |
| 82 | Spatial | Distance | `AlteryxSpatialPluginsGui.Distance.Distance` | Yes | No | `partial` |
| 83 | Spatial | Find Nearest | `AlteryxSpatialPluginsGui.FindNearest.FindNearest` | Yes | No | `partial` |
| 84 | Spatial | Generalize | `AlteryxSpatialPluginsGui.Generalize.Generalize` | Yes | No | `partial` |
| 85 | Spatial | Heat Map | `HeatMap.yxmc` | Yes | No | `partial` |
| 86 | Spatial | Make Grid | `AlteryxSpatialPluginsGui.MakeGrid.MakeGrid` | Yes | No | `partial` |
| 87 | Spatial | Poly-Build | `AlteryxSpatialPluginsGui.PolyBuild.PolyBuild` | Yes | No | `partial` |
| 88 | Spatial | Poly-Split | `AlteryxSpatialPluginsGui.PolySplit.PolySplit` | Yes | No | `partial` |
| 89 | Spatial | Smooth | `AlteryxSpatialPluginsGui.Smooth.Smooth` | Yes | No | `partial` |
| 90 | Spatial | Spatial Info | `AlteryxSpatialPluginsGui.SpatialInfo.SpatialInfo` | Yes | No | `partial` |
| 91 | Spatial | Spatial Match | `AlteryxSpatialPluginsGui.SpatialMatch.SpatialMatch` | Yes | No | `partial` |
| 92 | Spatial | Spatial Process | `AlteryxSpatialPluginsGui.SpatialProcess.SpatialProcess` | Yes | No | `partial` |
| 93 | Spatial | Trade Area | `AlteryxSpatialPluginsGui.TradeArea.TradeArea` | Yes | No | `partial` |
| 94 | Transform | Arrange | `AlteryxBasePluginsGui.Arrange.Arrange` | Yes | Yes | `full` |
| 95 | Transform | Count Records | `CountRecords.yxmc` | Yes | Yes | `full` |
| 96 | Transform | Cross Tab | `AlteryxBasePluginsGui.CrossTab.CrossTab` | Yes | Yes | `full` |
| 97 | Transform | Make Columns | `AlteryxBasePluginsGui.MakeColumns.MakeColumns` | Yes | Yes | `full` |
| 98 | Transform | Running Total | `AlteryxBasePluginsGui.RunningTotal.RunningTotal` | Yes | Yes | `full` |
| 99 | Transform | Summarize | `AlteryxSpatialPluginsGui.Summarize.Summarize` | Yes | Yes | `full` |
| 100 | Transform | Transpose | `AlteryxBasePluginsGui.Transpose.Transpose` | Yes | Yes | `full` |
