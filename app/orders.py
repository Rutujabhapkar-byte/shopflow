from . import db
from .models import CartItem, Order, OrderItem, Product


class CheckoutError(Exception):
    pass


def create_order_from_cart(user, address):
    """Create a pending order from the user's cart, using prices from the database."""
    rows = (
        db.session.query(CartItem, Product)
        .join(Product, CartItem.product_id == Product.id)
        .filter(CartItem.user_id == user.id)
        .order_by(CartItem.id)
        .all()
    )
    if not rows:
        raise CheckoutError("Your cart is empty.")

    for item, p in rows:
        if not p.active or p.stock < item.quantity:
            raise CheckoutError(f"'{p.name}' is not available in that quantity.")

    order = Order(user_id=user.id, address_id=address.id, total_paise=0, status="pending")
    db.session.add(order)
    db.session.flush()  # gives the order an id

    total = 0
    for item, p in rows:
        total += item.quantity * p.price_paise
        db.session.add(
            OrderItem(
                order_id=order.id,
                product_id=p.id,
                quantity=item.quantity,
                price_paise=p.price_paise,  # price copied at purchase time
            )
        )
    order.total_paise = total
    db.session.commit()


