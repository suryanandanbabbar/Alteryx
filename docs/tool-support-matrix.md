# AWA Top-100 Alteryx Tool Support Matrix

This matrix outlines the analysis, parsing, Python code generation, and business summary for the **top 100 Alteryx tools**.

| # | Category | Tool Name | XML Tool Name | Business Summary | Config Parsing | Python Translation | Support Level |
|---|---|---|---|---|---|---|---|
| 1 | In/Out | Input Data | `AlteryxBasePluginsGui.DbFileInput.DbFileInput` | Reads records from supported files, databases, or cloud stores into a workflow. | Yes | Yes | `full` |
| 2 | In/Out | Output Data | `AlteryxBasePluginsGui.DbFileOutput.DbFileOutput` | Writes workflow data to files, relational tables, or cloud destinations. | Yes | Yes | `full` |
| 3 | In/Out | Browse | `AlteryxBasePluginsGui.BrowseV2.BrowseV2` | Displays data profile, schema, and record details during workflow execution without altering data. | Yes | No | `pass_through` |
| 4 | In/Out | Text Input | `AlteryxBasePluginsGui.TextInput.TextInput` | Embeds hard-coded tabular text data directly into the workflow. | Yes | Yes | `full` |
| 5 | In/Out | Directory | `AlteryxBasePluginsGui.Directory.Directory` | Returns a list of files from a specified directory with file metadata. | Yes | No | `partial` |
| 6 | In/Out | Date Time Now | `DateTimeNow` | Returns the current date and time formatted according to user specifications. | Yes | Yes | `full` |
| 7 | Preparation | Auto Field | `AlteryxBasePluginsGui.AutoField.AutoField` | Automatically optimizes field data types to the smallest possible type based on incoming data values. | Yes | Yes | `full` |
| 8 | Preparation | Data Cleanse Pro | `DataCleansePro` | Enhanced data cleansing tool with advanced text replacement and normalization rules. | Yes | No | `partial` |
| 9 | Preparation | Data Cleansing | `Cleanse.yxmc` | Cleanses fields by removing null values, leading/trailing whitespace, and modifying text casing. | Yes | Yes | `full` |
| 10 | Preparation | Filter | `AlteryxBasePluginsGui.Filter.Filter` | Splits incoming data streams into True and False branches based on a boolean expression. | Yes | Yes | `full` |
| 11 | Preparation | Formula | `AlteryxBasePluginsGui.Formula.Formula` | Applies mathematical, string, datetime, and logical expressions to create or update columns. | Yes | Yes | `full` |
| 12 | Preparation | Generate Rows | `AlteryxBasePluginsGui.GenerateRows.GenerateRows` | Generates new rows of data using initialization, loop, and termination conditions. | Yes | Yes | `full` |
| 13 | Preparation | Multi-Field Formula | `AlteryxBasePluginsGui.MultiFieldFormula.MultiFieldFormula` | Applies a single formula across multiple selected fields simultaneously. | Yes | Yes | `full` |
| 14 | Preparation | Multi-Row Formula | `AlteryxBasePluginsGui.MultiRowFormula.MultiRowFormula` | References preceding or subsequent rows to calculate lag, lead, and running values. | Yes | Yes | `full` |
| 15 | Preparation | Record ID | `AlteryxBasePluginsGui.RecordID.RecordID` | Appends a sequential numeric identifier column to incoming records. | Yes | Yes | `full` |
| 16 | Preparation | Sample | `AlteryxBasePluginsGui.Sample.Sample` | Extracts first N, last N, or percentage subsets of records. | Yes | Yes | `full` |
| 17 | Preparation | Select | `AlteryxBasePluginsGui.AlteryxSelect.AlteryxSelect` | Selects, excludes, renames, and typecasts columns in the data stream. | Yes | Yes | `full` |
| 18 | Preparation | Select Records | `AlteryxBasePluginsGui.SelectRecords.SelectRecords` | Filters data stream by specific record row numbers or ranges. | Yes | Yes | `full` |
| 19 | Preparation | Sort | `AlteryxBasePluginsGui.Sort.Sort` | Sorts records ascending or descending based on one or more key columns. | Yes | Yes | `full` |
| 20 | Preparation | Tile | `AlteryxBasePluginsGui.Tile.Tile` | Assigns a tile number based on equal records, equal intervals, or unique values. | Yes | No | `partial` |
| 21 | Preparation | Unique | `AlteryxBasePluginsGui.Unique.Unique` | Separates unique records from duplicate records based on specified key columns. | Yes | Yes | `full` |
| 22 | Preparation | Rank | `AlteryxBasePluginsGui.Rank.Rank` | Calculates dense or standard rank positions for numeric or ordinal columns. | Yes | Yes | `full` |
| 23 | Preparation | Random % Sample | `RandomSampleSize.yxmc` | Draws an unbiased pseudo-random percentage sample of rows from the data stream. | Yes | Yes | `full` |
| 24 | Preparation | Create Samples | `CreateSamples.yxmc` | Partitions data stream into Estimation, Validation, and Holdout samples for modeling. | Yes | Yes | `full` |
| 25 | Preparation | Multi-Field Binning | `MultiFieldBinning.yxmc` | Groups continuous numerical columns into discrete bins or quantiles. | Yes | No | `partial` |
| 26 | Join | Append Fields | `AlteryxBasePluginsGui.AppendFields.AppendFields` | Performs a Cartesian (cross) product between target records and source records. | Yes | Yes | `full` |
| 27 | Join | Find Replace | `AlteryxBasePluginsGui.FindReplace.FindReplace` | Searches for substrings or exact matches in a target table and replaces or appends values from a reference table. | Yes | Yes | `full` |
| 28 | Join | Fuzzy Match | `AlteryxBasePluginsGui.FuzzyMatch.FuzzyMatch` | Identifies non-exact duplicate and matching records using phonetic and edit-distance matching algorithms. | Yes | No | `partial` |
| 29 | Join | Join | `AlteryxBasePluginsGui.Join.Join` | Combines two data streams based on common key columns or record position, outputting matched, left-unmatched, and right-unmatched streams. | Yes | Yes | `full` |
| 30 | Join | Join Multiple | `AlteryxBasePluginsGui.JoinMultiple.JoinMultiple` | Performs an n-way relational join across three or more data inputs simultaneously. | Yes | Yes | `full` |
| 31 | Join | Make Group | `AlteryxBasePluginsGui.MakeGroup.MakeGroup` | Creates connected component groups based on pair-wise record relationships. | Yes | No | `partial` |
| 32 | Join | Union | `AlteryxBasePluginsGui.Union.Union` | Concatenates multiple data streams vertically by column name or positional order. | Yes | Yes | `full` |
| 33 | Parse | DateTime | `AlteryxBasePluginsGui.DateTime.DateTime` | Converts datetime data between standardized string representations and native date/time formats. | Yes | Yes | `full` |
| 34 | Parse | RegEx | `AlteryxBasePluginsGui.RegEx.RegEx` | Parses, matches, replaces, or tokenizes string columns using regular expressions. | Yes | Yes | `full` |
| 35 | Parse | Text To Columns | `AlteryxBasePluginsGui.TextToColumns.TextToColumns` | Splits a single text column into multiple columns or rows using specified delimiters. | Yes | Yes | `full` |
| 36 | Parse | XML Parse | `AlteryxBasePluginsGui.XMLParse.XMLParse` | Extracts elements, attributes, and text values from XML formatted string columns. | Yes | No | `partial` |
| 37 | Transform | Arrange | `AlteryxBasePluginsGui.Arrange.Arrange` | Manually transposes, groups, and arranges column data into standardized output tables. | Yes | Yes | `full` |
| 38 | Transform | Count Records | `CountRecords.yxmc` | Returns a single row with the exact count of records passing through the stream. | Yes | Yes | `full` |
| 39 | Transform | Cross Tab | `AlteryxBasePluginsGui.CrossTab.CrossTab` | Pivots vertical tabular data horizontally into a cross-tabulated matrix. | Yes | Yes | `full` |
| 40 | Transform | Make Columns | `AlteryxBasePluginsGui.MakeColumns.MakeColumns` | Arranges rows into multiple columns arranged either horizontally or vertically. | Yes | Yes | `full` |
| 41 | Transform | Running Total | `AlteryxBasePluginsGui.RunningTotal.RunningTotal` | Calculates cumulative running totals over rows, optionally segmented by grouping fields. | Yes | Yes | `full` |
| 42 | Transform | Summarize | `AlteryxSpatialPluginsGui.Summarize.Summarize` | Aggregates and summarizes data (Group By, Sum, Count, Min, Max, Avg, First, Last, String Concat). | Yes | Yes | `full` |
| 43 | Transform | Transpose | `AlteryxBasePluginsGui.Transpose.Transpose` | Pivots horizontal columns vertically into Name/Value pairs preserving specified Key columns. | Yes | Yes | `full` |
| 44 | Developer | Block Until Done | `AlteryxBasePluginsGui.BlockUntilDone.BlockUntilDone` | Controls execution sequence by holding downstream branches until preceding branches complete. | Yes | No | `pass_through` |
| 45 | Developer | Detour | `AlteryxBasePluginsGui.Detour.Detour` | Bypasses downstream workflow logic by routing data to either the left or right branch. | Yes | No | `partial` |
| 46 | Developer | Detour End | `AlteryxBasePluginsGui.DetourEnd.DetourEnd` | Merges separated branches from a preceding Detour tool back into a single unified stream. | Yes | No | `pass_through` |
| 47 | Developer | Download | `AlteryxConnectorGui.Download.Download` | Retrieves data or files from web APIs and URLs via HTTP GET/POST requests. | Yes | No | `external_execution` |
| 48 | Developer | Dynamic Input | `AlteryxBasePluginsGui.DynamicInput.DynamicInput` | Dynamically alters queries, database paths, or input files based on incoming record values. | Yes | No | `partial` |
| 49 | Developer | Dynamic Rename | `AlteryxBasePluginsGui.DynamicRename.DynamicRename` | Dynamically renames columns using formulas, metadata prefixes/suffixes, or secondary lookup tables. | Yes | Yes | `full` |
| 50 | Developer | Dynamic Replace | `AlteryxBasePluginsGui.DynamicReplace.DynamicReplace` | Dynamically updates field values based on conditions defined in a secondary expression table. | Yes | No | `partial` |
| 51 | Developer | Dynamic Select | `AlteryxBasePluginsGui.DynamicSelect.DynamicSelect` | Selects or filters columns dynamically using boolean formulas or data type conditions. | Yes | Yes | `full` |
| 52 | Developer | Field Info | `AlteryxBasePluginsGui.FieldInfo.FieldInfo` | Extracts column metadata (names, types, sizes, descriptions) into a tabular output stream. | Yes | Yes | `full` |
| 53 | Developer | JSON Build | `AlteryxBasePluginsGui.JSONBuild.JSONBuild` | Constructs hierarchical JSON text strings from key/value pair records. | Yes | Yes | `full` |
| 54 | Developer | JSON Parse | `AlteryxBasePluginsGui.JSONParse.JSONParse` | Parses structured JSON strings into discrete key/value columns and arrays. | Yes | Yes | `full` |
| 55 | Developer | Message | `AlteryxBasePluginsGui.Message.Message` | Emits informational messages, warnings, or errors to the execution log when conditions are met. | Yes | No | `pass_through` |
| 56 | Developer | Python | `Python` | Executes arbitrary embedded Python code within an interactive Jupyter notebook container. | Yes | No | `external_execution` |
| 57 | Developer | R | `AlteryxRPluginGui.R.R` | Executes embedded R statistical scripting code on incoming data streams. | Yes | No | `external_execution` |
| 58 | Developer | Run Command | `AlteryxBasePluginsGui.RunCommand.RunCommand` | Executes external operating system command-line programs, batch files, or executables. | Yes | No | `external_execution` |
| 59 | Documentation | Comment | `AlteryxGuiToolkit.TextBox.TextBox` | Places free-form documentation, markdown notes, and visual annotation boxes on the workflow canvas. | Yes | No | `documentation_only` |
| 60 | Documentation | Tool Container | `AlteryxGuiToolkit.ToolContainer.ToolContainer` | Organizes and visually isolates a group of workflow tools into a collapsable, toggleable boundary box. | Yes | No | `documentation_only` |
| 61 | Reporting | Email | `AlteryxReportPluginsGui.Email.Email` | Sends emails with attached report snippets, tables, or output files via SMTP. | Yes | No | `external_execution` |
| 62 | Reporting | Layout | `AlteryxReportPluginsGui.Layout.Layout` | Combines multiple reporting elements (charts, tables, text) into a formatted horizontal/vertical layout snippet. | Yes | No | `documentation_only` |
| 63 | Reporting | Render | `AlteryxReportPluginsGui.Render.Render` | Transforms reporting snippets into final document formats (PDF, DOCX, HTML, PPTX, PNG). | Yes | No | `documentation_only` |
| 64 | Reporting | Report Footer | `ReportFooter.yxmc` | Appends standardized footer snippets, copyright text, and page numbering to report layouts. | Yes | No | `documentation_only` |
| 65 | Reporting | Report Header | `ReportHeader.yxmc` | Appends standardized header snippets, title, and organization branding logos to reports. | Yes | No | `documentation_only` |
| 66 | Reporting | Report Map | `AlteryxReportPluginsGui.ReportMap.ReportMap` | Renders spatial polygons, points, lines, and heatmaps into cartographic report image snippets. | Yes | No | `documentation_only` |
| 67 | Reporting | Report Text | `AlteryxReportPluginsGui.ReportText.ReportText` | Generates rich formatted text snippets with dynamic field replacement values for inclusion in reports. | Yes | No | `documentation_only` |
| 68 | Reporting | Table | `AlteryxReportPluginsGui.Table.Table` | Formats tabular datasets into styled report presentation table snippets with custom rules. | Yes | No | `documentation_only` |
| 69 | Reporting | Interactive Chart | `AlteryxReportPluginsGui.InteractiveChart.InteractiveChart` | Generates interactive Plotly/D3 based chart visualizations from workflow records. | Yes | No | `documentation_only` |
| 70 | Reporting | Image | `AlteryxReportPluginsGui.Image.Image` | Embeds raster or vector graphics and images into reporting layouts. | Yes | No | `documentation_only` |
| 71 | Spatial | Buffer | `AlteryxSpatialPluginsGui.Buffer.Buffer` | Expands or contracts the boundary of any polygon or polyline spatial object by a specified radius. | Yes | No | `partial` |
| 72 | Spatial | Create Points | `AlteryxSpatialPluginsGui.CreatePoints.CreatePoints` | Creates spatial point objects from numerical latitude and longitude coordinate columns. | Yes | No | `partial` |
| 73 | Spatial | Distance | `AlteryxSpatialPluginsGui.Distance.Distance` | Calculates point-to-point, point-to-edge, or driving distances between spatial objects. | Yes | No | `partial` |
| 74 | Spatial | Find Nearest | `AlteryxSpatialPluginsGui.FindNearest.FindNearest` | Identifies the nearest spatial objects in a universe dataset relative to a target dataset. | Yes | No | `partial` |
| 75 | Spatial | Generalize | `AlteryxSpatialPluginsGui.Generalize.Generalize` | Simplifies spatial polylines and polygons by reducing vertex count within a specified tolerance. | Yes | No | `partial` |
| 76 | Spatial | Heat Map | `HeatMap.yxmc` | Generates continuous density heat map polygons based on point clustering and intensity weights. | Yes | No | `partial` |
| 77 | Spatial | Make Grid | `AlteryxSpatialPluginsGui.MakeGrid.MakeGrid` | Creates a regular hexagonal or rectangular spatial polygon grid overlay across a bounding area. | Yes | No | `partial` |
| 78 | Spatial | Poly-Build | `AlteryxSpatialPluginsGui.PolyBuild.PolyBuild` | Transforms an ordered sequence of spatial points into convex hulls, polygons, or polylines. | Yes | No | `partial` |
| 79 | Spatial | Poly-Split | `AlteryxSpatialPluginsGui.PolySplit.PolySplit` | Deconstructs polygon and polyline spatial objects into component points, segments, or rings. | Yes | No | `partial` |
| 80 | Spatial | Smooth | `AlteryxSpatialPluginsGui.Smooth.Smooth` | Rounds the sharp corners of polygon and polyline spatial objects using spline curve algorithms. | Yes | No | `partial` |
| 81 | Spatial | Spatial Info | `AlteryxSpatialPluginsGui.SpatialInfo.SpatialInfo` | Extracts spatial metadata (area, length, centroid coordinates, bounding box) from spatial objects. | Yes | No | `partial` |
| 82 | Spatial | Spatial Match | `AlteryxSpatialPluginsGui.SpatialMatch.SpatialMatch` | Establishes spatial relationships (intersects, contains, touches, overlaps) between two spatial datasets. | Yes | No | `partial` |
| 83 | Spatial | Spatial Process | `AlteryxSpatialPluginsGui.SpatialProcess.SpatialProcess` | Performs geometric boolean operations (combine, cut, intersect, symmetric difference) between spatial objects. | Yes | No | `partial` |
| 84 | Spatial | Trade Area | `AlteryxSpatialPluginsGui.TradeArea.TradeArea` | Creates circular or drive-time catchment areas around spatial point locations. | Yes | No | `partial` |
| 85 | In-Database | Connect In-DB | `LockInGui.LockInInput.LockInInput` | Establishes an in-database query connection to a relational or cloud warehouse database. | Yes | No | `external_execution` |
| 86 | In-Database | Data Stream In | `LockInGui.LockInStreamIn.LockInStreamIn` | Streams in-memory workflow records into a temporary table inside the connected database engine. | Yes | No | `external_execution` |
| 87 | In-Database | Data Stream Out | `LockInGui.LockInStreamOut.LockInStreamOut` | Executes the accumulated In-DB query pipeline and streams results back into in-memory workflow data. | Yes | No | `external_execution` |
| 88 | In-Database | Filter In-DB | `LockInGui.LockInFilter.LockInFilter` | Applies SQL WHERE filter clauses directly inside the database engine query plan. | Yes | No | `external_execution` |
| 89 | In-Database | Formula In-DB | `LockInGui.LockInFormula.LockInFormula` | Applies SQL expressions and column transformations natively within the database query. | Yes | No | `external_execution` |
| 90 | In-Database | Join In-DB | `LockInGui.LockInJoin.LockInJoin` | Executes native SQL relational joins between two In-DB database tables or subqueries. | Yes | No | `external_execution` |
| 91 | In-Database | Select In-DB | `LockInGui.LockInSelect.LockInSelect` | Selects, renames, and typecasts columns inside the database execution plan. | Yes | No | `external_execution` |
| 92 | Connectors | Amazon S3 Download | `AmazonS3Download.yxmc` | Retrieves and reads files stored in Amazon Web Services Simple Storage Service (S3) buckets. | Yes | No | `external_execution` |
| 93 | Connectors | Amazon S3 Upload | `AmazonS3Upload.yxmc` | Uploads workflow records and data files to an Amazon S3 cloud bucket destination. | Yes | No | `external_execution` |
| 94 | Connectors | SharePoint Files Input | `SharePointFilesInput.yxmc` | Downloads and reads Excel, CSV, or XML data files from Microsoft SharePoint document libraries. | Yes | No | `external_execution` |
| 95 | Connectors | SharePoint Files Output | `SharePointFilesOutput.yxmc` | Writes and uploads dataset files to a target Microsoft SharePoint document library. | Yes | No | `external_execution` |
| 96 | Connectors | Salesforce Input | `SalesforceInput.yxmc` | Queries and extracts tables and object records from Salesforce CRM via SOQL API. | Yes | No | `external_execution` |
| 97 | Connectors | Salesforce Output (New) | `SalesforceOutput.yxmc` | Inserts, updates, or upserts workflow records into Salesforce database objects via API. | Yes | No | `external_execution` |
| 98 | Connectors | Tableau Output | `TableauOutput.yxmc` | Publishes data extracts (.hyper) directly to Tableau Server or Tableau Cloud sites. | Yes | No | `external_execution` |
| 99 | Connectors | MongoDB Input | `AlteryxConnectorGui.MongoInput.MongoInput` | Queries documents from MongoDB NoSQL database collections and flattens into tabular records. | Yes | No | `external_execution` |
| 100 | Connectors | MongoDB Output | `AlteryxConnectorGui.MongoOutput.MongoOutput` | Writes workflow data streams as JSON documents into MongoDB collections. | Yes | No | `external_execution` |
