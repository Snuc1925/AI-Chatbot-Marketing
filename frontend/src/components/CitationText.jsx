import React, { useState, useRef } from 'react';
import { Database, Copy, Check, Clock } from 'lucide-react';

/**
 * Formats inline Markdown (bold **...**, italic *...*, code `...`) and newlines into React elements.
 */
function renderFormattedText(rawText, keyPrefix = '') {
  if (!rawText) return null;

  const lines = rawText.split('\n');
  return lines.map((line, lineIdx) => {
    const parts = [];
    const inlineRegex = /(\*\*[\s\S]+?\*\*|\*[^*]+?\*|`[^`]+?`)/g;
    let lastIdx = 0;
    let match;

    while ((match = inlineRegex.exec(line)) !== null) {
      const full = match[0];
      const matchIdx = match.index;

      if (matchIdx > lastIdx) {
        parts.push(line.substring(lastIdx, matchIdx));
      }

      if (full.startsWith('**') && full.endsWith('**')) {
        parts.push(
          <strong key={`b-${keyPrefix}-${lineIdx}-${matchIdx}`} style={{ fontWeight: 600 }}>
            {full.slice(2, -2)}
          </strong>
        );
      } else if (full.startsWith('*') && full.endsWith('*')) {
        parts.push(
          <em key={`i-${keyPrefix}-${lineIdx}-${matchIdx}`}>
            {full.slice(1, -1)}
          </em>
        );
      } else if (full.startsWith('`') && full.endsWith('`')) {
        parts.push(
          <code
            key={`c-${keyPrefix}-${lineIdx}-${matchIdx}`}
            style={{ background: '#f1f5f9', padding: '2px 5px', borderRadius: '4px', fontSize: '0.9em', color: '#0284c7' }}
          >
            {full.slice(1, -1)}
          </code>
        );
      }

      lastIdx = matchIdx + full.length;
    }

    if (lastIdx < line.length) {
      parts.push(line.substring(lastIdx));
    }

    return (
      <React.Fragment key={`line-${keyPrefix}-${lineIdx}`}>
        {parts}
        {lineIdx < lines.length - 1 && <br />}
      </React.Fragment>
    );
  });
}

export const CitationText = ({ text, citations = [] }) => {
  const [activeOccurrenceKey, setActiveOccurrenceKey] = useState(null);
  const [copiedId, setCopiedId] = useState(null);
  const closeTimeoutRef = useRef(null);

  if (!text) return null;

  // Map citations by ID for fast lookup
  const citationMap = React.useMemo(() => {
    const map = {};
    if (Array.isArray(citations)) {
      citations.forEach((c) => {
        if (c && c.id) {
          map[c.id] = c;
        }
      });
    }
    return map;
  }, [citations]);

  const handleMouseEnter = (uniqueKey) => {
    if (closeTimeoutRef.current) {
      clearTimeout(closeTimeoutRef.current);
    }
    setActiveOccurrenceKey(uniqueKey);
  };

  const handleMouseLeave = () => {
    closeTimeoutRef.current = setTimeout(() => {
      setActiveOccurrenceKey(null);
    }, 250);
  };

  const handleCopySql = (sql, id, e) => {
    e.stopPropagation();
    navigator.clipboard.writeText(sql);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  // Regex to match <cite id="sql_1">content</cite>
  const citeRegex = /<cite\s+id=["']([^"']+)["']>([\s\S]*?)<\/cite>/gi;
  const elements = [];
  let lastIndex = 0;
  let match;

  while ((match = citeRegex.exec(text)) !== null) {
    const [fullMatch, citeId, innerContent] = match;
    const startIndex = match.index;
    const uniqueKey = `cite-${citeId}-${startIndex}`;

    // Push text before this tag formatted with Markdown
    if (startIndex > lastIndex) {
      elements.push(
        <React.Fragment key={`text-${lastIndex}`}>
          {renderFormattedText(text.substring(lastIndex, startIndex), `pre-${lastIndex}`)}
        </React.Fragment>
      );
    }

    const citationData = citationMap[citeId];
    const isHovered = activeOccurrenceKey === uniqueKey;

    if (citationData) {
      elements.push(
        <span
          key={uniqueKey}
          className="citation-wrapper"
          onMouseEnter={() => handleMouseEnter(uniqueKey)}
          onMouseLeave={handleMouseLeave}
        >
          <span className="citation-highlight">
            <Database size={11} className="citation-icon" />
            {innerContent}
          </span>

          {isHovered && (
            <div
              className="citation-popover"
              onMouseEnter={() => handleMouseEnter(uniqueKey)}
              onMouseLeave={handleMouseLeave}
            >
              <div className="citation-popover-header">
                <div className="citation-popover-title">
                  <Database size={13} color="#38bdf8" />
                  <span>{citationData.title || 'Truy vấn ClickHouse'}</span>
                </div>
                {citationData.execution_time_ms !== null && citationData.execution_time_ms !== undefined && (
                  <span className="citation-time-badge">
                    <Clock size={10} />
                    {citationData.execution_time_ms}ms
                  </span>
                )}
              </div>

              <div className="citation-sql-box">
                <div className="citation-sql-header">
                  <span>SQL EXECUTION</span>
                  <button
                    className="citation-copy-btn"
                    onClick={(e) => handleCopySql(citationData.query, citeId, e)}
                    title="Sao chép câu SQL"
                  >
                    {copiedId === citeId ? (
                      <>
                        <Check size={11} color="#22c55e" /> Đã chép
                      </>
                    ) : (
                      <>
                        <Copy size={11} /> Copy SQL
                      </>
                    )}
                  </button>
                </div>
                <pre className="citation-sql-code">
                  <code>{citationData.query}</code>
                </pre>
              </div>

              {citationData.raw_result && Array.isArray(citationData.raw_result) && citationData.raw_result.length > 0 && (
                <div className="citation-preview-footer">
                  <span>Kết quả ({citationData.raw_result.length} bản ghi):</span>
                  <div className="citation-preview-data">
                    {JSON.stringify(citationData.raw_result[0])}
                    {citationData.raw_result.length > 1 ? ` (+${citationData.raw_result.length - 1} dòng nữa)` : ''}
                  </div>
                </div>
              )}
            </div>
          )}
        </span>
      );
    } else {
      // If no citation metadata found for this ID, render formatted text
      elements.push(
        <React.Fragment key={`cite-fallback-${startIndex}`}>
          {renderFormattedText(innerContent, `fallback-${startIndex}`)}
        </React.Fragment>
      );
    }

    lastIndex = startIndex + fullMatch.length;
  }

  // Push trailing text formatted with Markdown
  if (lastIndex < text.length) {
    elements.push(
      <React.Fragment key={`text-${lastIndex}`}>
        {renderFormattedText(text.substring(lastIndex), `post-${lastIndex}`)}
      </React.Fragment>
    );
  }

  return <>{elements}</>;
};
