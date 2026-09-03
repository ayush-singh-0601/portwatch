/* ═══════════════════════════════════════════════════════════════
   OwnershipGraph — D3 force-directed graph for vessel ownership
   chains. Renders nodes (vessel, company, person) and directed
   edges with labels showing relationship types.
   ═══════════════════════════════════════════════════════════════ */

import { useEffect, useRef, useState } from 'react'
import * as d3 from 'd3'
import './OwnershipGraph.css'

/**
 * Generate mock ownership graph from vessel mock data.
 */
function buildMockGraph(vessel) {
  const nodes = [
    {
      id: `vessel_${vessel.id}`,
      label: vessel.name,
      type: 'vessel',
      isCenter: true,
      flag: vessel.flag?.code,
    },
    {
      id: 'entity_1',
      label: vessel.ownership?.registeredOwner || 'Unknown Owner',
      type: 'company',
      country: vessel.flag?.code,
    },
    {
      id: 'entity_2',
      label: vessel.ownership?.beneficialOwner || 'Unknown Beneficial',
      type: vessel.ownership?.beneficialOwner?.includes('Disputed') ? 'alert' : 'company',
      country: 'MH',
    },
    {
      id: 'entity_3',
      label: vessel.ownership?.operator || 'Unknown Operator',
      type: 'company',
      country: 'SG',
    },
  ]

  // Add a shell company layer for high-risk vessels
  if (vessel.riskScore > 60) {
    nodes.push({
      id: 'entity_4',
      label: 'Meridian Offshore Holdings',
      type: 'shell',
      country: 'PA',
    })
    nodes.push({
      id: 'entity_5',
      label: 'Unnamed Trust',
      type: 'trust',
      country: 'VG',
    })
  }

  const links = [
    { source: 'entity_1', target: `vessel_${vessel.id}`, relationship: 'registered_owner' },
    { source: 'entity_2', target: 'entity_1', relationship: 'beneficial_owner' },
    { source: 'entity_3', target: `vessel_${vessel.id}`, relationship: 'operator' },
  ]

  if (vessel.riskScore > 60) {
    links.push(
      { source: 'entity_4', target: 'entity_2', relationship: 'shareholder' },
      { source: 'entity_5', target: 'entity_4', relationship: 'beneficial_owner' },
    )
  }

  return { nodes, links }
}

function normalizeGraphData(vessel, graphData) {
  if (!graphData) return buildMockGraph(vessel)

  // If already in D3 format ({ nodes: [...], links: [...] })
  if (Array.isArray(graphData.nodes) && Array.isArray(graphData.links)) {
    return graphData
  }

  // If backend API format ({ vessel_imo, nodes: [...], edges: [...] })
  if (Array.isArray(graphData.nodes) && Array.isArray(graphData.edges)) {
    const vesselId = `vessel_${vessel.imo || vessel.id}`
    const centerNode = {
      id: vesselId,
      label: vessel.name,
      type: 'vessel',
      isCenter: true,
      flag: vessel.flag?.code,
    }

    const entityNodes = graphData.nodes.map(n => ({
      id: `entity_${n.id}`,
      label: n.name || `Entity ${n.id}`,
      type: n.entity_type || 'company',
      country: n.country,
    }))

    const nodes = [centerNode, ...entityNodes]

    const links = graphData.edges.map(e => ({
      source: `entity_${e.source_entity_id}`,
      target: e.vessel_imo ? vesselId : `entity_${e.target_entity_id}`,
      relationship: e.relationship_type || 'owner',
    }))

    // If no links connected to vessel directly and we have entity nodes, link the first
    if (entityNodes.length > 0 && !links.some(l => l.target === vesselId || l.source === vesselId)) {
      links.push({
        source: entityNodes[0].id,
        target: vesselId,
        relationship: 'owner',
      })
    }

    return { nodes, links }
  }

  return buildMockGraph(vessel)
}

const NODE_COLORS = {
  vessel: 'var(--accent)',
  company: 'hsl(220, 50%, 55%)',
  shell: 'var(--warning)',
  trust: 'hsl(280, 50%, 55%)',
  person: 'hsl(340, 50%, 55%)',
  alert: 'var(--danger)',
}

const NODE_ICONS = {
  vessel: '⚓',
  company: '🏢',
  shell: '🏝️',
  trust: '🔒',
  person: '👤',
  alert: '⚠️',
}

