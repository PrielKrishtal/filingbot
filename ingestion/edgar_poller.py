from lxml import etree
from datetime import datetime, timezone
from core.schemas.filing import InsiderFiling
from ingestion.rate_limiter import throttled_get
from ingestion.form4_parser import parse_form4
from core.config import settings
from core.logging_config import get_logger
import logging

base_logger = get_logger("ingestion")

RSS_URL = (
    "https://www.sec.gov/cgi-bin/browse-edgar"
    "?action=getcurrent&type=4&dateb=&owner=include&count=40&search_text=&output=atom"
)

EDGAR_HEADERS = {"User-Agent": settings.sec_user_agent}
ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}


async def poll_new_filings(since: datetime) -> list[InsiderFiling]:

    response = await throttled_get(url=RSS_URL, headers=EDGAR_HEADERS)

    if response.status_code != 200:
        raise RuntimeError(f"EDGAR RSS fetch failed: {response.status_code}")

    root = etree.fromstring(response.content)

    entries = root.xpath("//atom:entry[atom:category/@term='4']", namespaces=ATOM_NS) #list of <entry> tags — one per filing.


    seen: dict[str, etree._Element] = {} # dedupe entries within this single feed fetch
    for entry in entries:
                             #[0] for xml match and [-1] for accession
        accession = entry.xpath("atom:id/text()", namespaces=ATOM_NS)[0].split("=")[-1]
        seen[accession] = entry

    filings: list[InsiderFiling] = []

    for accession, entry in seen.items():
        filing_date_str = entry.xpath("atom:updated/text()", namespaces=ATOM_NS)[0]
        filing_date = datetime.fromisoformat(filing_date_str).astimezone(timezone.utc)
        log = logging.LoggerAdapter(base_logger, extra={"correlation_id": accession})

        if filing_date <= since: # skip filings already processed in a previous poll
            continue

        link_href = entry.xpath("atom:link/@href", namespaces=ATOM_NS)[0]
        cik = link_href.split("/data/")[1].split("/")[0]
        accession_no_dashes = accession.replace("-", "")

        json_url = (
                    f"https://www.sec.gov/Archives/edgar/data/"
                    f"{cik}/{accession_no_dashes}/index.json"
                )

        json_response = await throttled_get(url=json_url, headers=EDGAR_HEADERS)
        if json_response.status_code != 200:
                log.warning("EDGAR Json Name file fetch failed")
                continue

        data = json_response.json()
        xml_filename = None
        for item  in data["directory"]["item"]:
            if item ["name"].endswith(".xml"):
                xml_filename = item ["name"] 

        if xml_filename is None:
            log.warning("no primary XML found in filing index")
            continue
             
                       

        xml_url = (
                    f"https://www.sec.gov/Archives/edgar/data/"
                    f"{cik}/{accession_no_dashes}/{xml_filename}"
                )

        xml_response = await throttled_get(url=xml_url, headers=EDGAR_HEADERS)
        if xml_response.status_code != 200:
            continue

        try:
            filing = parse_form4(xml_response.text, accession, filing_date)
            filings.append(filing)
        except Exception:
            continue

    return filings
