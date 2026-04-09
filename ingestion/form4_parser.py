from lxml import etree                                                                                                                                                                      
from datetime import datetime                             
from decimal import Decimal                                                                                                                                                                 
from core.schemas.filing import InsiderFiling                                                                                                                                               
from core.schemas.enums import TransactionCode



def parse_form4(xml_content: str, accession_number: str, filing_date: datetime) -> InsiderFiling:
    root = etree.fromstring(xml_content.encode())

    return InsiderFiling(                                                                                                                                                                       
        accession_number= accession_number,                    
        filing_date = filing_date,                                                                                                                                                                
        issuer_name = root.xpath("//issuerName/text()")[0],                                                                                                                                                                        
        issuer_ticker = root.xpath("//issuerTradingSymbol/text()")[0],                                                                                                                                                                     
        issuer_cik = root.xpath("//issuerCik/text()")[0],                                          
        insider_name = root.xpath("//rptOwnerName/text()")[0],   
        insider_title = root.xpath("//officerTitle/text()")[0],   
        transaction_code = TransactionCode(root.xpath("//nonDerivativeTransaction/transactionCoding/transactionCode/text()")[0]),
        shares_traded = Decimal(root.xpath("//nonDerivativeTransaction/transactionAmounts/transactionShares/value/text()")[0]),
        price_per_share = Decimal(root.xpath("//nonDerivativeTransaction/transactionAmounts/transactionPricePerShare/value/text()")[0]),
        total_value = Decimal(root.xpath("//nonDerivativeTransaction/transactionAmounts/transactionShares/value/text()")[0]) * Decimal(root.xpath("//nonDerivativeTransaction/transactionAmounts/transactionPricePerShare/value/text()")[0]),
        shares_owned_after = Decimal(root.xpath("//nonDerivativeTransaction/postTransactionAmounts/sharesOwnedFollowingTransaction/value/text()")[0]),
        is_10b5_1 = root.xpath("//aff10b5One/text()")[0] in ("true", "1") if root.xpath("//aff10b5One/text()") else False
    )