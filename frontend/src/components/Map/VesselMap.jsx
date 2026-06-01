import { MapContainer, TileLayer, useMap } from 'react-leaflet'
import VesselMarker from './VesselMarker'
import 'leaflet/dist/leaflet.css'
import './VesselMap.css'

function MapBounds({ vessels }) {
  // Could auto-fit bounds to vessels if desired
  return null
}

export default function VesselMap({ vessels = [], selectedVessel, onVesselClick }) {
  return (
    <MapContainer
      center={[20, 0]}
      zoom={3}
      minZoom={2}
      maxZoom={18}
      zoomControl={true}
      className="vessel-map"
      worldCopyJump={true}
    >
      <TileLayer
        url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/">CARTO</a>'
        subdomains="abcd"
        maxZoom={20}
      />

      {vessels.map((vessel) => (
        <VesselMarker
          key={vessel.id}
          vessel={vessel}
          isSelected={selectedVessel?.id === vessel.id}
          onClick={onVesselClick}
        />
      ))}

      <MapBounds vessels={vessels} />
    </MapContainer>
  )
}
