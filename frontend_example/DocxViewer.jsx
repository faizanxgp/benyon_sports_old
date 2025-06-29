import React, { useEffect, useState } from "react";

function DocxViewer({ fileId, apiBase = "/docx" }) {
  const [info, setInfo] = useState(null);
  const [page, setPage] = useState(1);
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
    fetch(`${apiBase}_page?file_id=${fileId}&page=${page}`)
      .then((res) => res.json())
      .then((data) => {
        setHtml(data.html || "<div>No content</div>");
        setLoading(false);
      });
  }, [info, page, fileId, apiBase]);

  if (!info) return <div>Loading document info...</div>;

  return (
    <div>
      <div style={{ marginBottom: 8 }}>
        <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}>Prev</button>
        <span style={{ margin: "0 8px" }}>
          Page {page} / {info.page_count}
        </span>
        <button onClick={() => setPage((p) => Math.min(info.page_count, p + 1))} disabled={page === info.page_count}>Next</button>
      </div>
      <div style={{ border: "1px solid #ccc", minHeight: 400, padding: 16, background: "#fff" }}>
        {loading ? <div>Loading page...</div> : <div dangerouslySetInnerHTML={{ __html: html }} />}
      </div>
    </div>
  );
}

export default DocxViewer;
