from enum import Enum

class SignalStrength(Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    NOISE = "NOISE"


class PipelineStatus(Enum):
    INGESTED = "INGESTED"
    CLASSIFIED = "CLASSIFIED"
    ENRICHED = "ENRICHED"
    NOTIFIED = "NOTIFIED"
    DONE = "DONE"
    

class TransactionCode(Enum):
    P = "P"                   
    S = "S"                                       
    M = "M"                             
    A = "A"                                 
    G = "G"
    
class TransactionClassification(Enum):
    voluntary_purchase = "voluntary_purchase"
    option_exercise = "option_exercise"
    planned_sale = "planned_sale"
    tax_disposition = "tax_disposition"
    gift = "gift"
    other = "other"