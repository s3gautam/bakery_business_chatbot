from dataclasses import dataclass

from app.store.menu_store import MenuStore
from app.store.models import BusinessConfig

CartLine = dict  # {"name": str, "unit_price": float, "quantity": int}


@dataclass(frozen=True)
class CartTotals:
    subtotal: float
    discount: float
    delivery_fee: float
    total: float
    qualifies_for_free_delivery: bool


def compute_totals(cart: list[CartLine], business_config: BusinessConfig) -> CartTotals:
    subtotal = sum(line["unit_price"] * line["quantity"] for line in cart)
    discount = round(subtotal * business_config.discount_percent / 100, 2)
    discounted_subtotal = subtotal - discount
    qualifies_for_free_delivery = discounted_subtotal >= business_config.min_cart_for_free_delivery
    delivery_fee = 0.0 if qualifies_for_free_delivery else business_config.delivery_fee
    total = round(discounted_subtotal + delivery_fee, 2)
    return CartTotals(
        subtotal=round(subtotal, 2),
        discount=discount,
        delivery_fee=delivery_fee,
        total=total,
        qualifies_for_free_delivery=qualifies_for_free_delivery,
    )


def format_cart(cart: list[CartLine], business_config: BusinessConfig) -> str:
    if not cart:
        return "EMPTY_CART"

    lines = [
        f"- {line['quantity']} x {line['name']} @ Rs. {line['unit_price']} = "
        f"Rs. {line['unit_price'] * line['quantity']}"
        for line in cart
    ]
    totals = compute_totals(cart, business_config)
    lines.append(f"Subtotal: Rs. {totals.subtotal}")
    lines.append(f"Discount ({business_config.discount_percent}%): -Rs. {totals.discount}")
    lines.append(f"Delivery fee: Rs. {totals.delivery_fee}")
    lines.append(f"Total: Rs. {totals.total}")
    return "\n".join(lines)


class CartTool:
    """Agent tool: add/remove/update/show/clear cart items and compute
    totals. Cart items are matched against the menu file only — never a
    hallucinated item.
    """

    def __init__(self, menu_store: MenuStore) -> None:
        self._menu_store = menu_store

    def add(self, cart: list[CartLine], item_query: str, quantity: int) -> tuple[list[CartLine], str]:
        if quantity <= 0:
            return cart, "Quantity must be at least 1."

        matches = self._menu_store.search(item_query)
        if not matches:
            return cart, f"NO_MATCH: '{item_query}' is not on the menu."
        if len(matches) > 1:
            names = ", ".join(m.name for m in matches[:5])
            return cart, f"AMBIGUOUS: multiple items match '{item_query}': {names}"

        item = matches[0]
        new_cart = [dict(line) for line in cart]
        for line in new_cart:
            if line["name"] == item.name:
                line["quantity"] += quantity
                return new_cart, f"Added {quantity} x {item.name} to your cart."

        new_cart.append({"name": item.name, "unit_price": item.price, "quantity": quantity})
        return new_cart, f"Added {quantity} x {item.name} to your cart."

    def remove(self, cart: list[CartLine], item_query: str) -> tuple[list[CartLine], str]:
        query = item_query.strip().lower()
        new_cart = [line for line in cart if query not in line["name"].lower()]
        if len(new_cart) == len(cart):
            return cart, f"'{item_query}' isn't in your cart."
        return new_cart, f"Removed {item_query} from your cart."

    def update_quantity(
        self, cart: list[CartLine], item_query: str, quantity: int
    ) -> tuple[list[CartLine], str]:
        if quantity <= 0:
            return self.remove(cart, item_query)

        query = item_query.strip().lower()
        new_cart = [dict(line) for line in cart]
        for line in new_cart:
            if query in line["name"].lower():
                line["quantity"] = quantity
                return new_cart, f"Updated {line['name']} to {quantity}."
        return cart, f"'{item_query}' isn't in your cart."

    def clear(self, cart: list[CartLine]) -> tuple[list[CartLine], str]:
        return [], "Cart cleared."

    def show(self, cart: list[CartLine], business_config: BusinessConfig) -> str:
        return format_cart(cart, business_config)
