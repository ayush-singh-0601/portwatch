# Changelog

All notable changes to PortWatch are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased]

### Fixed

#### Backend
- **`dark_detection.py` — `point_in_polygon` variable-scope bug**
  The ray-casting algorithm read `xints` before it was assigned when a
  horizontal polygon edge (`p1y == p2y`) was encountered, causing the
  crossing counter to toggle on stale data from the previous iteration.
  The second condition is now nested inside the `if p1y != p2y:` block,
  matching the canonical even-odd rule implementation.

- **`ais_ingestion.py` — self-referential `OwnershipEdge`**
  `populate_vessel_analytics` created `edge3` with
  `source_entity_id == target_entity_id` (both pointing to `ent_owner`),
  producing a circular self-loop that corrupted D3 graph rendering and
  the risk agent's `_check_identity_changes` traversal. The edge is now
  directed `ent_owner → ent_ubo` (`controlled_by`) to model the correct
  top-down ownership chain.

- **`enriched.py` — risk score selected by `id` instead of `calculated_at`**
  When multiple risk scores exist for a vessel the latest was previously
  chosen via `max(..., key=lambda x: x.id)`.  A manually triggered
  recalculation with a lower auto-increment id (e.g. from a restored backup)
  would be silently ignored.  The key is now `lambda x: x.calculated_at`.

#### Frontend
- **`useWebSocket.js` — full positions map replacement on every flush**
  The 2-second flush interval replaced the entire positions state object
  with only the vessels seen in the current batch.  Any vessel that sent
  no update in the last 2 s was dropped, causing map markers to flicker.
  Fixed by merging with the spread operator: `setPositions(prev => ({...prev, ...batch}))`.

- **`useWebSocket.js` — broken timestamp sort**
  The oversized-batch sort used `String.localeCompare` on ISO timestamp
  strings, which produces incorrect ordering for strings of different
  lengths.  Fixed with `new Date(b.ts) - new Date(a.ts)`.

- **`useVessels.js` — stale `selectedVessel` after live position update**
  Clicking a vessel stored a frozen object snapshot in `selectedVessel`.
  When the live WebSocket position arrived, `vessels` was updated but the
  detail panel continued to display the old heading/speed/position.
  A `useEffect` now re-derives `selectedVessel` from the `vessels` array
  whenever the array changes.

- **`VesselPanel.jsx` — `toLocaleDateString` drops `hour`/`minute` options**
  The ETA field used `toLocaleDateString` with `hour: '2-digit'` and
  `minute: '2-digit'` options that this method silently ignores.
  Replaced with `toLocaleString` which correctly formats date and time.

- **`VesselPanel.jsx` — `undefined°` / `undefined kn` for null speed/heading**
  Speed and heading fields rendered `"undefined kn"` / `"undefined°"` when
  the API returned `null`.  Added `!= null` guards that fall back to `'—'`.

- **`VesselMarker.jsx` — icon cache collision across risk bands**
  The icon cache was keyed by `type|heading|selected`, so two vessels of
  the same type and heading but different risk scores could share the same
  cached icon object, skipping any risk-band-specific styling.  The key
  now includes the risk band (`low|medium|high|critical`).

### Added

#### Backend
- `tests/test_dark_detection.py` — unit tests for `point_in_polygon` and
  `is_in_dead_zone`, including a direct regression for the
  `xints`-before-assignment bug.
- `tests/test_ais_ingestion.py` — regression test asserting that no
  self-loop `OwnershipEdge` is created during vessel analytics population.
- `tests/test_enriched.py` — tests for `_vessel_type_normalise`,
  `_resolve_ownership_from_edges`, and `calculated_at`-based score selection.

### Improved

#### Backend
- **`enriched.py` — extracted `_resolve_ownership_from_edges` helper**
  The inline edge-resolution loop is now a standalone, unit-testable
  module-level function.  Edges are grouped by vessel IMO before the
  helper is called, eliminating the per-edge dict lookup.

#### Frontend
- **`VesselPanel.jsx`** — tab bar now carries `role="tablist"`,
  `role="tab"`, and `aria-selected` for screen-reader compatibility.
- **`RiskBreakdown.jsx`** — risk score SVG ring has `role="img"` and a
  descriptive `aria-label` (e.g. "Risk score 72 out of 100 — HIGH").
- **`VesselSearch.jsx`** — results list has `role="listbox"` and each
  item has `role="option"` with `aria-selected` reflecting keyboard focus.
- **`Sidebar.jsx`** — risk range inputs clamp so `riskMin` cannot exceed
  `riskMax` and vice versa, preventing an inverted range that produces an
  empty vessel list with no user feedback.
