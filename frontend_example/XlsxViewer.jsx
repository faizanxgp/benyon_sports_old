import React, { useEffect, useState } from "react";

function XlsxViewer({ fileId, apiBase = "/xlsx" }) {
  const [info, setInfo] = useState(null);
  const [sheetIdx, setSheetIdx] = useState(0);
  const [html, setHtml] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetch(`${apiBase}_info?file_id=${fileId}`)
      .then((res) => res.json())
      .then(setInfo);
  }, [fileId, apiBase]);

  useEffect(() => {
    if (!info) return;
    setLoading(true);
    fetch(`${apiBase}_sheet?file_id=${fileId}&sheet=${sheetIdx}`)
      .then((res) => res.json())
      .then((data) => {
        setHtml(data.html || "<div>No content</div>");
        setLoading(false);
      });
  }, [info, sheetIdx, fileId, apiBase]);

  if (!info) return <div>Loading spreadsheet info...</div>;

  return (
    <div>
      <div style={{ marginBottom: 8 }}>
        <button onClick={() => setSheetIdx((i) => Math.max(0, i - 1))} disabled={sheetIdx === 0}>Prev</button>
        <span style={{ margin: "0 8px" }}>
          Sheet {sheetIdx + 1} / {info.sheets.length} ({info.sheets[sheetIdx]})
        </span>
        <button onClick={() => setSheetIdx((i) => Math.min(info.sheets.length - 1, i + 1))} disabled={sheetIdx === info.sheets.length - 1}>Next</button>
      </div>
      <div style={{ border: "1px solid #ccc", minHeight: 400, padding: 16, background: "#fff", overflowX: "auto" }}>
        {loading ? <div>Loading sheet...</div> : <div dangerouslySetInnerHTML={{ __html: html }} />}
      </div>
    </div>
  );
}

export default XlsxViewer;
