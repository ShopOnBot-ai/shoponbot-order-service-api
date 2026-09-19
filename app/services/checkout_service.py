from decimal import Decimal

from fastapi import HTTPException, status

from app.core.logging import logger


class CheckoutService:
    @staticmethod
    def calculate_bill(cart_data: dict, address_data: dict) -> dict:
        items = cart_data.get("items", [])
        logger.info("Items: %s", items)
        logger.info("items: %s", type(items))
        if not items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cart is empty can't proceed to checkout"
            )
        subtotal = Decimal("0.00")
        for item in items:
            product_info = item.get("product", {})
            price = Decimal(str(product_info.get("price", 0)))
            quantity = int(item.get("quantity", 1))
            subtotal += price * quantity

        shipping_fee = Decimal("0.00")
        tax = Decimal("0.00")
        discount = Decimal("0.00")

        if address_data and address_data.get("addresses"):
            shipping_fee = Decimal("50.00") if subtotal < Decimal("500.00") else Decimal("0.00")
            tax = (subtotal * Decimal("0.18")).quantize(Decimal("0.01"))
        
        total_amount = subtotal + shipping_fee + tax - discount

        return {
            "subtotal": subtotal,
            "tax": tax,
            "shipping_fee": shipping_fee,
            "discount": discount,
            "total_amount": total_amount,
            "items": items
        }
