import React, { useEffect, useState } from "react";

function PptxViewer({ fileId, apiBase = "/pptx" }) {
  const [info, setInfo] = useState(null);
  const [slide, setSlide] = useState(1);
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
    fetch(`${apiBase}_slide?file_id=${fileId}&slide=${slide}`)
      .then((res) => res.json())
      .then((data) => {
        setHtml(data.html || "<div>No content</div>");
        setLoading(false);
      });
  }, [info, slide, fileId, apiBase]);

  if (!info) return <div>Loading presentation info...</div>;

  return (
    <div>
      <div style={{ marginBottom: 8 }}>
        <button onClick={() => setSlide((s) => Math.max(1, s - 1))} disabled={slide === 1}>Prev</button>
        <span style={{ margin: "0 8px" }}>
          Slide {slide} / {info.slide_count}
        </span>
        <button onClick={() => setSlide((s) => Math.min(info.slide_count, s + 1))} disabled={slide === info.slide_count}>Next</button>
      </div>
      <div style={{ border: "1px solid #ccc", minHeight: 400, padding: 16, background: "#fff" }}>
        {loading ? <div>Loading slide...</div> : <div dangerouslySetInnerHTML={{ __html: html }} />}
      </div>
    </div>
  );
}

export default PptxViewer;
