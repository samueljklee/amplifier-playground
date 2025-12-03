import { useState, useEffect } from 'react';
import type { ProfileContent } from '../types';
import { getProfileContent, saveProfileContent } from '../api';
import { DependencyGraphViewer } from './DependencyGraphViewer';

interface ProfileViewerProps {
  profileName: string | null;
  onClose: () => void;
}

export function ProfileViewer({ profileName, onClose }: ProfileViewerProps) {
  const [content, setContent] = useState<ProfileContent | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [editedContent, setEditedContent] = useState('');
  const [showGraph, setShowGraph] = useState(false);

  useEffect(() => {
    if (!profileName) {
      setContent(null);
      setIsEditing(false);
      setShowGraph(false);
      return;
    }

    setLoading(true);
    setError(null);
    setIsEditing(false);
    setShowGraph(false);

    getProfileContent(profileName)
      .then((data) => {
        setContent(data);
        setEditedContent(data.content);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [profileName]);

  const handleEdit = () => {
    if (content) {
      setEditedContent(content.content);
      setIsEditing(true);
    }
  };

  const handleCancel = () => {
    if (content) {
      setEditedContent(content.content);
    }
    setIsEditing(false);
  };

  const handleSave = async () => {
    if (!profileName) return;

    setSaving(true);
    setError(null);

    try {
      const saved = await saveProfileContent(profileName, editedContent);
      setContent(saved);
      setIsEditing(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to save');
    } finally {
      setSaving(false);
    }
  };

  if (!profileName) return null;

  return (
    <div className="profile-viewer-overlay" onClick={onClose}>
      <div className="profile-viewer" onClick={(e) => e.stopPropagation()}>
        <div className="profile-viewer-header">
          <div>
            <h2>{profileName}</h2>
            {content && <p className="profile-path">{content.path}</p>}
          </div>
          <div className="profile-viewer-actions">
            <button
              onClick={() => setShowGraph(true)}
              className="button small view-graph-btn"
              disabled={!content || loading}
            >
              View Graph
            </button>
            {!isEditing ? (
              <button onClick={handleEdit} className="button small" disabled={!content || loading}>
                Edit
              </button>
            ) : (
              <>
                <button onClick={handleSave} className="button primary small" disabled={saving}>
                  {saving ? 'Saving...' : 'Save'}
                </button>
                <button onClick={handleCancel} className="button small" disabled={saving}>
                  Cancel
                </button>
              </>
            )}
            <button onClick={onClose} className="button small close-btn">X</button>
          </div>
        </div>

        <div className="profile-viewer-content">
          {loading && <p className="loading">Loading...</p>}
          {error && <p className="error">{error}</p>}
          {content && !loading && (
            isEditing ? (
              <textarea
                className="profile-editor"
                value={editedContent}
                onChange={(e) => setEditedContent(e.target.value)}
                disabled={saving}
              />
            ) : (
              <pre className="profile-markdown">{content.content}</pre>
            )
          )}
        </div>

        {/* Dependency Graph Viewer Modal */}
        {showGraph && (
          <DependencyGraphViewer
            profileName={profileName}
            onClose={() => setShowGraph(false)}
          />
        )}
      </div>
    </div>
  );
}
