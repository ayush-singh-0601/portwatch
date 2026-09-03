"""
OFAC SDN Enhanced XML parser.

Downloads and parses the OFAC Specially Designated Nationals (SDN) list
from the US Treasury. Extracts vessel entries, individuals, and entities
for sanctions screening.

Data source:
    https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/SDN_ENHANCED.XML
"""

import logging
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from xml.etree.ElementTree import iterparse

import httpx

logger = logging.getLogger(__name__)

OFAC_SDN_URL = (
    "https://sanctionslistservice.ofac.treas.gov/"
    "api/PublicationPreview/exports/SDN_ENHANCED.XML"
)

# XML namespace used in the enhanced SDN file
NS = {"ns": "https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/ENHANCED"}


@dataclass
class SDNEntity:
    """A parsed entity from the OFAC SDN list."""

    source_id: str = ""
    entity_name: str = ""
    entity_type: str = ""  # "vessel", "individual", "organization"
    program: str = ""
    aliases: list[str] = field(default_factory=list)
    imo_number: str | None = None
    mmsi: str | None = None
    call_sign: str | None = None
    flag: str | None = None
    vessel_type: str | None = None
    tonnage: str | None = None
    remarks: str = ""


def normalize_text(text: str | None) -> str:
    """Normalize unicode text and whitespace for consistent matching."""
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text)
    return " ".join(text.split())


async def download_sdn_xml(output_path: Path) -> Path:
    """Download the OFAC SDN Enhanced XML file.

    Args:
        output_path: Directory to save the downloaded XML file.

    Returns:
        Path to the downloaded XML file.
    """
    output_path.mkdir(parents=True, exist_ok=True)
    file_path = output_path / "SDN_ENHANCED.XML"

    logger.info("Downloading OFAC SDN Enhanced XML from %s", OFAC_SDN_URL)

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.get(OFAC_SDN_URL)
        response.raise_for_status()

        file_path.write_bytes(response.content)
        size_mb = len(response.content) / (1024 * 1024)
        logger.info("Downloaded SDN XML: %.1f MB -> %s", size_mb, file_path)

    return file_path


def _strip_ns(tag: str) -> str:
    """Strip XML namespace prefix from a tag name."""
    return re.sub(r"\{.*\}", "", tag)


def parse_sdn_xml(xml_path: Path) -> list[SDNEntity]:
    """Parse the OFAC SDN Enhanced XML file into structured entities.

    Uses iterparse for memory efficiency on large files.

    Args:
        xml_path: Path to the SDN_ENHANCED.XML file.

    Returns:
        List of parsed SDNEntity objects.
    """
    entities: list[SDNEntity] = []
    current_entity: SDNEntity | None = None
    current_path: list[str] = []

    logger.info("Parsing SDN XML: %s", xml_path)

    for event, elem in iterparse(str(xml_path), events=("start", "end")):
        tag = _strip_ns(elem.tag)

        if event == "start":
            current_path.append(tag)

            if tag == "sdnEntry":
                current_entity = SDNEntity()

        elif event == "end":
            if current_entity is not None:
                text = normalize_text(elem.text)

                # Core identity fields
                if tag == "uid":
                    current_entity.source_id = text
                elif tag == "lastName" or tag == "sdnName":
                    if not current_entity.entity_name:
                        current_entity.entity_name = text
                elif tag == "firstName":
                    if text and current_entity.entity_name:
                        current_entity.entity_name = f"{text} {current_entity.entity_name}"
                elif tag == "sdnType":
                    sdn_type = text.lower()
                    if "vessel" in sdn_type:
                        current_entity.entity_type = "vessel"
                    elif "individual" in sdn_type:
                        current_entity.entity_type = "individual"
                    else:
                        current_entity.entity_type = "organization"
                elif tag == "programList":
                    programs = [
                        normalize_text(p.text)
                        for p in elem
                        if _strip_ns(p.tag) == "program" and p.text
                    ]
                    if not programs:
                        programs = [
                            normalize_text(p.text)
                            for p in elem
                            if p.text
                        ]
                    current_entity.program = "; ".join([p for p in programs if p])

                # Aliases
                elif tag == "aka" or tag == "akaName":
                    if text:
                        current_entity.aliases.append(text)

                # Vessel-specific ID documents
                elif tag == "idType":
                    # Store temporarily — pair with idNumber
                    elem.set("_parsed_type", text.lower())
                elif tag == "idNumber":
                    parent_path = "/".join(current_path[:-1])
                    # Try to find the idType sibling
                    id_type = ""
                    parent = None
                    for ancestor_tag in reversed(current_path):
                        if ancestor_tag in ("id", "idList"):
                            break
                    # Check if parent element has parsed type
                    if elem.getparent is not None:
                        pass  # iterparse doesn't give parent easily

                # Vessel details from remarks or vessel info sections
                elif tag == "vesselInfo":
                    pass  # Container element
                elif tag == "callSign":
                    current_entity.call_sign = text
                elif tag == "vesselType":
                    current_entity.vessel_type = text
                elif tag == "tonnage":
                    current_entity.tonnage = text
                elif tag == "vesselFlag":
                    current_entity.flag = text

                elif tag == "remarks":
                    current_entity.remarks = text
                    # Extract IMO from remarks if present
                    imo_match = re.search(r"IMO\s*(\d{7})", text, re.IGNORECASE)
                    if imo_match:
                        current_entity.imo_number = imo_match.group(1)

                # End of entity
                if tag == "sdnEntry":
                    if current_entity.entity_name:
                        entities.append(current_entity)
                    current_entity = None

            if current_path:
                current_path.pop()

            # Free memory for processed elements
            elem.clear()

    vessels = sum(1 for e in entities if e.entity_type == "vessel")
    individuals = sum(1 for e in entities if e.entity_type == "individual")
    orgs = sum(1 for e in entities if e.entity_type == "organization")

    logger.info(
        "Parsed %d SDN entities: %d vessels, %d individuals, %d organizations",
        len(entities), vessels, individuals, orgs,
    )

    return entities


def sdn_entities_to_dicts(entities: list[SDNEntity]) -> list[dict]:
    """Convert SDNEntity objects to dicts for database insertion.

    Returns:
        List of dicts matching the SanctionsEntry model schema.
    """
    results = []
    for entity in entities:
        results.append({
            "source": "OFAC",
            "entity_name": entity.entity_name,
            "entity_type": entity.entity_type,
            "program": entity.program,
            "list_id": entity.source_id,
            "aliases": entity.aliases if entity.aliases else None,
            "imo_number": entity.imo_number,
        })
    return results
