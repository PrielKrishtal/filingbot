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
    SKIPPED = "SKIPPED"
    DONE = "DONE" #TODO: remove this from FSM

    

class TransactionCode(Enum):
    P = "P"  # open market or private Purchase
    S = "S"  # open market or private Sale
    V = "V"  # transaction voluntarily reported earlier than required
    A = "A"  # grant/Award/other acquisition (e.g. RSU grant)
    D = "D"  # disposition to the issuer (Rule 16b-3(e))
    F = "F"  # shares withheld/sold to pay taxes on a Filer's vesting (tax withholding)
    I = "I"  # discretionary transaction under Rule 16b-3(f)
    M = "M"  # exercise/conversion of a derivative security (e.g. stock option exercise)
    C = "C"  # conversion of a derivative security
    E = "E"  # expiration of a short derivative position
    H = "H"  # expiration or cancellation of a long derivative position
    O = "O"  # exercise of an out-of-the-money derivative
    X = "X"  # exercise of an in-the-money or at-the-money derivative
    G = "G"  # Gift
    L = "L"  # small acquisition under Rule 16a-6
    W = "W"  # acquisition or disposition by will or the laws of descent
    Z = "Z"  # deposit into or withdrawal from a voting trust
    J = "J"  # other acquisition or disposition (described in a footnote)
    K = "K"  # transaction in an equity swap or similar instrument
    U = "U"  # disposition from a tender of shares in a change of control
    
class TransactionClassification(Enum):
    voluntary_purchase = "voluntary_purchase"
    option_exercise = "option_exercise"
    planned_sale = "planned_sale"
    tax_disposition = "tax_disposition"
    gift = "gift"
    other = "other"