/**
 * Pure deterministic generic XML formatter for presentation layer.
 * Prettifies XML strings into clean, indented code blocks while strictly preserving
 * all tags, attributes, text values, CDATA, comments, and structure.
 */
export function formatXmlForDisplay(xml: string, indentSpaces: number = 4): string {
  if (!xml || typeof xml !== 'string') return '';
  const trimmed = xml.trim();
  if (!trimmed || trimmed === 'Source Node unavailable') return trimmed;

  const indentStr = ' '.repeat(indentSpaces);
  let depth = 0;

  try {
    const tokenRegex = /(<!\[CDATA\[[\s\S]*?\]\]>|<!--[\s\S]*?-->|<\/?[a-zA-Z0-9_:-]+(?:(?:\s+[a-zA-Z0-9_:-]+(?:\s*=\s*(?:"[^"]*"|'[^']*'|[^\s>]+))?)*)\s*\/?>|[^<]+)/g;
    const tokens = trimmed.match(tokenRegex);
    if (!tokens || tokens.length === 0) return trimmed;

    const lines: string[] = [];

    for (let i = 0; i < tokens.length; i++) {
      const token = tokens[i];
      const tokenTrimmed = token.trim();
      if (!tokenTrimmed) continue;

      if (tokenTrimmed.startsWith('<!--') || tokenTrimmed.startsWith('<![CDATA[')) {
        lines.push(indentStr.repeat(depth) + tokenTrimmed);
      } else if (tokenTrimmed.startsWith('</')) {
        depth = Math.max(0, depth - 1);
        lines.push(indentStr.repeat(depth) + tokenTrimmed);
      } else if (tokenTrimmed.startsWith('<') && (tokenTrimmed.endsWith('/>') || tokenTrimmed.endsWith('/ >'))) {
        lines.push(indentStr.repeat(depth) + tokenTrimmed);
      } else if (tokenTrimmed.startsWith('<')) {
        const nextToken = tokens[i + 1]?.trim();
        const nextNextToken = tokens[i + 2]?.trim();
        const tagNameMatch = tokenTrimmed.match(/^<([a-zA-Z0-9_:-]+)/);
        const tagName = tagNameMatch ? tagNameMatch[1] : '';

        if (
          tagName &&
          nextToken &&
          !nextToken.startsWith('<') &&
          nextNextToken &&
          nextNextToken === `</${tagName}>`
        ) {
          lines.push(indentStr.repeat(depth) + `${tokenTrimmed}${nextToken}${nextNextToken}`);
          i += 2;
        } else {
          lines.push(indentStr.repeat(depth) + tokenTrimmed);
          depth++;
        }
      } else {
        lines.push(indentStr.repeat(depth) + tokenTrimmed);
      }
    }

    return lines.join('\n') || trimmed;
  } catch {
    return trimmed;
  }
}
