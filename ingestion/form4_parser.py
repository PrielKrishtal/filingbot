from datetime import datetime
from decimal import Decimal

from lxml import etree

from core.schemas.enums import TransactionCode
from core.schemas.filing import InsiderFiling


def xpath_text(root, path: str) -> str:
    matches = root.xpath(path)
    if not matches:
        raise ValueError(f"missing field: {path}")
    return matches[0]

def xpath_text_optional(root, path: str, default: str = "") -> str:
    matches = root.xpath(path)
    if not matches:
        return default
    return matches[0]


def xpath_bool(root, path: str, default: bool = False) -> bool:
    matches = root.xpath(path)
    if not matches:
        return default
    return matches[0] in ("true", "1")



def resolve_insider_title(root) -> str:
    if xpath_bool(root, "//isOfficer/text()"):
        return xpath_text_optional(root, "//officerTitle/text()", "Officer")
    if xpath_bool(root, "//isDirector/text()"):
        return "Director"
    if xpath_bool(root, "//isTenPercentOwner/text()"):
        return "10% Owner"
    if xpath_bool(root, "//isOther/text()"):
        return xpath_text_optional(root, "//otherText/text()", "Other")
    return "Unknown"


def parse_form4(xml_content: str, accession_number: str, filing_date: datetime) -> InsiderFiling:
    root = etree.fromstring(xml_content.encode())

    return InsiderFiling(                                                                                                                                                                       
        accession_number= accession_number,                    
        filing_date = filing_date,                                                                                                                                                                
        issuer_name = xpath_text(root,"//issuerName/text()"),                                                                                                                                                                        
        issuer_ticker = xpath_text(root,"//issuerTradingSymbol/text()"),                                                                                                                                                                     
        issuer_cik = xpath_text(root,"//issuerCik/text()"),                                          
        insider_name = xpath_text(root,"//rptOwnerName/text()"),   
        insider_title = resolve_insider_title(root),
        transaction_code = TransactionCode(xpath_text(root,"//nonDerivativeTransaction/transactionCoding/transactionCode/text()")),
        shares_traded = Decimal(xpath_text(root,"//nonDerivativeTransaction/transactionAmounts/transactionShares/value/text()")),
        price_per_share = Decimal(xpath_text(root,"//nonDerivativeTransaction/transactionAmounts/transactionPricePerShare/value/text()")),
        total_value = Decimal(xpath_text(root,"//nonDerivativeTransaction/transactionAmounts/transactionShares/value/text()")) * Decimal(xpath_text(root,"//nonDerivativeTransaction/transactionAmounts/transactionPricePerShare/value/text()")),
        shares_owned_after = Decimal(xpath_text(root,"//nonDerivativeTransaction/postTransactionAmounts/sharesOwnedFollowingTransaction/value/text()")),
        is_10b5_1 = xpath_bool(root, "//aff10b5One/text()")
    )