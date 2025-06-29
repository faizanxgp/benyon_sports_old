# Incremental PDF Preview System with Text Selection

This implementation provides a Google Drive-style PDF preview feature that allows users to browse large PDFs incrementally in their browser **with full text selection support**.

## Features

### Backend (FastAPI)
- **PDF Information**: Get metadata like page count, dimensions, file size
- **Single Page Loading**: Load specific pages on demand
- **Page with Text Layer**: Load pages with selectable text overlay
- **Text Layer Only**: Get just the text positioning data
- **Raw PDF Serving**: Serve original PDF files for PDF.js
- **Range Loading**: Load multiple pages at once (max 5 pages per request)
- **Search Functionality**: Search for text within PDFs and get page locations
- **Quality Control**: Low, medium, high quality rendering
- **Zoom Support**: Dynamic scaling from 0.5x to 3.0x
- **Caching**: In-memory PDF caching to avoid repeated file opening
- **Error Handling**: Comprehensive error handling and validation

### Frontend (React + Vanilla JS)
- **Three Viewing Modes**:
  1. **Image Mode**: Fast rendering, no text selection (like original implementation)
  2. **Text Selection Mode**: Custom text layer overlay with selectable text
  3. **PDF.js Mode**: Full PDF.js integration with native text selection
- **Text Selection**: Users can select, copy, and interact with PDF text
- **Lazy Loading**: Pages load only when needed (Intersection Observer)
- **Virtual Scrolling**: Efficient rendering of large documents
- **Search Integration**: Real-time search with result navigation
- **Zoom Controls**: Smooth zoom in/out functionality
- **Quality Selection**: Choose rendering quality
- **Responsive Design**: Works on desktop and mobile
- **Touch Support**: Mobile-friendly interactions
- **Loading States**: Proper loading indicators and error handling

## API Endpoints

### 1. Get PDF Information
```
POST /files/pdf_info
Body: path=docs/sample.pdf
```
Returns:
```json
{
  "detail": {
    "page_count": 25,
    "width": 595.32,
    "height": 841.92,
    "title": "Sample Document",
    "file_size": 1048576
  }
}
```

### 2. Get Single Page (Image Only)
```
POST /files/pdf_page
Body: 
  path=docs/sample.pdf
  page=1
  quality=medium (low|medium|high)
  scale=1.0
```
Returns:
```json
{
  "detail": {
    "page_number": 1,
    "image_data": "base64_encoded_png",
    "width": 893,
    "height": 1262,
    "scale": 1.5
  }
}
```

### 3. Get Page with Text Layer (NEW!)
```
POST /files/pdf_page_with_text
Body: 
  path=docs/sample.pdf
  page=1
  quality=medium
  scale=1.0
```
Returns:
```json
{
  "detail": {
    "page_number": 1,
    "image_data": "base64_encoded_png",
    "width": 893,
    "height": 1262,
    "scale": 1.5,
    "text_layer": [
      {
        "text": "Hello",
        "bbox": {"x": 100, "y": 200, "width": 50, "height": 15},
        "block_no": 0,
        "line_no": 0,
        "word_no": 0,
        "type": "word"
      }
    ]
  }
}
```

### 4. Get Text Layer Only (NEW!)
```
POST /files/pdf_text_layer
Body:
  path=docs/sample.pdf
  page=1
  scale=1.0
```
Returns:
```json
{
  "detail": {
    "page_number": 1,
    "scale": 1.0,
    "text_blocks": [...],
    "text_paragraphs": [...],
    "page_width": 595.32,
    "page_height": 841.92
  }
}
```

### 5. Get Raw PDF File (NEW!)
```
GET /files/pdf_raw?path=docs/sample.pdf
```
Returns: Raw PDF file with `Content-Type: application/pdf`

### 6. Get Page Range
```
POST /files/pdf_pages_range
Body:
  path=docs/sample.pdf
  start_page=1
  end_page=3
  quality=medium
  scale=1.0
```
Returns:
```json
{
  "detail": {
    "pages": [
      {
        "page_number": 1,
        "image_data": "base64_encoded_png",
        "width": 893,
        "height": 1262
      }
    ],
    "start_page": 1,
    "end_page": 3,
    "total_pages": 3
  }
}
```

