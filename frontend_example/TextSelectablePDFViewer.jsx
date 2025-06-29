import React, { useState, useEffect, useRef } from 'react';
import './TextSelectablePDFViewer.css';

const TextSelectablePDFViewer = ({ 
  filePath, 
  apiBaseUrl = 'http://127.0.0.1:5000',
  viewMode = 'text' // 'image', 'text', 'pdfjs'
}) => {
  const [pdfState, setPdfState] = useState({
    info: null,
    currentPage: 1,
    totalPages: 0,
    zoomLevel: 1.0,
    quality: 'medium',
    isLoading: false,
    error: null,
    selectedText: '',
    viewMode: viewMode
  });
  
  const containerRef = useRef(null);
  const [pdfJsLib, setPdfJsLib] = useState(null);

  // Load PDF.js dynamically
  useEffect(() => {
    if (pdfState.viewMode === 'pdfjs' && !pdfJsLib) {
      loadPdfJs();
    }
  }, [pdfState.viewMode, pdfJsLib]);

  const loadPdfJs = async () => {
    try {
      // Dynamically import PDF.js
      const pdfjsLib = await import('pdfjs-dist');
      pdfjsLib.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjsLib.version}/pdf.worker.min.js`;
      setPdfJsLib(pdfjsLib);
    } catch (error) {
      console.error('Failed to load PDF.js:', error);
      setPdfState(prev => ({ ...prev, error: 'Failed to load PDF.js library' }));
    }
  };

  // Load PDF info when component mounts or filePath changes
  useEffect(() => {
    if (filePath) {
      loadPdfInfo();
    }
  }, [filePath]);

  // Load initial page when PDF info is loaded
  useEffect(() => {
    if (pdfState.info && pdfState.totalPages > 0) {
      loadPage(1);
    }
  }, [pdfState.info]);

  const loadPdfInfo = async () => {
    setPdfState(prev => ({ ...prev, isLoading: true, error: null }));
    
    try {
      const formData = new FormData();
      formData.append('path', filePath);

      const response = await fetch(`${apiBaseUrl}/files/pdf_info`, {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        throw new Error(`Failed to load PDF info: ${response.status}`);
      }

      const result = await response.json();
      const info = result.detail;

      setPdfState(prev => ({
        ...prev,
        info,
        totalPages: info.page_count,
        isLoading: false
      }));

    } catch (error) {
      setPdfState(prev => ({
        ...prev,
        error: error.message,
        isLoading: false
      }));
    }
  };

  const loadPage = async (pageNum) => {
    setPdfState(prev => ({ ...prev, currentPage: pageNum, isLoading: true }));

    try {
      if (pdfState.viewMode === 'image') {
        await loadImagePage(pageNum);
      } else if (pdfState.viewMode === 'text') {
        await loadTextSelectablePage(pageNum);
      } else if (pdfState.viewMode === 'pdfjs') {
        await loadPdfJsPage(pageNum);
      }
    } catch (error) {
      setPdfState(prev => ({
        ...prev,
        error: error.message,
        isLoading: false
      }));
    }
  };

  const loadImagePage = async (pageNum) => {
    const formData = new FormData();
    formData.append('path', filePath);
    formData.append('page', pageNum.toString());
    formData.append('quality', pdfState.quality);
    formData.append('scale', pdfState.zoomLevel.toString());

    const response = await fetch(`${apiBaseUrl}/files/pdf_page`, {
      method: 'POST',
      body: formData
    });

    if (!response.ok) {
      throw new Error(`Failed to load page ${pageNum}`);
    }

    const result = await response.json();
    const pageData = result.detail;

    // Render image page
    const container = containerRef.current;
    if (container) {
      container.innerHTML = `
        <div class="pdf-page-container">
          <img 
            src="data:image/png;base64,${pageData.image_data}" 
            alt="Page ${pageNum}"
            class="pdf-page-background"
          />
        </div>
      `;
    }

    setPdfState(prev => ({ ...prev, isLoading: false }));
  };

  const loadTextSelectablePage = async (pageNum) => {
    const formData = new FormData();
    formData.append('path', filePath);
    formData.append('page', pageNum.toString());
    formData.append('quality', pdfState.quality);
    formData.append('scale', pdfState.zoomLevel.toString());

    const response = await fetch(`${apiBaseUrl}/files/pdf_page_with_text`, {
      method: 'POST',
      body: formData
    });

    if (!response.ok) {
      throw new Error(`Failed to load page with text ${pageNum}`);
    }

    const result = await response.json();
    const pageData = result.detail;

    // Render page with text layer
    const container = containerRef.current;
    if (container) {
      const pageContainer = document.createElement('div');
      pageContainer.className = 'pdf-page-container';

      // Background image
      const img = document.createElement('img');
      img.src = `data:image/png;base64,${pageData.image_data}`;
      img.alt = `Page ${pageNum}`;
      img.className = 'pdf-page-background';

      // Text layer
      const textLayer = document.createElement('div');
      textLayer.className = 'pdf-text-layer';

      // Add text spans
      pageData.text_layer.forEach(textBlock => {
        if (textBlock.type === 'word' && textBlock.text.trim()) {
          const span = document.createElement('span');
          span.className = 'text-span';
          span.textContent = textBlock.text;
          
          // Position the span
          span.style.left = textBlock.bbox.x + 'px';
          span.style.top = textBlock.bbox.y + 'px';
          span.style.width = textBlock.bbox.width + 'px';
          span.style.height = textBlock.bbox.height + 'px';
          span.style.fontSize = textBlock.bbox.height + 'px';
          
          textLayer.appendChild(span);
        }
      });

      pageContainer.appendChild(img);
      pageContainer.appendChild(textLayer);
      
      container.innerHTML = '';
      container.appendChild(pageContainer);

      // Add text selection handler
      textLayer.addEventListener('mouseup', handleTextSelection);
    }

    setPdfState(prev => ({ ...prev, isLoading: false }));
  };

  const loadPdfJsPage = async (pageNum) => {
    if (!pdfJsLib) {
      throw new Error('PDF.js not loaded');
    }

    try {
      const pdfUrl = `${apiBaseUrl}/files/pdf_raw?path=${encodeURIComponent(filePath)}`;
      const pdf = await pdfJsLib.getDocument(pdfUrl).promise;
      const page = await pdf.getPage(pageNum);
      
      const scale = pdfState.zoomLevel * 1.5;
      const viewport = page.getViewport({ scale });
      
      // Create canvas
      const canvas = document.createElement('canvas');
      const context = canvas.getContext('2d');
      canvas.height = viewport.height;
      canvas.width = viewport.width;
      
      // Create container
      const pageContainer = document.createElement('div');
      pageContainer.className = 'pdf-page-container';
      pageContainer.style.position = 'relative';
      
      // Render PDF page
      const renderContext = {
        canvasContext: context,
        viewport: viewport
      };
      
      await page.render(renderContext).promise;
      
      // Create text layer
      const textLayerDiv = document.createElement('div');
      textLayerDiv.className = 'pdf-text-layer';
      textLayerDiv.style.width = viewport.width + 'px';
      textLayerDiv.style.height = viewport.height + 'px';
      
      pageContainer.appendChild(canvas);
      pageContainer.appendChild(textLayerDiv);
      
      const container = containerRef.current;
      if (container) {
        container.innerHTML = '';
        container.appendChild(pageContainer);
      }
      
      // Render text layer
      const textContent = await page.getTextContent();
      
      textContent.items.forEach(item => {
        if (item.str.trim()) {
          const span = document.createElement('span');
          span.textContent = item.str;
          span.className = 'text-span';
          
          const transform = item.transform;
          const x = transform[4];
          const y = viewport.height - transform[5];
          const fontSize = transform[0];
          
          span.style.left = x + 'px';
          span.style.top = (y - fontSize) + 'px';
          span.style.fontSize = fontSize + 'px';
          span.style.transform = `scaleX(${transform[0] / fontSize})`;
          
          textLayerDiv.appendChild(span);
        }
      });
      
      textLayerDiv.addEventListener('mouseup', handleTextSelection);
      
    } catch (error) {
      throw new Error(`PDF.js error: ${error.message}`);
    }

    setPdfState(prev => ({ ...prev, isLoading: false }));
  };

  const handleTextSelection = () => {
    const selection = window.getSelection();
    if (selection.toString().trim()) {
      const selectedText = selection.toString();
      setPdfState(prev => ({ ...prev, selectedText }));
      
      // Custom event for text selection
      if (window.onPdfTextSelected) {
        window.onPdfTextSelected(selectedText, pdfState.currentPage);
      }
    }
  };

  const goToPage = (pageNum) => {
    if (pageNum >= 1 && pageNum <= pdfState.totalPages) {
      loadPage(pageNum);
    }
  };

  const changeZoom = (delta) => {
    const newZoom = Math.max(0.5, Math.min(3.0, pdfState.zoomLevel + delta));
    setPdfState(prev => ({ ...prev, zoomLevel: newZoom }));
    
    // Reload current page with new zoom
    if (pdfState.currentPage) {
      loadPage(pdfState.currentPage);
    }
  };

  const changeViewMode = (mode) => {
    setPdfState(prev => ({ ...prev, viewMode: mode }));
    
    // Reload current page with new mode
    if (pdfState.currentPage) {
      loadPage(pdfState.currentPage);
    }
  };

  if (pdfState.error) {
    return (
      <div className="pdf-viewer-error">
        <h3>Error loading PDF</h3>
        <p>{pdfState.error}</p>
        <button onClick={loadPdfInfo}>Retry</button>
      </div>
    );
  }

  if (!pdfState.info) {
    return (
      <div className="pdf-viewer-loading">
        <div className="spinner"></div>
        <p>Loading PDF information...</p>
      </div>
    );
  }

  return (
    <div className="text-selectable-pdf-viewer">
      {/* Header */}
      <div className="pdf-viewer-header">
        <h3>{pdfState.info.title || filePath}</h3>
        <div className="pdf-info">
          {pdfState.info.page_count} pages • {Math.round(pdfState.info.file_size / 1024)} KB
        </div>
      </div>

      {/* View Mode Selector */}
      <div className="mode-selector">
        <label>
          <input 
            type="radio" 
            name="viewMode" 
            value="image" 
            checked={pdfState.viewMode === 'image'}
            onChange={(e) => changeViewMode(e.target.value)}
          />
          Image Mode (Fast)
        </label>
        <label>
          <input 
            type="radio" 
            name="viewMode" 
            value="text" 
            checked={pdfState.viewMode === 'text'}
            onChange={(e) => changeViewMode(e.target.value)}
          />
          Text Selection Mode
        </label>
        <label>
          <input 
            type="radio" 
            name="viewMode" 
            value="pdfjs" 
            checked={pdfState.viewMode === 'pdfjs'}
            onChange={(e) => changeViewMode(e.target.value)}
          />
          PDF.js Mode (Best)
        </label>
      </div>

      {/* Toolbar */}
      <div className="pdf-toolbar">
        <div className="page-navigation">
          <button 
            onClick={() => goToPage(pdfState.currentPage - 1)}
            disabled={pdfState.currentPage <= 1}
          >
            Previous
          </button>
          <span>
            Page {pdfState.currentPage} of {pdfState.totalPages}
          </span>
          <button 
            onClick={() => goToPage(pdfState.currentPage + 1)}
            disabled={pdfState.currentPage >= pdfState.totalPages}
          >
            Next
          </button>
        </div>

        <div className="zoom-controls">
          <button onClick={() => changeZoom(-0.25)}>Zoom Out</button>
          <span>{Math.round(pdfState.zoomLevel * 100)}%</span>
          <button onClick={() => changeZoom(0.25)}>Zoom In</button>
        </div>
      </div>

      {/* PDF Content */}
      <div className="pdf-content" ref={containerRef}>
        {pdfState.isLoading && (
          <div className="loading">
            <div className="spinner"></div>
            <p>Loading page {pdfState.currentPage}...</p>
          </div>
        )}
      </div>

      {/* Selected Text Display */}
      {pdfState.selectedText && (
        <div className="selection-info">
          <strong>Selected Text:</strong>
          <p>"{pdfState.selectedText.substring(0, 200)}{pdfState.selectedText.length > 200 ? '...' : ''}"</p>
          <button onClick={() => setPdfState(prev => ({ ...prev, selectedText: '' }))}>
            Clear
          </button>
        </div>
      )}
    </div>
  );
};

export default TextSelectablePDFViewer;
