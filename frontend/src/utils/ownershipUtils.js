/**
 * Generate mock ownership graph from vessel mock data.
 */
export function buildMockGraph(vessel) {
  const hasOwnership = vessel?.ownership && (
    vessel.ownership.registeredOwner ||
    vessel.ownership.beneficialOwner ||
    vessel.ownership.operator
  )
  if (!hasOwnership) {
    return { nodes: [], links: [] }
  }

  const nodes = [
    {
      id: `vessel_${vessel.id}`,
      label: vessel.name,
      type: 'vessel',
      isCenter: true,
      flag: vessel.flag?.code,
    },
  ]
  const links = []

  if (vessel.ownership?.registeredOwner) {
    nodes.push({
      id: 'entity_1',
      label: vessel.ownership.registeredOwner,
      type: 'company',
      country: vessel.flag?.code,
    })
    links.push({ source: 'entity_1', target: `vessel_${vessel.id}`, relationship: 'registered_owner' })
  }

  if (vessel.ownership?.beneficialOwner) {
    nodes.push({
      id: 'entity_2',
      label: vessel.ownership.beneficialOwner,
      type: vessel.ownership.beneficialOwner.includes('Disputed') ? 'alert' : 'company',
      country: 'MH',
    })
    const targetId = nodes.some(n => n.id === 'entity_1') ? 'entity_1' : `vessel_${vessel.id}`
    links.push({ source: 'entity_2', target: targetId, relationship: 'beneficial_owner' })
  }

  if (vessel.ownership?.operator) {
    nodes.push({
      id: 'entity_3',
      label: vessel.ownership.operator,
      type: 'company',
      country: 'SG',
    })
    links.push({ source: 'entity_3', target: `vessel_${vessel.id}`, relationship: 'operator' })
  }

  // Add a shell company layer for high-risk vessels
  if (vessel.riskScore > 60 && nodes.some(n => n.id === 'entity_2')) {
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
    links.push(
      { source: 'entity_4', target: 'entity_2', relationship: 'shareholder' },
      { source: 'entity_5', target: 'entity_4', relationship: 'beneficial_owner' },
    )
  }

  return { nodes, links }
}

export function normalizeGraphData(vessel, graphData) {
  if (!graphData) return buildMockGraph(vessel)

  // If already in D3 format ({ nodes: [...], links: [...] })
  if (Array.isArray(graphData.nodes) && Array.isArray(graphData.links)) {
    const nodes = graphData.nodes.map(n => ({ ...n }))
    const nodeIds = new Set(nodes.map(n => n.id))
    const links = graphData.links
      .filter(l => {
        const s = typeof l.source === 'object' ? l.source?.id : l.source
        const t = typeof l.target === 'object' ? l.target?.id : l.target
        return nodeIds.has(s) && nodeIds.has(t)
      })
      .map(l => ({
        ...l,
        source: typeof l.source === 'object' ? l.source.id : l.source,
        target: typeof l.target === 'object' ? l.target.id : l.target,
      }))
    return { nodes, links }
  }

  // If backend API format ({ vessel_imo, nodes: [...], edges: [...] })
  if (Array.isArray(graphData.nodes) && Array.isArray(graphData.edges)) {
    if (graphData.nodes.length === 0) {
      return { nodes: [], links: [] }
    }

    const vesselId = `vessel_${vessel?.imo || vessel?.id}`
    const centerNode = {
      id: vesselId,
      label: vessel?.name || 'Vessel',
      type: 'vessel',
      isCenter: true,
      flag: vessel?.flag?.code,
    }

    const entityNodes = graphData.nodes.map(n => ({
      id: `entity_${n.id}`,
      label: n.name || `Entity ${n.id}`,
      type: n.entity_type || 'company',
      country: n.country,
    }))

    const nodes = [centerNode, ...entityNodes]
    const nodeIds = new Set(nodes.map(n => n.id))

    const links = graphData.edges
      .map(e => ({
        source: `entity_${e.source_entity_id}`,
        target: e.target_entity_id != null ? `entity_${e.target_entity_id}` : vesselId,
        relationship: e.relationship_type || 'owner',
      }))
      .filter(l => nodeIds.has(l.source) && nodeIds.has(l.target))

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
