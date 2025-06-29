import React, { useState, useEffect, useCallback, useRef } from 'react';
import './PDFViewer.css';

const PDFViewer = ({ filePath, apiBaseUrl = 'http://127.0.0.1:5000' }) => {
  const [pdfState, setPdfState] = useState({
    info: null,
    currentPage: 1,
    totalPages: 0,
    zoomLevel: 1.0,
    quality: 'medium',
    isLoading: false,
    error: null,
    loadedPages: new Map(), // page_num -> image_data
    searchResults: null,
    isSearching: false
  });
  
  const [searchTerm, setSearchTerm] = useState('');
  const containerRef = useRef(null);
  const [visiblePages, setVisiblePages] = useState(new Set([1]));

  // Load PDF info when component mounts or filePath changes
  useEffect(() => {
    if (filePath) {
      loadPdfInfo();
    }
  }, [filePath]);

  // Load initial pages when PDF info is loaded
  useEffect(() => {
    if (pdfState.info && pdfState.totalPages > 0) {
      loadInitialPages();
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

  const loadInitialPages = async () => {
    // Load first 3 pages initially
    const pagesToLoad = Math.min(3, pdfState.totalPages);
    await loadPagesRange(1, pagesToLoad);
  };

  const loadPage = async (pageNum) => {
    if (pdfState.loadedPages.has(pageNum)) {
      return pdfState.loadedPages.get(pageNum);
    }

    try {
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

      setPdfState(prev => ({
        ...prev,
        loadedPages: new Map(prev.loadedPages.set(pageNum, pageData))
      }));

      return pageData;

    } catch (error) {
      console.error(`Error loading page ${pageNum}:`, error);
      throw error;
    }
  };

  const loadPagesRange = async (startPage, endPage) => {
    setPdfState(prev => ({ ...prev, isLoading: true }));

    try {
      const formData = new FormData();
      formData.append('path', filePath);
      formData.append('start_page', startPage.toString());
      formData.append('end_page', endPage.toString());
      formData.append('quality', pdfState.quality);
      formData.append('scale', pdfState.zoomLevel.toString());

      const response = await fetch(`${apiBaseUrl}/files/pdf_pages_range`, {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        throw new Error(`Failed to load pages ${startPage}-${endPage}`);
      }

      const result = await response.json();
      const pagesData = result.detail;

      setPdfState(prev => {
        const newLoadedPages = new Map(prev.loadedPages);
        pagesData.pages.forEach(pageData => {
          newLoadedPages.set(pageData.page_number, pageData);
        });

        return {
          ...prev,
          loadedPages: newLoadedPages,
          isLoading: false
        };
      });

    } catch (error) {
      setPdfState(prev => ({
        ...prev,
        error: error.message,
        isLoading: false
      }));
    }
  };

  const searchInPdf = async () => {
    if (!searchTerm.trim()) return;

    setPdfState(prev => ({ ...prev, isSearching: true }));

    try {
      const formData = new FormData();
      formData.append('path', filePath);
      formData.append('search_text', searchTerm);

      const response = await fetch(`${apiBaseUrl}/files/pdf_search`, {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        throw new Error('Search failed');
      }

      const result = await response.json();

      setPdfState(prev => ({
        ...prev,
        searchResults: result.detail,
        isSearching: false
      }));

    } catch (error) {
      setPdfState(prev => ({
        ...prev,
        error: error.message,
        isSearching: false
      }));
    }
  };

  const goToPage = (pageNum) => {
    setPdfState(prev => ({ ...prev, currentPage: pageNum }));
    
    // Scroll to page
    const pageElement = document.getElementById(`pdf-page-${pageNum}`);
    if (pageElement) {
      pageElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  const changeZoom = (delta) => {
    const newZoom = Math.max(0.5, Math.min(3.0, pdfState.zoomLevel + delta));
    setPdfState(prev => ({ 
      ...prev, 
      zoomLevel: newZoom,
      loadedPages: new Map() // Clear loaded pages to force reload at new zoom
    }));
  };

  const changeQuality = (quality) => {
    setPdfState(prev => ({
      ...prev,
      quality,
      loadedPages: new Map() // Clear loaded pages to force reload at new quality
    }));
  };

  // Intersection Observer for lazy loading
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            const pageNum = parseInt(entry.target.dataset.pageNum);
            setVisiblePages(prev => new Set(prev).add(pageNum));
            
            // Load nearby pages
            const pagesToLoad = [];
            for (let i = Math.max(1, pageNum - 1); i <= Math.min(pdfState.totalPages, pageNum + 1); i++) {
              if (!pdfState.loadedPages.has(i)) {
                pagesToLoad.push(i);
              }
            }
            
            pagesToLoad.forEach(page => loadPage(page));
          }
        });
      },
      { threshold: 0.1 }
    );

    // Observe all page placeholders
    const pageElements = document.querySelectorAll('[data-page-num]');
    pageElements.forEach(el => observer.observe(el));

    return () => observer.disconnect();
  }, [pdfState.totalPages, pdfState.loadedPages]);

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
    <div className="pdf-viewer">
      {/* Header */}
      <div className="pdf-viewer-header">
        <h3>{pdfState.info.title || filePath}</h3>
        <div className="pdf-info">
          {pdfState.info.page_count} pages • {Math.round(pdfState.info.file_size / 1024)} KB
        </div>
      </div>

      {/* Search Bar */}
      <div className="pdf-search-bar">
        <input
          type="text"
          placeholder="Search in PDF..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && searchInPdf()}
        />
        <button onClick={searchInPdf} disabled={pdfState.isSearching}>
          {pdfState.isSearching ? 'Searching...' : 'Search'}
        </button>
      </div>

      {/* Search Results */}
      {pdfState.searchResults && (
        <div className="pdf-search-results">
          <p>
            Found {pdfState.searchResults.total_matches} matches on{' '}
            {pdfState.searchResults.pages_with_matches} pages
          </p>
          <div className="search-matches">
            {pdfState.searchResults.results.map(result => (
              <button
                key={result.page_number}
                onClick={() => goToPage(result.page_number)}
                className="search-match"
              >
                Page {result.page_number} ({result.matches.length} matches)
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Toolbar */}
      <div className="pdf-toolbar">
        <div className="page-navigation">
          <button 
            onClick={() => goToPage(Math.max(1, pdfState.currentPage - 1))}
            disabled={pdfState.currentPage <= 1}
          >
            Previous
          </button>
          <span>
            Page {pdfState.currentPage} of {pdfState.totalPages}
          </span>
          <button 
            onClick={() => goToPage(Math.min(pdfState.totalPages, pdfState.currentPage + 1))}
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

        <div className="quality-controls">
          <select 
            value={pdfState.quality} 
            onChange={(e) => changeQuality(e.target.value)}
          >
            <option value="low">Low Quality</option>
            <option value="medium">Medium Quality</option>
            <option value="high">High Quality</option>
          </select>
        </div>
      </div>

      {/* PDF Content */}
      <div className="pdf-content" ref={containerRef}>
        {Array.from({ length: pdfState.totalPages }, (_, i) => {
          const pageNum = i + 1;
          const pageData = pdfState.loadedPages.get(pageNum);

          return (
            <div
              key={pageNum}
              id={`pdf-page-${pageNum}`}
              data-page-num={pageNum}
              className="pdf-page-container"
            >
              <div className="pdf-page-number">Page {pageNum}</div>
              {pageData ? (
                <div className="pdf-page">
                  <img
                    src={`data:image/png;base64,${pageData.image_data}`}
                    alt={`Page ${pageNum}`}
                    style={{
                      width: `${pageData.width * pdfState.zoomLevel}px`,
                      height: `${pageData.height * pdfState.zoomLevel}px`
                    }}
                  />
                </div>
              ) : (
                <div className="pdf-page-placeholder">
                  <div className="page-loading">Loading page {pageNum}...</div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {pdfState.isLoading && (
        <div className="pdf-loading-overlay">
          <div className="spinner"></div>
          <p>Loading pages...</p>
        </div>
      )}
    </div>
  );
};

export default PDFViewer;
