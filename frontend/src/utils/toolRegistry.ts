import { NodeDTO } from '../types/workflow';

/**
 * Authoritative deterministic tool registry mapping derived from docs/tool-support-matrix.md
 * and backend tool catalog definitions.
 */
export const TOOL_REGISTRY_XML_NAMES: Record<string, string> = {
  // In/Out
  dbfileinput: 'AlteryxBasePluginsGui.DbFileInput.DbFileInput',
  dbfileoutput: 'AlteryxBasePluginsGui.DbFileOutput.DbFileOutput',
  browse: 'AlteryxBasePluginsGui.BrowseV2.BrowseV2',
  browsev2: 'AlteryxBasePluginsGui.BrowseV2.BrowseV2',
  textinput: 'AlteryxBasePluginsGui.TextInput.TextInput',
  directory: 'AlteryxBasePluginsGui.Directory.Directory',
  datetimenow: 'DateTimeNow',

  // Preparation
  autofield: 'AlteryxBasePluginsGui.AutoField.AutoField',
  datacleansepro: 'DataCleansePro',
  cleanse: 'Cleanse.yxmc',
  datacleansing: 'Cleanse.yxmc',
  filter: 'AlteryxBasePluginsGui.Filter.Filter',
  formula: 'AlteryxBasePluginsGui.Formula.Formula',
  generaterows: 'AlteryxBasePluginsGui.GenerateRows.GenerateRows',
  multifieldformula: 'AlteryxBasePluginsGui.MultiFieldFormula.MultiFieldFormula',
  multirowformula: 'AlteryxBasePluginsGui.MultiRowFormula.MultiRowFormula',
  recordid: 'AlteryxBasePluginsGui.RecordID.RecordID',
  sample: 'AlteryxBasePluginsGui.Sample.Sample',
  select: 'AlteryxBasePluginsGui.AlteryxSelect.AlteryxSelect',
  alteryxselect: 'AlteryxBasePluginsGui.AlteryxSelect.AlteryxSelect',
  selectrecords: 'AlteryxBasePluginsGui.SelectRecords.SelectRecords',
  sort: 'AlteryxBasePluginsGui.Sort.Sort',
  tile: 'AlteryxBasePluginsGui.Tile.Tile',
  unique: 'AlteryxBasePluginsGui.Unique.Unique',
  rank: 'AlteryxBasePluginsGui.Rank.Rank',
  randomsamplesize: 'RandomSampleSize.yxmc',
  createsamples: 'CreateSamples.yxmc',
  multifieldbinning: 'MultiFieldBinning.yxmc',

  // Join
  appendfields: 'AlteryxBasePluginsGui.AppendFields.AppendFields',
  findreplace: 'AlteryxBasePluginsGui.FindReplace.FindReplace',
  fuzzymatch: 'AlteryxBasePluginsGui.FuzzyMatch.FuzzyMatch',
  join: 'AlteryxBasePluginsGui.Join.Join',
  joinmultiple: 'AlteryxBasePluginsGui.JoinMultiple.JoinMultiple',
  makegroup: 'AlteryxBasePluginsGui.MakeGroup.MakeGroup',
  union: 'AlteryxBasePluginsGui.Union.Union',

  // Parse
  datetime: 'AlteryxBasePluginsGui.DateTime.DateTime',
  regex: 'AlteryxBasePluginsGui.RegEx.RegEx',
  texttocolumns: 'AlteryxBasePluginsGui.TextToColumns.TextToColumns',
  xmlparse: 'AlteryxBasePluginsGui.XMLParse.XMLParse',

  // Transform
  arrange: 'AlteryxBasePluginsGui.Arrange.Arrange',
  countrecords: 'CountRecords.yxmc',
  crosstab: 'AlteryxBasePluginsGui.CrossTab.CrossTab',
  makecolumns: 'AlteryxBasePluginsGui.MakeColumns.MakeColumns',
  runningtotal: 'AlteryxBasePluginsGui.RunningTotal.RunningTotal',
  summarize: 'AlteryxSpatialPluginsGui.Summarize.Summarize',
  transpose: 'AlteryxBasePluginsGui.Transpose.Transpose',

  // Developer
  blockuntildone: 'AlteryxBasePluginsGui.BlockUntilDone.BlockUntilDone',
  detour: 'AlteryxBasePluginsGui.Detour.Detour',
  detourend: 'AlteryxBasePluginsGui.DetourEnd.DetourEnd',
  download: 'AlteryxConnectorGui.Download.Download',
  dynamicinput: 'AlteryxBasePluginsGui.DynamicInput.DynamicInput',
  dynamicrename: 'AlteryxBasePluginsGui.DynamicRename.DynamicRename',
  dynamicreplace: 'AlteryxBasePluginsGui.DynamicReplace.DynamicReplace',
  dynamicselect: 'AlteryxBasePluginsGui.DynamicSelect.DynamicSelect',
  fieldinfo: 'AlteryxBasePluginsGui.FieldInfo.FieldInfo',
  jsonbuild: 'AlteryxBasePluginsGui.JSONBuild.JSONBuild',
  jsonparse: 'AlteryxBasePluginsGui.JSONParse.JSONParse',
  message: 'AlteryxBasePluginsGui.Message.Message',
  python: 'Python',
  r: 'AlteryxRPluginGui.R.R',
  runcommand: 'AlteryxBasePluginsGui.RunCommand.RunCommand',

  // Documentation
  textbox: 'AlteryxGuiToolkit.TextBox.TextBox',
  comment: 'AlteryxGuiToolkit.TextBox.TextBox',
  toolcontainer: 'AlteryxGuiToolkit.ToolContainer.ToolContainer',

  // Reporting
  email: 'AlteryxReportPluginsGui.Email.Email',
  layout: 'AlteryxReportPluginsGui.Layout.Layout',
  render: 'AlteryxReportPluginsGui.Render.Render',
  reportfooter: 'ReportFooter.yxmc',
  reportheader: 'ReportHeader.yxmc',
  reportmap: 'AlteryxReportPluginsGui.ReportMap.ReportMap',
  reporttext: 'AlteryxReportPluginsGui.ReportText.ReportText',
  table: 'AlteryxReportPluginsGui.Table.Table',
  interactivechart: 'AlteryxReportPluginsGui.InteractiveChart.InteractiveChart',
  image: 'AlteryxReportPluginsGui.Image.Image',

  // Spatial
  buffer: 'AlteryxSpatialPluginsGui.Buffer.Buffer',
  createpoints: 'AlteryxSpatialPluginsGui.CreatePoints.CreatePoints',
  distance: 'AlteryxSpatialPluginsGui.Distance.Distance',
  findnearest: 'AlteryxSpatialPluginsGui.FindNearest.FindNearest',
  generalize: 'AlteryxSpatialPluginsGui.Generalize.Generalize',
  heatmap: 'HeatMap.yxmc',
  makegrid: 'AlteryxSpatialPluginsGui.MakeGrid.MakeGrid',
  polybuild: 'AlteryxSpatialPluginsGui.PolyBuild.PolyBuild',
  polysplit: 'AlteryxSpatialPluginsGui.PolySplit.PolySplit',
  smooth: 'AlteryxSpatialPluginsGui.Smooth.Smooth',
  spatialinfo: 'AlteryxSpatialPluginsGui.SpatialInfo.SpatialInfo',
  spatialmatch: 'AlteryxSpatialPluginsGui.SpatialMatch.SpatialMatch',
  spatialprocess: 'AlteryxSpatialPluginsGui.SpatialProcess.SpatialProcess',
  tradearea: 'AlteryxSpatialPluginsGui.TradeArea.TradeArea',

  // In-Database
  lockininput: 'LockInGui.LockInInput.LockInInput',
  lockinstreamin: 'LockInGui.LockInStreamIn.LockInStreamIn',
  lockinstreamout: 'LockInGui.LockInStreamOut.LockInStreamOut',
  lockinfilter: 'LockInGui.LockInFilter.LockInFilter',
  lockinformula: 'LockInGui.LockInFormula.LockInFormula',
  lockinjoin: 'LockInGui.LockInJoin.LockInJoin',
  lockinselect: 'LockInGui.LockInSelect.LockInSelect',

  // Connectors
  amazons3download: 'AmazonS3Download.yxmc',
  amazons3upload: 'AmazonS3Upload.yxmc',
  sharepointfilesinput: 'SharePointFilesInput.yxmc',
};

