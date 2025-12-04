import { useState, useEffect } from 'react';
import type { ProfileDependencyGraph, DependencyFile } from '../types';
import { getProfileDependencyGraph } from '../api';
import { MountPlanViewer } from './MountPlanViewer';

interface DependencyGraphViewerProps {
  profileName: string | null;
  onClose: () => void;
}

type ViewTab = 'dependencies' | 'mount-plan';

function getFileIcon(file: DependencyFile): string {
  if (file.file_type === 'profile') return 'P';
  if (file.file_type === 'context') return 'C';
  if (file.file_type === 'agent') return 'A';
  return 'F';
}

function getRelationshipLabel(relationship: string): string {
  switch (relationship) {
    case 'root': return 'Profile';
    case 'extends': return 'Extends';
    case 'mentions': return 'Context (@mentions)';
    case 'agents': return 'Agents';
    default: return relationship;
  }
}

function getShortPath(path: string): string {
  const parts = path.split('/');
  return parts.slice(-2).join('/');
}

export function DependencyGraphViewer({ profileName, onClose }: DependencyGraphViewerProps) {
  const [graph, setGraph] = useState<ProfileDependencyGraph | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<DependencyFile | null>(null);
  const [activeTab, setActiveTab] = useState<ViewTab>('dependencies');

  useEffect(() => {
    if (!profileName) {
      setGraph(null);
      setSelectedFile(null);
      return;
    }

    setLoading(true);
    setError(null);
    setSelectedFile(null);

    getProfileDependencyGraph(profileName)
      .then((data) => {
        setGraph(data);
        // Auto-select the root file
        const rootFile = data.files.find(f => f.relationship === 'root');
        if (rootFile) {
          setSelectedFile(rootFile);
        }
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [profileName]);

  if (!profileName) return null;

  // Group files by relationship
  const groupedFiles: Record<string, DependencyFile[]> = {};
  if (graph) {
    for (const file of graph.files) {
      const key = file.relationship;
      if (!groupedFiles[key]) {
        groupedFiles[key] = [];
      }
      groupedFiles[key].push(file);
    }
  }

  // Order: root first, then extends, then agents, then mentions
  const orderedGroups = ['root', 'extends', 'agents', 'mentions'].filter(k => groupedFiles[k]?.length);

  return (
    <div className="graph-viewer-overlay" onClick={onClose}>
      <div className="graph-viewer" onClick={(e) => e.stopPropagation()}>
        {/* Header with tabs */}
        <div className="graph-viewer-header">
          <div className="graph-viewer-title">
            <h2>{profileName}</h2>
          </div>
          <div className="graph-viewer-tabs">
            <button
              className={`tab-button ${activeTab === 'dependencies' ? 'active' : ''}`}
              onClick={() => setActiveTab('dependencies')}
            >
              Dependencies
            </button>
            <button
              className={`tab-button ${activeTab === 'mount-plan' ? 'active' : ''}`}
              onClick={() => setActiveTab('mount-plan')}
            >
              Mount Plan
            </button>
          </div>
          <button onClick={onClose} className="button small close-btn">X</button>
        </div>

        {/* Main content area */}
        <div className="graph-viewer-body">
          {loading && (
            <div className="graph-loading">Loading...</div>
          )}

          {error && (
            <div className="graph-error">{error}</div>
          )}

          {graph && !loading && activeTab === 'dependencies' && (
            <>
              {/* File tree sidebar */}
              <div className="file-tree-sidebar">
                <div className="file-tree-header">Files ({graph.files.length})</div>
                <div className="file-tree">
                  {orderedGroups.map(groupKey => (
                    <div key={groupKey} className="file-group">
                      <div className="file-group-label">
                        {getRelationshipLabel(groupKey)}
                      </div>
                      {groupedFiles[groupKey].map((file, idx) => (
                        <div
                          key={`${groupKey}-${idx}`}
                          className={`file-tree-item ${selectedFile?.path === file.path ? 'selected' : ''}`}
                          onClick={() => setSelectedFile(file)}
                        >
                          <span className={`file-icon file-icon-${file.file_type}`}>
                            {getFileIcon(file)}
                          </span>
                          <span className="file-name" title={file.path}>
                            {file.name}
                          </span>
                        </div>
                      ))}
                    </div>
                  ))}
                </div>
              </div>

              {/* Content panel */}
              <div className="content-panel">
                {selectedFile ? (
                  <>
                    <div className="content-panel-header">
                      <div className="content-file-info">
                        <span className={`file-badge file-badge-${selectedFile.file_type}`}>
                          {selectedFile.file_type}
                        </span>
                        <span className="content-file-name">{selectedFile.name}</span>
                      </div>
                      <div className="content-file-path" title={selectedFile.path}>
                        {getShortPath(selectedFile.path)}
                      </div>
                      {selectedFile.referenced_by.length > 0 && (
                        <div className="content-file-referrers">
                          <span className="referrer-label">Referenced by:</span>
                          {selectedFile.referenced_by.map((ref, idx) => {
                            const refFile = graph?.files.find(f => f.path === ref);
                            return (
                              <span
                                key={idx}
                                className={`referrer-item ${refFile ? 'clickable' : ''}`}
                                title={ref}
                                onClick={() => refFile && setSelectedFile(refFile)}
                              >
                                {getShortPath(ref)}
                              </span>
                            );
                          })}
                        </div>
                      )}
                    </div>
                    <div className="content-panel-body">
                      <pre className="file-content">{selectedFile.content}</pre>
                    </div>
                  </>
                ) : (
                  <div className="content-empty">
                    Select a file from the sidebar to view its contents
                  </div>
                )}
              </div>
            </>
          )}

          {graph && !loading && activeTab === 'mount-plan' && (
            <MountPlanViewer plan={graph.mount_plan} />
          )}
        </div>
      </div>
    </div>
  );
}
