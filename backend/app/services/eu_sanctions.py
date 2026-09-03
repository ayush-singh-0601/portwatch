"""
EU / UN / OFSI sanctions list parsers.

Provides download and parsing for:
- EU consolidated financial sanctions (FISMA XML)
- UN Security Council consolidated list
- UK OFSI consolidated list

All parsers normalize entries into the same dict format used
by :mod:`app.services.ofac_parser` for unified screening.
"""

import logging
import re
import unicodedata
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

# ── Download URLs ──────────────────────────────────────────────────
EU_SANCTIONS_URL = (
    "https://webgate.ec.europa.eu/fsd/fsf/public/files/"
    "xmlFullSanctionsList_1_1/content?token=dG9rZW4tMjAxNw"
)
UN_SANCTIONS_URL = (
    "https://scsanctions.un.org/resources/xml/en/consolidated.xml"
)
OFSI_SANCTIONS_URL = (
    "https://assets.publishing.service.gov.uk/media/"
    "ConsolidatedList.xml"
)


def _normalize(text: str | None) -> str:
    """Normalize unicode and collapse whitespace."""
    if not text:
        return ""
    return " ".join(unicodedata.normalize("NFKD", text).split())


def _find_text(element, tag: str) -> str:
    """Safely extract text from a child element."""
    child = element.find(tag)
    if child is not None and child.text:
        return _normalize(child.text)
    return ""


# ═══════════════════════════════════════════════════════════════════
# EU Financial Sanctions (FISMA)
# ═══════════════════════════════════════════════════════════════════

async def download_eu_sanctions(output_dir: Path) -> Path:
    """Download the EU consolidated sanctions XML."""
    output_dir.mkdir(parents=True, exist_ok=True)
    file_path = output_dir / "eu_sanctions.xml"

    logger.info("Downloading EU sanctions list")
    async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
        resp = await client.get(EU_SANCTIONS_URL)
        resp.raise_for_status()
        file_path.write_bytes(resp.content)

    logger.info("Downloaded EU sanctions: %.1f KB", len(resp.content) / 1024)
    return file_path


def parse_eu_sanctions(xml_path: Path) -> list[dict]:
    """Parse the EU consolidated sanctions XML.

    Returns:
        List of dicts matching the SanctionsEntry model schema.
    """
    from xml.etree.ElementTree import iterparse

    entries = []
    for event, elem in iterparse(str(xml_path), events=("end",)):
        tag = re.sub(r"\{.*\}", "", elem.tag)

        if tag == "sanctionEntity":
            names = []
            entity_type = "organization"

            # Extract names
            for name_elem in elem.iter():
                name_tag = re.sub(r"\{.*\}", "", name_elem.tag)
                if name_tag in ("wholeName", "lastName"):
                    if name_elem.text:
                        names.append(_normalize(name_elem.text))
                elif name_tag == "subjectType":
                    if name_elem.text:
                        st = name_elem.text.lower()
                        if "person" in st:
                            entity_type = "individual"
                        elif "enterprise" in st or "entity" in st:
                            entity_type = "organization"

            # Extract programme / regime
            programme = ""
            for prog_elem in elem.iter():
                prog_tag = re.sub(r"\{.*\}", "", prog_elem.tag)
                if prog_tag == "programme" and prog_elem.text:
                    programme = _normalize(prog_elem.text)
                    break

            # Extract identifiers (look for IMO)
            imo_number = None
            for id_elem in elem.iter():
                id_tag = re.sub(r"\{.*\}", "", id_elem.tag)
                if id_tag == "identification":
                    number = _find_text(id_elem, "number") or _find_text(id_elem, "Number")
                    id_type = _find_text(id_elem, "identificationTypeDescription")
                    if "imo" in id_type.lower() and number:
                        imo_number = number

            primary_name = names[0] if names else ""
            aliases = names[1:] if len(names) > 1 else []

            if primary_name:
                entries.append({
                    "source": "EU",
                    "entity_name": primary_name,
                    "entity_type": entity_type,
                    "program": programme,
                    "list_id": None,
                    "aliases": aliases or None,
                    "imo_number": imo_number,
                })

            elem.clear()

    logger.info("Parsed %d EU sanctions entries", len(entries))
    return entries


# ═══════════════════════════════════════════════════════════════════
# UN Security Council Consolidated List
# ═══════════════════════════════════════════════════════════════════

