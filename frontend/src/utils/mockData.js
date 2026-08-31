/* ═══════════════════════════════════════════════════════════════
   Mock Data — 50 vessels across major shipping lanes
   Allows the frontend to render standalone without a backend.
   ═══════════════════════════════════════════════════════════════ */

const FLAGS = [
  { code: 'PA', name: 'Panama', emoji: '🇵🇦' },
  { code: 'LR', name: 'Liberia', emoji: '🇱🇷' },
  { code: 'MH', name: 'Marshall Islands', emoji: '🇲🇭' },
  { code: 'HK', name: 'Hong Kong', emoji: '🇭🇰' },
  { code: 'SG', name: 'Singapore', emoji: '🇸🇬' },
  { code: 'MT', name: 'Malta', emoji: '🇲🇹' },
  { code: 'BS', name: 'Bahamas', emoji: '🇧🇸' },
  { code: 'CN', name: 'China', emoji: '🇨🇳' },
  { code: 'GR', name: 'Greece', emoji: '🇬🇷' },
  { code: 'NO', name: 'Norway', emoji: '🇳🇴' },
  { code: 'GB', name: 'United Kingdom', emoji: '🇬🇧' },
  { code: 'JP', name: 'Japan', emoji: '🇯🇵' },
  { code: 'KR', name: 'South Korea', emoji: '🇰🇷' },
  { code: 'RU', name: 'Russia', emoji: '🇷🇺' },
  { code: 'IR', name: 'Iran', emoji: '🇮🇷' },
  { code: 'CY', name: 'Cyprus', emoji: '🇨🇾' },
]

const VESSEL_NAMES = [
  'MSC Gülsün', 'Ever Given', 'Maersk Eindhoven', 'CMA CGM Marco Polo',
  'CSCL Globe', 'Berge Stahl', 'Olympic Lion', 'Stena Bulk',
  'Pacific Voyager', 'Atlantic Guardian', 'Nordic Spirit', 'Eastern Phoenix',
  'Silver Dawn', 'Golden Horizon', 'Emerald Star', 'Crystal Seas',
  'Iron Gate', 'Storm Petrel', 'Ocean Titan', 'Neptune Grace',
  'Arctic Pearl', 'Coral Enterprise', 'Jade Harmony', 'Blue Marlin',
  'Red Dragon', 'White Cliffs', 'Black Pearl', 'Grey Fox',
  'Green Spirit', 'Amber Wave', 'Crimson Tide', 'Sapphire Coast',
  'Diamond Ray', 'Ruby Fortune', 'Opal Venture', 'Topaz Light',
  'Shadow Carrier', 'Night Hawk', 'Dawn Treader', 'Sun Chaser',
  'Star Phoenix', 'Moon Rise', 'Sky Bridge', 'Wind Runner',
  'Thunder Bay', 'Lightning Bolt', 'Frost Giant', 'Fire Storm',
  'Dark Horizon', 'Bright Future',
]

const TYPES = ['cargo', 'cargo', 'cargo', 'tanker', 'tanker', 'fishing', 'passenger', 'other']

// Major shipping lane coordinates
const SHIPPING_POSITIONS = [
  // Strait of Malacca
  { lat: 1.3, lon: 103.8 }, { lat: 2.5, lon: 101.5 }, { lat: 3.8, lon: 100.2 },
  // South China Sea
  { lat: 10.2, lon: 114.5 }, { lat: 15.8, lon: 112.3 }, { lat: 21.0, lon: 115.0 },
  // Suez approach
  { lat: 29.9, lon: 32.5 }, { lat: 27.5, lon: 34.0 }, { lat: 13.0, lon: 43.5 },
  // Gulf of Aden
  { lat: 12.5, lon: 45.0 }, { lat: 11.8, lon: 50.2 },
  // English Channel
  { lat: 50.8, lon: 1.2 }, { lat: 51.0, lon: -1.0 },
  // Mediterranean
  { lat: 36.0, lon: 14.5 }, { lat: 37.5, lon: 5.0 }, { lat: 35.8, lon: -5.5 },
  // Panama Canal approach
  { lat: 9.0, lon: -79.5 }, { lat: 8.5, lon: -80.2 },
  // Caribbean
  { lat: 18.5, lon: -66.0 }, { lat: 25.0, lon: -80.0 },
  // US East Coast
  { lat: 40.5, lon: -73.8 }, { lat: 36.8, lon: -75.5 },
  // North Sea
  { lat: 53.5, lon: 4.5 }, { lat: 57.0, lon: 2.0 },
  // Persian Gulf
  { lat: 26.5, lon: 56.2 }, { lat: 26.0, lon: 51.5 }, { lat: 29.0, lon: 48.5 },
  // Indian Ocean
  { lat: -6.0, lon: 71.5 }, { lat: 5.0, lon: 80.0 },
  // East Africa
  { lat: -4.0, lon: 39.5 }, { lat: -6.8, lon: 39.2 },
  // West Africa
  { lat: 6.5, lon: 3.4 }, { lat: 4.0, lon: 7.0 },
  // South America
  { lat: -23.0, lon: -43.0 }, { lat: -34.5, lon: -58.5 },
  // Cape of Good Hope
  { lat: -34.0, lon: 18.5 }, { lat: -33.5, lon: 25.0 },
  // Australia
  { lat: -33.8, lon: 151.2 }, { lat: -37.8, lon: 144.9 },
  // Japan / Korea
  { lat: 35.4, lon: 139.7 }, { lat: 35.0, lon: 129.0 },
  // Taiwan Strait
  { lat: 24.5, lon: 118.5 },
  // Bay of Bengal
  { lat: 13.0, lon: 80.3 }, { lat: 22.3, lon: 91.8 },
  // Baltic
  { lat: 59.4, lon: 24.7 }, { lat: 55.7, lon: 12.6 },
  // US West Coast
  { lat: 33.7, lon: -118.2 }, { lat: 37.8, lon: -122.4 },
  // Alaska
  { lat: 57.0, lon: -135.3 },
  // Arctic route
  { lat: 71.0, lon: 25.0 },
]