### 7. Search in PDF
```
POST /files/pdf_search
Body:
  path=docs/sample.pdf
  search_text=keyword
```
Returns:
```json
{
  "detail": {
    "search_text": "keyword",
    "total_matches": 5,
    "pages_with_matches": 3,
    "results": [
      {
        "page_number": 1,
        "matches": [
          {
            "position": {"x": 100, "y": 200, "width": 50, "height": 15},
            "context": "surrounding text with keyword highlighted"
          }
        ]
      }
    ]
  }
}
```

## Usage Examples

### Backend Setup
Your FastAPI app already has the necessary endpoints. Make sure you have the required dependencies:

```bash
pip install PyMuPDF Pillow
```

### Frontend Usage (React)
```jsx
import PDFViewer from './PDFViewer';

function DocumentModal({ pdfPath, onClose }) {
  return (
    <div className="modal">
      <div className="modal-header">
        <h2>Document Preview</h2>
        <button onClick={onClose}>×</button>
      </div>
      <div className="modal-content">
        <PDFViewer 
          filePath={pdfPath}
          apiBaseUrl="http://127.0.0.1:5000"
        />
      </div>
    </div>
  );
}
```

### Vanilla JavaScript Usage
Open `frontend_example/pdf_preview.html` in your browser and enter a PDF path to test.

## Performance Optimizations

### Backend
1. **PDF Caching**: PDFs are cached in memory to avoid repeated file operations
2. **Page Limits**: Maximum 5 pages per range request to prevent memory issues
3. **Quality Settings**: Different rendering qualities for bandwidth optimization
4. **Error Handling**: Proper validation and error responses

### Frontend
1. **Intersection Observer**: Pages load only when visible
2. **Image Optimization**: Base64 images with proper sizing
3. **Memory Management**: Loaded pages are managed efficiently
4. **Debounced Search**: Search requests are optimized
5. **Responsive Images**: Images scale properly on different devices

## Browser Compatibility

- **Modern Browsers**: Chrome 60+, Firefox 55+, Safari 12+, Edge 79+
- **Mobile**: iOS Safari 12+, Chrome Mobile 60+
- **Features Used**: Intersection Observer, Fetch API, CSS Grid/Flexbox

## Security Considerations

1. **Path Validation**: File paths are validated and sanitized
2. **JWT Authentication**: All endpoints require valid JWT tokens
3. **File Access Control**: Users can only access files they have permission for
4. **Content Security**: PDF content is rendered as images (no executable content)

## Deployment Notes

### Production Optimizations
1. **CDN**: Serve base64 images through a CDN for better performance
2. **Compression**: Enable gzip compression for API responses
3. **Caching Headers**: Set appropriate cache headers for static content
4. **Rate Limiting**: Implement rate limiting for PDF processing endpoints

### Environment Variables
```bash
# Optional: Configure cache settings
PDF_CACHE_SIZE=20
PDF_QUALITY_DEFAULT=medium
MAX_PAGES_PER_REQUEST=5
```

## Troubleshooting

### Common Issues
1. **Large Files**: For very large PDFs (>100MB), consider implementing file streaming
2. **Memory Usage**: Monitor memory usage, especially with high-quality renders
3. **CORS**: Ensure CORS is properly configured for your frontend domain
4. **JWT Tokens**: Make sure JWT tokens are properly included in requests

### Error Messages
- `"Invalid file path"`: Check file path and permissions
- `"Preview not supported"`: File is not a PDF
- `"Page X not found"`: Page number exceeds document length
- `"Maximum X pages per request"`: Reduce page range size

## Future Enhancements

1. **Text Layer**: Add selectable text overlay on images
2. **Annotations**: Support for PDF annotations and comments
3. **Thumbnails**: Generate thumbnail navigation
4. **Full-text Search**: Index PDF content for faster search
5. **Print Support**: Add print functionality
6. **Download Options**: Allow downloading specific pages
7. **Bookmark Support**: Navigate using PDF bookmarks
8. **Collaborative Features**: Real-time collaborative viewing
