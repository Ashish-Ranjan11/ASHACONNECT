
def beneficiary_public_id(beneficiary_id: int) -> str:
    """Human-readable permanent beneficiary reference."""
    return f"ASHA-BEN-{int(beneficiary_id):06d}"
