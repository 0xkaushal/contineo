import { BaseEdge, EdgeLabelRenderer, getBezierPath } from '@xyflow/react';
import type { EdgeProps } from '@xyflow/react';

interface OffsetEdgeData {
  sourceOffset?: number;
  targetOffset?: number;
  callCount?: number;
}

export function OffsetBezierEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  style,
  markerEnd,
  animated,
  data,
}: EdgeProps) {
  const d = (data ?? {}) as OffsetEdgeData;
  const sOffset = d.sourceOffset ?? 0;
  const tOffset = d.targetOffset ?? 0;

  // Shift the Y coordinates so edges fan out from their source/target nodes
  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY: sourceY + sOffset,
    sourcePosition,
    targetX,
    targetY: targetY + tOffset,
    targetPosition,
    // Increase curvature so paths arc wider and don't overlap
    curvature: 0.35,
  });

  return (
    <>
      <BaseEdge
        id={id}
        path={edgePath}
        style={style}
        markerEnd={markerEnd}
        className={animated ? 'animated' : ''}
      />
      {d.callCount !== undefined && d.callCount > 0 && (
        <EdgeLabelRenderer>
          <div
            style={{
              position: 'absolute',
              transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
              pointerEvents: 'none',
              fontSize: 10,
              padding: '2px 5px',
              borderRadius: 4,
              background: 'var(--bg-2)',
              color: 'var(--text-muted)',
              border: '1px solid var(--border)',
              whiteSpace: 'nowrap',
            }}
            className="nodrag nopan"
          >
            {d.callCount}
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  );
}
