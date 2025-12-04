import { useState, useEffect } from 'react';
import { AlertCircle, Check } from 'lucide-react';
import './MountPlanInputModal.css';

interface MountPlanInputModalProps {
  onConfirm: (mountPlan: Record<string, unknown>) => void;
  onClose: () => void;
  initialValue?: string;
}

export function MountPlanInputModal({ onConfirm, onClose, initialValue = '' }: MountPlanInputModalProps) {
  const [jsonInput, setJsonInput] = useState(initialValue);
  const [error, setError] = useState<string | null>(null);
  const [isValid, setIsValid] = useState(false);

  useEffect(() => {
    if (!jsonInput.trim()) {
      setError(null);
      setIsValid(false);
      return;
    }

    try {
      const parsed = JSON.parse(jsonInput);
      if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
        setError('Mount plan must be a JSON object');
        setIsValid(false);
      } else {
        setError(null);
        setIsValid(true);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Invalid JSON');
      setIsValid(false);
    }
  }, [jsonInput]);

  const handleConfirm = () => {
    if (!isValid) return;
    try {
      const parsed = JSON.parse(jsonInput);
      onConfirm(parsed);
    } catch {
      // Should not happen since we validated
    }
  };

  const handlePaste = async () => {
    try {
      const text = await navigator.clipboard.readText();
      setJsonInput(text);
    } catch {
      // Clipboard access denied
    }
  };

  const formatJson = () => {
    if (!isValid) return;
    try {
      const parsed = JSON.parse(jsonInput);
      setJsonInput(JSON.stringify(parsed, null, 2));
    } catch {
      // Should not happen
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal mount-plan-input-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Custom Mount Plan</h3>
          <button onClick={onClose} className="button small close-btn">X</button>
        </div>

        <div className="modal-body">
          <p className="modal-description">
            Paste a mount plan JSON to run a session with custom configuration.
          </p>

          <div className="json-input-actions">
            <button onClick={handlePaste} className="button small">
              Paste from Clipboard
            </button>
            <button onClick={formatJson} className="button small" disabled={!isValid}>
              Format JSON
            </button>
          </div>

          <textarea
            value={jsonInput}
            onChange={(e) => setJsonInput(e.target.value)}
            placeholder='{"session": {"orchestrator": "loop-basic"}, "providers": [...], ...}'
            className={`json-input ${error ? 'has-error' : ''} ${isValid ? 'is-valid' : ''}`}
            rows={15}
            spellCheck={false}
          />

          {error && (
            <div className="json-error">
              <AlertCircle size={14} />
              {error}
            </div>
          )}

          {isValid && (
            <div className="json-valid">
              <Check size={14} />
              Valid JSON
            </div>
          )}
        </div>

        <div className="modal-footer">
          <button onClick={onClose} className="button secondary">
            Cancel
          </button>
          <button onClick={handleConfirm} className="button primary" disabled={!isValid}>
            Use Mount Plan
          </button>
        </div>
      </div>
    </div>
  );
}
