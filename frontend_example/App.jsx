import React from 'react';
import PDFViewer from './PDFViewer';

const App = () => {
  return (
    <div className="App">
      <h1>PDF Preview Demo</h1>
      
      {/* Example usage */}
      <PDFViewer 
        filePath="docs/sample.pdf"
        apiBaseUrl="http://127.0.0.1:5000"
      />
    </div>
  );
};

export default App;
