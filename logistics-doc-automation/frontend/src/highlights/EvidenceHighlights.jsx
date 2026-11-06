import React, { Component, useEffect, useRef } from 'react';

export const EVIDENCE_HIGHLIGHTS_ENABLED = import.meta.env.VITE_ENABLE_HIGHLIGHTS === 'true';

class EvidenceOverlayErrorBoundary extends Component {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  componentDidCatch() {}

  render() {
    return this.state.failed ? null : this.props.children;
  }
}

const EvidenceOverlayContent = ({ locations, pageNumber, activeField, onFieldSelect }) => {
  const activeRectRef = useRef(null);

  const pageLocations = Object.entries(locations || {}).filter(([fieldKey, location]) => (
    !fieldKey.startsWith('charges.')
    && Number(location?.page) === Number(pageNumber)
    && Array.isArray(location?.rects)
  ));

  useEffect(() => {
    try {
      activeRectRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'center' });
    } catch {
      // A missing or stale highlight must not affect the document viewer.
    }
  }, [activeField, pageNumber]);

  const handleSelect = (fieldKey) => {
    try {
      onFieldSelect?.(fieldKey);
    } catch {
      // Ignore highlight-only failures and keep the review screen usable.
    }
  };

  return (
    <div
      aria-label="Extracted value locations"
      style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }}
    >
      {pageLocations.flatMap(([fieldKey, location]) => location.rects.map((rect, rectIndex) => {
        const isActive = fieldKey === activeField;
        return (
          <button
            key={`${fieldKey}-${rectIndex}`}
            ref={isActive ? activeRectRef : null}
            type="button"
            title={fieldKey}
            aria-label={`Select extracted field ${fieldKey}`}
            onClick={() => handleSelect(fieldKey)}
            style={{
              position: 'absolute',
              display: 'block',
              left: `${rect[0] * 100}%`,
              top: `${rect[1] * 100}%`,
              width: `${Math.max(0, rect[2] - rect[0]) * 100}%`,
              height: `${Math.max(0, rect[3] - rect[1]) * 100}%`,
              minWidth: 2,
              minHeight: 3,
              padding: 0,
              border: isActive ? '2px solid #f97316' : '1px solid rgba(234, 179, 8, 0.68)',
              borderRadius: 2,
              background: isActive ? 'rgba(249, 115, 22, 0.35)' : 'rgba(250, 204, 21, 0.24)',
              pointerEvents: 'auto',
              cursor: 'pointer',
              boxSizing: 'border-box',
              zIndex: isActive ? 1 : 'auto',
            }}
          />
        );
      }))}
    </div>
  );
};

export const EvidenceOverlay = (props) => {
  if (!EVIDENCE_HIGHLIGHTS_ENABLED || !props.showHighlights) return null;

  try {
    return (
      <EvidenceOverlayErrorBoundary>
        <EvidenceOverlayContent {...props} />
      </EvidenceOverlayErrorBoundary>
    );
  } catch {
    return null;
  }
};
