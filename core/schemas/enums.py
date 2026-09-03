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
    P = "P"  # open market or private Purchase
    S = "S"  # open market or private Sale
    M = "M"  # exercise/conversion of a derivative security (e.g. stock option exercise)
    A = "A"  # grant/Award/other acquisition (e.g. RSU grant)
    G = "G"  # Gift
    F = "F"  # shares withheld/sold to pay taxes on a Filer's vesting (tax withholding)
    
class TransactionClassification(Enum):
    voluntary_purchase = "voluntary_purchase"
    option_exercise = "option_exercise"
    planned_sale = "planned_sale"
    tax_disposition = "tax_disposition"
    gift = "gift"
    other = "other"