function randomBetween(min, max) {
  return Math.random() * (max - min) + min
}

function generateIMO() {
  return `${Math.floor(1000000 + Math.random() * 8999999)}`
}

function generateMMSI() {
  return `${Math.floor(200000000 + Math.random() * 799999999)}`
}

function generateCallSign() {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
  const nums = '0123456789'
  return (
    chars[Math.floor(Math.random() * 26)] +
    chars[Math.floor(Math.random() * 26)] +
    nums[Math.floor(Math.random() * 10)] +
    chars[Math.floor(Math.random() * 26)] +
    nums[Math.floor(Math.random() * 10)]
  )
}

export const MOCK_VESSELS = Array.from({ length: 50 }, (_, i) => {
  const type = TYPES[i % TYPES.length]
  const flag = FLAGS[i % FLAGS.length]
  const pos = SHIPPING_POSITIONS[i % SHIPPING_POSITIONS.length]
  const riskScore = i < 5
    ? Math.floor(randomBetween(65, 95))   // first 5 are high-risk for demo
    : i < 15
    ? Math.floor(randomBetween(35, 64))   // next 10 medium
    : Math.floor(randomBetween(5, 34))    // rest are low

  const heading = Math.floor(randomBetween(0, 359))
  const speed = type === 'fishing'
    ? randomBetween(2, 8)
    : type === 'passenger'
    ? randomBetween(15, 25)
    : randomBetween(8, 18)

  return {
    id: String(i + 1),
    imo: generateIMO(),
    mmsi: generateMMSI(),
    callSign: generateCallSign(),
    name: VESSEL_NAMES[i],
    type,
    flag,
    riskScore,
    riskFactors: [],
    position: {
      lat: pos.lat + randomBetween(-0.5, 0.5),
      lon: pos.lon + randomBetween(-0.5, 0.5),
    },
    heading,
    speed: parseFloat(speed.toFixed(1)),
    grossTonnage: Math.floor(randomBetween(5000, 200000)),
    deadweight: Math.floor(randomBetween(8000, 320000)),
    yearBuilt: Math.floor(randomBetween(1998, 2024)),
    length: Math.floor(randomBetween(100, 400)),
    beam: Math.floor(randomBetween(20, 62)),
    lastSeen: new Date(Date.now() - Math.floor(randomBetween(0, 3600000))).toISOString(),
    destination: [
      'Singapore', 'Rotterdam', 'Shanghai', 'Dubai', 'Houston',
      'Busan', 'Hamburg', 'Antwerp', 'Los Angeles', 'Yokohama',
      'Piraeus', 'Santos', 'Mumbai', 'Lagos', 'Durban',
    ][i % 15],
    eta: new Date(Date.now() + Math.floor(randomBetween(86400000, 864000000))).toISOString(),
    ownership: {
      registeredOwner: [
        'Neptune Shipping Ltd', 'Atlas Maritime Corp', 'Oceanus Holdings',
        'Pacific Ventures LLC', 'Golden Anchor Inc', 'Baltic Trade SA',
        'Meridian Lines', 'Horizon Marine Group',
      ][i % 8],
      beneficialOwner: i < 5
        ? 'Disputed — under investigation'
        : [
            'Maersk Group', 'MSC Mediterranean', 'CMA CGM',
            'COSCO Shipping', 'Hapag-Lloyd', 'ONE Ocean Network',
            'Evergreen Marine', 'Yang Ming Marine',
          ][i % 8],
      operator: [
        'OceanLink Management', 'SeaBridge Operations',
        'WavePoint Shipping', 'Anchor Global Services',
      ][i % 4],
      flagHistory: [
        { flag: FLAGS[(i + 1) % FLAGS.length], from: '2015', to: '2020' },
        { flag, from: '2020', to: 'present' },
      ],
    },
    sanctions: i < 5
      ? {
          matched: true,
          lists: [
            { name: 'OFAC SDN', matchType: 'Direct', confidence: 0.92 },
            ...(i < 3 ? [{ name: 'EU Sanctions', matchType: 'Associated Entity', confidence: 0.78 }] : []),
          ],
        }
      : { matched: false, lists: [] },
  }
})

export default MOCK_VESSELS
