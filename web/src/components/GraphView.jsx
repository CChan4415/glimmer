import { useEffect, useRef } from 'react'
import cytoscape from 'cytoscape'

const GROUP_COLORS = {
  center: '#4f6ef7',
  family: '#e8456b',
  colleague: '#12a5a0',
  friend: '#f2a33c',
  ungrouped: '#8a8fa3',
}

const GROUP_LABELS = {
  center: '我',
  family: '家人',
  colleague: '同事',
  friend: '朋友',
  ungrouped: '未分组',
}

export default function GraphView({ graphData, onNodeClick }) {
  const containerRef = useRef(null)
  const cyRef = useRef(null)

  useEffect(() => {
    if (!graphData || !containerRef.current) return

    const elements = [
      // Nodes
      ...graphData.nodes.map((n) => ({
        data: {
          id: n.id,
          label: n.name || n.display_name,
          group: n.group,
          degree: n.degree,
          isRegistered: n.is_registered,
          nodeData: n,
        },
      })),
      // Edges
      ...graphData.edges.map((e, i) => ({
        data: {
          id: `e${i}`,
          source: e.source,
          target: e.target,
        },
      })),
    ]

    const cy = cytoscape({
      container: containerRef.current,
      elements,
      style: [
        {
          selector: 'node',
          style: {
            'background-color': (ele) => GROUP_COLORS[ele.data('group')] || '#8a8fa3',
            label: 'data(label)',
            'text-valign': 'center',
            'text-halign': 'center',
            'font-size': 12,
            width: 28,
            height: 28,
            'border-width': 1,
            'border-color': '#fff',
          },
        },
        {
          selector: 'node[degree = 0]',
          style: {
            width: 44,
            height: 44,
            'font-size': 14,
            'text-wrap': 'wrap',
          },
        },
        {
          selector: 'node[degree = 2]',
          style: {
            'border-style': 'dashed',
            'border-width': 2,
            'border-color': GROUP_COLORS.center,
            opacity: 0.85,
          },
        },
        {
          selector: 'node[isRegistered = true]',
          style: {
            'border-color': '#22c55e',
            'border-width': 2,
          },
        },
        {
          selector: 'edge',
          style: {
            width: 1.5,
            'line-color': '#cbd5e1',
            'target-arrow-color': '#cbd5e1',
            'curve-style': 'bezier',
          },
        },
        {
          selector: 'edge[isSecondDegree = true]',
          style: {
            'line-style': 'dashed',
            'line-color': '#94a3b8',
          },
        },
      ],
      layout: {
        name: 'cose',
        animate: true,
        padding: 30,
        nodeRepulsion: 8000,
        idealEdgeLength: 90,
      },
      minZoom: 0.2,
      maxZoom: 3,
      wheelSensitivity: 0.3,
    })

    cy.on('tap', 'node', (evt) => {
      onNodeClick?.(evt.target.data('nodeData'))
    })

    cyRef.current = cy
    return () => {
      cy.destroy()
      cyRef.current = null
    }
  }, [graphData, onNodeClick])

  return <div ref={containerRef} className="graph-canvas" />
}
