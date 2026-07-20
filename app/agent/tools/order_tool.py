import re
import uuid


def generate_order_id(business_name: str) -> str:
    """Order IDs are generated per-conversation only — nothing is
    written to a database, so this is purely a customer-facing reference.
    """
    initials = "".join(word[0] for word in re.findall(r"[A-Za-z]+", business_name)[:3]).upper()
    initials = initials or "ORD"
    return f"{initials}-{uuid.uuid4().hex[:8].upper()}"
