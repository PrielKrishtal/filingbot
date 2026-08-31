from lxml import etree
from datetime import datetime
from core.schemas.filing import InsiderFiling
from ingestion.rate_limiter import throttled_get
from ingestion.form4_parser import parse_form4
from core.config import settings

RSS_URL = (
    "https://www.sec.gov/cgi-bin/browse-edgar"
    "?action=getcurrent&type=4&dateb=&owner=include&count=40&search_text=&output=atom"
)

EDGAR_HEADERS = {"User-Agent": settings.sec_user_agent}


async def poll_new_filings(since: datetime) -> list[InsiderFiling]:
    response = await throttled_get(url=RSS_URL, headers=EDGAR_HEADERS)

    if response.status_code != 200:
        raise RuntimeError(f"EDGAR RSS fetch failed: {response.status_code}")

    root = etree.fromstring(response.content)

    entries = root.xpath("//entry[category/@term='4']") #list of <entry> tags — one per filing. 

    
    seen: dict[str, etree._Element] = {} # dedupe entries within this single feed fetch
    for entry in entries:
                             #[0] for xml match and [-1] for accession 
        accession = entry.xpath("id/text()")[0].split("=")[-1] 
        seen[accession] = entry

    filings: list[InsiderFiling] = [] 

    for accession, entry in seen.items():
        filing_date_str = entry.xpath("updated/text()")[0]
        filing_date = datetime.fromisoformat(filing_date_str).replace(tzinfo=None)

        if filing_date <= since: # skip filings already processed in a previous poll
            continue

        link_href = entry.xpath("link/@href")[0]
        cik = link_href.split("/data/")[1].split("/")[0]
        accession_no_dashes = accession.replace("-", "")

        xml_url = (
            f"https://www.sec.gov/Archives/edgar/data/"
            f"{cik}/{accession_no_dashes}/{accession}.xml"
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