async def download_un_sanctions(output_dir: Path) -> Path:
    """Download the UN Security Council consolidated list XML."""
    output_dir.mkdir(parents=True, exist_ok=True)
    file_path = output_dir / "un_sanctions.xml"

    logger.info("Downloading UN Security Council sanctions list")
    async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
        resp = await client.get(UN_SANCTIONS_URL)
        resp.raise_for_status()
        file_path.write_bytes(resp.content)

    logger.info("Downloaded UN sanctions: %.1f KB", len(resp.content) / 1024)
    return file_path


def parse_un_sanctions(xml_path: Path) -> list[dict]:
    """Parse the UN Security Council consolidated sanctions XML."""
    from xml.etree.ElementTree import iterparse

    entries = []
    for event, elem in iterparse(str(xml_path), events=("end",)):
        tag = re.sub(r"\{.*\}", "", elem.tag)

        if tag == "INDIVIDUAL" or tag == "ENTITY":
            entity_type = "individual" if tag == "INDIVIDUAL" else "organization"

            # Names
            first = _find_text(elem, "FIRST_NAME")
            second = _find_text(elem, "SECOND_NAME")
            third = _find_text(elem, "THIRD_NAME")
            name_parts = [p for p in [first, second, third] if p]
            primary_name = " ".join(name_parts)

            # Aliases
            aliases = []
            for alias_elem in elem.iter():
                alias_tag = re.sub(r"\{.*\}", "", alias_elem.tag)
                if alias_tag == "ALIAS_NAME" and alias_elem.text:
                    aliases.append(_normalize(alias_elem.text))

            # Reference number
            list_id = _find_text(elem, "REFERENCE_NUMBER") or _find_text(elem, "DATAID")

            # UN list type
            un_list = _find_text(elem, "UN_LIST_TYPE")

            if primary_name:
                entries.append({
                    "source": "UN",
                    "entity_name": primary_name,
                    "entity_type": entity_type,
                    "program": un_list,
                    "list_id": list_id,
                    "aliases": aliases or None,
                    "imo_number": None,
                })

            elem.clear()

    logger.info("Parsed %d UN sanctions entries", len(entries))
    return entries


# ═══════════════════════════════════════════════════════════════════
# UK OFSI Consolidated List
# ═══════════════════════════════════════════════════════════════════

async def download_ofsi_sanctions(output_dir: Path) -> Path:
    """Download the UK OFSI consolidated sanctions list XML."""
    output_dir.mkdir(parents=True, exist_ok=True)
    file_path = output_dir / "ofsi_sanctions.xml"

    logger.info("Downloading OFSI sanctions list")
    async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
        resp = await client.get(OFSI_SANCTIONS_URL)
        resp.raise_for_status()
        file_path.write_bytes(resp.content)

    logger.info("Downloaded OFSI sanctions: %.1f KB", len(resp.content) / 1024)
    return file_path


def parse_ofsi_sanctions(xml_path: Path) -> list[dict]:
    """Parse the UK OFSI consolidated sanctions XML."""
    from xml.etree.ElementTree import iterparse

    entries = []
    for event, elem in iterparse(str(xml_path), events=("end",)):
        tag = re.sub(r"\{.*\}", "", elem.tag)

        if tag == "FinancialSanctionsTarget":
            names = []
            entity_type = "organization"
            group_type = _find_text(elem, "GroupTypeDescription")
            if "individual" in group_type.lower():
                entity_type = "individual"

            # Collect all name parts
            name_parts = []
            for name_elem in elem.iter():
                name_tag = re.sub(r"\{.*\}", "", name_elem.tag)
                if name_tag.lower() in ("fullname", "entityname", "name6", "name1", "name2", "name3", "name4", "name5"):
                    if name_elem.text and name_elem.text.strip():
                        name_parts.append(_normalize(name_elem.text))

            full_combined = " ".join([p for p in name_parts if p]).strip()
            if full_combined:
                names.append(full_combined)
            for p in name_parts:
                if p and p not in names:
                    names.append(p)

            # Regime
            regime = _find_text(elem, "RegimeName")

            # Reference
            list_id = _find_text(elem, "UniqueID") or _find_text(elem, "GroupID")

            primary_name = names[0] if names else ""
            aliases = names[1:] if len(names) > 1 else []

            if primary_name:
                entries.append({
                    "source": "OFSI",
                    "entity_name": primary_name,
                    "entity_type": entity_type,
                    "program": regime,
                    "list_id": list_id,
                    "aliases": aliases or None,
                    "imo_number": None,
                })

            elem.clear()

    logger.info("Parsed %d OFSI sanctions entries", len(entries))
    return entries
