import React, { useRef, useState } from 'react';

function BankStatementUpload({ onFileSelect, formType }) {
  const [selectedFile, setSelectedFile] = useState(null);
  const [error, setError] = useState(null);
  const fileInputRef = useRef(null);

  const inputId = `bank-upload-${formType}`;

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (!file) return;

    if (!file.name.toLowerCase().endsWith('.csv')) {
      setError('Invalid file format. Please upload a .csv file.');
      setSelectedFile(null);
      onFileSelect(null);
      // Clear the input
      if (fileInputRef.current) fileInputRef.current.value = '';
      // Auto-dismiss error after 4s
      setTimeout(() => setError(null), 4000);
      return;
    }

    setError(null);
    setSelectedFile(file);
    onFileSelect(file);
  };

  const handleRemove = () => {
    setSelectedFile(null);
    setError(null);
    onFileSelect(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  return (
    <div className="space-y-4">
      <div className="bg-surface-container-low border-2 border-dashed border-outline-variant/50 rounded-xl p-8 flex flex-col items-center text-center space-y-4">
        <div className="w-16 h-16 bg-surface-container-highest rounded-full flex items-center justify-center">
          <span className="material-symbols-outlined text-slate-900 dark:text-white text-3xl">cloud_upload</span>
        </div>
        <div>
          <h3 className="text-sm font-bold uppercase tracking-widest text-slate-900 dark:text-white">UPLOAD BANK STATEMENT CSV</h3>
          <p className="text-xs text-on-surface-variant dark:text-slate-400 mt-2 max-w-sm">
            {formType === 'msme'
              ? '6-12 months of bank statements. Expected columns: date, amount, type (debit/credit), description'
              : 'We derive 26 behavioral signals from your bank statement — no manual entry needed'}
          </p>
        </div>
        <input
          accept=".csv"
          className="hidden"
          id={inputId}
          type="file"
          ref={fileInputRef}
          onChange={handleFileChange}
        />
        <label
          className="bg-slate-900 text-white px-6 py-3 rounded-full font-bold text-xs uppercase tracking-widest cursor-pointer hover:bg-slate-800 transition-colors"
          htmlFor={inputId}
        >
          Select .csv File
        </label>
      </div>

      {/* File selected confirmation */}
      {selectedFile && (
        <div className="flex items-center justify-between bg-tertiary-container/20 border border-tertiary/20 px-4 py-3 rounded-lg">
          <span className="text-sm text-on-surface dark:text-slate-200 font-medium">
            <span className="text-tertiary font-bold">✓</span> {selectedFile.name} selected
          </span>
          <button
            type="button"
            onClick={handleRemove}
            className="text-xs text-error font-bold uppercase tracking-widest hover:underline"
          >
            Remove
          </button>
        </div>
      )}

      {/* Error toast */}
      {error && (
        <div className="flex items-center gap-2 bg-error-container/30 border border-error/20 px-4 py-3 rounded-lg">
          <span className="material-symbols-outlined text-error text-lg">error</span>
          <span className="text-sm text-on-error-container font-medium">{error}</span>
        </div>
      )}
    </div>
  );
}

export default BankStatementUpload;
