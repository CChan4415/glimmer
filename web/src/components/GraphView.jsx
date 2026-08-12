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

export default function GraphView({ graphData, secondDegreeNodes, onNodeClick }) {
  const containerRef = useRef(null)
  const cyRef = useRef(null)

  useEffect(() => {
    if (!graphData || !containerRef.current) return

    // Merge 1st-degree nodes + second-degree nodes into one element set
    const nodes = graphData.nodes.map((n) => ({
      data: {
        id: n.id,
        label: n.name || n.display_name,
        group: n.group,
        degree: n.degree,
        isRegistered: n.is_registered,
        nodeData: n,
      },
    }))

    const edges = graphData.edges.map((e, i) => ({
      data: {
        id: `e${i}`,
        source: e.source,
        target: e.target,
      },
    }))

    // Second-degree nodes drawn into graph (dashed border + dashed edge)
    const secondDegreeNodesList = secondDegreeNodes || []
    for (const n of secondDegreeNodesList) {
      const nodeId = `sd-${n.id}`
      // Avoid collision with existing node ids
      if (!nodes.some((x) => x.data.id === nodeId) && !nodes.some((x) => x.data.id === n.id)) {
        nodes.push({
          data: {
            id: nodeId,
            label: n.display_name,
            group: n.group || 'ungrouped',
            degree: 2,
            isRegistered: n.is_registered,
            nodeData: { ...n, is_second_degree: true },
          },
        })
      }
      if (n.source_contact_id) {
        const edgeId = `e2-${n.source_contact_id}-${n.id}`
        if (!edges.some((x) => x.data.id === edgeId)) {
          edges.push({
            data: {
              id: edgeId,
              source: n.source_contact_id,
              target: nodeId,
              isSecondDegree: true,
            },
          })
        }
      }
    }

    const cy = cytoscape({
      container: containerRef.current,
      elements: [...nodes, ...edges],
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
            'border-color': '#7c8aa5',
            opacity: 0.9,
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
            width: 1,
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
  }, [graphData, secondDegreeNodes, onNodeClick])

  return <div ref={containerRef} className="graph-canvas" />
}
