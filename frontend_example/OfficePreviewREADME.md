# Office Document Preview Components

This folder contains React components for incremental, in-browser preview of MS Office documents (Word, Excel, PowerPoint), consuming the backend preview endpoints.

## Components

- `DocxViewer.jsx`: Paginated preview for Word (DOCX) files.
- `XlsxViewer.jsx`: Sheet-by-sheet preview for Excel (XLSX) files.
- `PptxViewer.jsx`: Slide-by-slide preview for PowerPoint (PPTX) files.

## Usage Example

```
import DocxViewer from './DocxViewer';
import XlsxViewer from './XlsxViewer';
import PptxViewer from './PptxViewer';

// ...
<DocxViewer fileId="your_file_id" />
<XlsxViewer fileId="your_file_id" />
<PptxViewer fileId="your_file_id" />
```

- `fileId` is the identifier used by your backend to locate the file.
- The components fetch metadata and HTML for each page/sheet/slide incrementally.
- Navigation controls are provided for browsing.

## Backend Endpoints Expected

- `/docx_info?file_id=...` → `{ page_count, ... }`
- `/docx_page?file_id=...&page=...` → `{ html }`
- `/xlsx_info?file_id=...` → `{ sheets: ["Sheet1", ...] }`
- `/xlsx_sheet?file_id=...&sheet=...` → `{ html }`
- `/pptx_info?file_id=...` → `{ slide_count, ... }`
- `/pptx_slide?file_id=...&slide=...` → `{ html }`

## Notes

- The HTML is rendered using `dangerouslySetInnerHTML`. Ensure your backend sanitizes output.
- For advanced features (images, tables, formatting), further backend and frontend work may be needed.
- These components are designed for integration into your document management frontend.