export default function OwnershipGraph({ vessel, graphData }) {
  const svgRef = useRef(null)
  const containerRef = useRef(null)
  const [dimensions, setDimensions] = useState({ width: 380, height: 350 })

  // Resize observer
  useEffect(() => {
    const container = containerRef.current
    if (!container) return
    let alive = true
    const obs = new ResizeObserver((entries) => {
      const { width, height } = entries[0].contentRect
      if (alive && width > 0 && height > 0) {
        setDimensions({ width, height: Math.max(height, 300) })
      }
    })
    obs.observe(container)
    return () => {
      alive = false
      obs.disconnect()
    }
  }, [])

  useEffect(() => {
    if (!vessel) return

    const data = normalizeGraphData(vessel, graphData)
    const { width, height } = dimensions
    if (!data.nodes || data.nodes.length === 0 || width <= 0 || height <= 0 || !svgRef.current) return

    // Clear stale fixed positions from any previous drag interactions
    data.nodes.forEach(d => { d.fx = null; d.fy = null })

    const svg = d3.select(svgRef.current)
    svg.selectAll('*').remove()

    // Create zoom group
    const g = svg.append('g')

    const zoom = d3.zoom()
      .scaleExtent([0.3, 3])
      .on('zoom', (event) => g.attr('transform', event.transform))
    svg.call(zoom)

    // Arrow marker
    svg.append('defs').append('marker')
      .attr('id', 'arrow')
      .attr('viewBox', '0 -5 10 10')
      .attr('refX', 32)
      .attr('refY', 0)
      .attr('markerWidth', 6)
      .attr('markerHeight', 6)
      .attr('orient', 'auto')
      .append('path')
      .attr('d', 'M0,-5L10,0L0,5')
      .attr('fill', 'rgba(255,255,255,0.3)')

    // Simulation
    const simulation = d3.forceSimulation(data.nodes)
      .force('link', d3.forceLink(data.links).id(d => d.id).distance(100))
      .force('charge', d3.forceManyBody().strength(-400))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide().radius(40))

    // Links
    const link = g.append('g')
      .selectAll('line')
      .data(data.links)
      .join('line')
      .attr('class', 'ownership-link')
      .attr('marker-end', 'url(#arrow)')

    // Link labels
    const linkLabel = g.append('g')
      .selectAll('text')
      .data(data.links)
      .join('text')
      .attr('class', 'ownership-link-label')
      .text(d => d.relationship?.replace(/_/g, ' ') || '')

    // Node groups
    const node = g.append('g')
      .selectAll('g')
      .data(data.nodes)
      .join('g')
      .attr('class', 'ownership-node')
      .call(d3.drag()
        .on('start', (event, d) => {
          if (!event.active) simulation.alphaTarget(0.3).restart()
          d.fx = d.x
          d.fy = d.y
        })
        .on('drag', (event, d) => {
          d.fx = event.x
          d.fy = event.y
        })
        .on('end', (event, d) => {
          if (!event.active) simulation.alphaTarget(0)
          d.fx = null
          d.fy = null
        }),
      )

    // Node circles
    node.append('circle')
      .attr('r', d => d.isCenter ? 24 : 18)
      .attr('fill', d => {
        const color = NODE_COLORS[d.type] || NODE_COLORS.company
        return color
      })
      .attr('fill-opacity', 0.15)
      .attr('stroke', d => NODE_COLORS[d.type] || NODE_COLORS.company)
      .attr('stroke-width', d => d.isCenter ? 2.5 : 1.5)
      .attr('class', d => d.type === 'alert' ? 'node-pulse' : '')

    // Node icons
    node.append('text')
      .attr('text-anchor', 'middle')
      .attr('dy', '0.35em')
      .attr('font-size', d => d.isCenter ? '16px' : '12px')
      .text(d => NODE_ICONS[d.type] || '🏢')

    // Node labels
    node.append('text')
      .attr('class', 'ownership-node-label')
      .attr('dy', d => d.isCenter ? 38 : 30)
      .attr('text-anchor', 'middle')
      .text(d => d.label?.length > 20 ? d.label.slice(0, 18) + '…' : d.label)

    // Country badge
    node.filter(d => d.country && !d.isCenter)
      .append('text')
      .attr('class', 'ownership-country')
      .attr('dy', d => d.isCenter ? 52 : 44)
      .attr('text-anchor', 'middle')
      .text(d => d.country)

    // Tick
    simulation.on('tick', () => {
      link
        .attr('x1', d => d.source.x)
        .attr('y1', d => d.source.y)
        .attr('x2', d => d.target.x)
        .attr('y2', d => d.target.y)

      linkLabel
        .attr('x', d => (d.source.x + d.target.x) / 2)
        .attr('y', d => (d.source.y + d.target.y) / 2)

      node.attr('transform', d => `translate(${d.x},${d.y})`)
    })

    // Cleanup
    return () => simulation.stop()
  }, [vessel, graphData, dimensions])

  const handleZoomIn = () => {
    if (svgRef.current) {
      d3.select(svgRef.current).transition().duration(250).call(d3.zoom().scaleBy, 1.3)
    }
  }

  const handleZoomOut = () => {
    if (svgRef.current) {
      d3.select(svgRef.current).transition().duration(250).call(d3.zoom().scaleBy, 0.7)
    }
  }

  const handleResetZoom = () => {
    if (svgRef.current) {
      d3.select(svgRef.current).transition().duration(350).call(d3.zoom().transform, d3.zoomIdentity)
    }
  }

  return (
    <div className="ownership-graph-container" ref={containerRef}>
      <div className="ownership-graph-header">
        <h4 className="ownership-graph-title">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="16" height="16">
            <circle cx="12" cy="5" r="3" />
            <circle cx="5" cy="19" r="3" />
            <circle cx="19" cy="19" r="3" />
            <path d="M12 8v3M8.5 16.5L10.5 13M15.5 16.5L13.5 13" />
          </svg>
          Ownership Network
        </h4>
        <div className="ownership-graph-controls">
          <button className="ownership-ctrl-btn" onClick={handleZoomIn} title="Zoom in" aria-label="Zoom in">+</button>
          <button className="ownership-ctrl-btn" onClick={handleZoomOut} title="Zoom out" aria-label="Zoom out">−</button>
          <button className="ownership-ctrl-btn" onClick={handleResetZoom} title="Reset zoom" aria-label="Reset zoom">⟲</button>
        </div>
      </div>
      <svg
        ref={svgRef}
        width={dimensions.width}
        height={dimensions.height}
        className="ownership-graph-svg"
      />
    </div>
  )
}