/**
 * Resolves the XML Tool Name deterministically:
 * 1. From node.xml_tool_name if already resolved and valid
 * 2. By matching node.plugin against authoritative tool registry
 * 3. By matching normalized node.tool_type against authoritative tool registry
 * 4. Fallback: 'Not available in tool registry'
 */
export function resolveXmlToolName(node: NodeDTO | null | undefined): string {
  if (!node) {
    return 'Not available in tool registry';
  }

  // 1. Direct DTO attribute if populated
  if (node.xml_tool_name && node.xml_tool_name.trim().length > 0) {
    return node.xml_tool_name.trim();
  }

  // 2. Direct Plugin string if already canonical XML identifier
  if (node.plugin && node.plugin.includes('.')) {
    const normPlugin = node.plugin.toLowerCase().replace(/[^a-z0-9]/g, '');
    if (TOOL_REGISTRY_XML_NAMES[normPlugin]) {
      return TOOL_REGISTRY_XML_NAMES[normPlugin];
    }
    return node.plugin;
  }

  // 3. Normalized tool_type lookup
  const normType = (node.tool_type || '').toLowerCase().replace(/[^a-z0-9]/g, '');
  if (normType && TOOL_REGISTRY_XML_NAMES[normType]) {
    return TOOL_REGISTRY_XML_NAMES[normType];
  }

  // 4. Fallback convention
  return 'Not available in tool registry';
}
