"""Black-box API tests for the QuickCart e-commerce REST API.

The tests treat the API as opaque and check only HTTP status codes and
response bodies against the specification. A QuickCart server must be
running at ``BASE_URL``.
"""

import requests
import pytest
from datetime import datetime, timezone

BASE_URL = "http://localhost:8080/api/v1"

HEADERS = {
    "X-Roll-Number": "123",
    "X-User-ID": "1"
}

INVALID_HEADERS = {
    "X-Roll-Number": "abc",
    "X-User-ID": "1"
}


def clear_cart():
    """Empty the test user's cart."""
    requests.delete(f"{BASE_URL}/cart/clear", headers=HEADERS)


def add_to_cart(product_id, quantity):
    """Add a product to the cart and return the response."""
    return requests.post(f"{BASE_URL}/cart/add",
                         json={"product_id": product_id, "quantity": quantity},
                         headers=HEADERS)


def get_cart():
    """Fetch the test user's cart."""
    return requests.get(f"{BASE_URL}/cart", headers=HEADERS)


def get_product_price(product_id):
    """Return the listed price of a product."""
    res = requests.get(f"{BASE_URL}/products/{product_id}", headers=HEADERS)
    return res.json()["price"]


def _find_product_with_stock(min_qty=1):
    """Return a product dict that has at least min_qty stock."""
    products = requests.get(f"{BASE_URL}/products", headers=HEADERS).json()
    for p in products:
        stock = p.get("stock_quantity", 0)
        if stock >= min_qty:
            return p
    return None


def _place_order():
    """Clear cart, add one item, checkout with CARD, return order."""
    clear_cart()
    p = _find_product_with_stock(1)
    assert p is not None, "No product with stock available"
    add_to_cart(p["product_id"], 1)
    res = requests.post(f"{BASE_URL}/checkout",
                        json={"payment_method": "CARD"},
                        headers=HEADERS)
    assert res.status_code == 200
    return res.json()


def test_missing_roll_number():
    """A request without the X-Roll-Number header returns HTTP 401."""
    res = requests.get(f"{BASE_URL}/products")
    assert res.status_code == 401


def test_invalid_roll_number():
    """A non-numeric X-Roll-Number header returns HTTP 400."""
    res = requests.get(f"{BASE_URL}/products", headers=INVALID_HEADERS)
    assert res.status_code == 400


def test_missing_user_id():
    """A request without the X-User-ID header returns HTTP 400."""
    headers = {"X-Roll-Number": "123"}
    res = requests.get(f"{BASE_URL}/products", headers=headers)
    assert res.status_code == 400


def test_get_products():
    """Listing products returns HTTP 200."""
    res = requests.get(f"{BASE_URL}/products", headers=HEADERS)
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_product_not_found():
    """Fetching a non-existent product returns HTTP 404."""
    res = requests.get(f"{BASE_URL}/products/9999", headers=HEADERS)
    assert res.status_code == 404


def test_product_list_structure():
    """Every product in the listing has the required fields."""
    res = requests.get(f"{BASE_URL}/products", headers=HEADERS)
    data = res.json()
    assert isinstance(data, list)
    if len(data) > 0:
        assert "product_id" in data[0]
        assert "price" in data[0]


def test_inactive_products_hidden():
    """Active-only list: every item returned must be active."""
    res = requests.get(f"{BASE_URL}/products", headers=HEADERS)
    assert res.status_code == 200
    for product in res.json():
        assert product.get("is_active", True) is True


def test_product_filter_by_category():
    """Filter by category returns only products in that category."""
    res_all = requests.get(f"{BASE_URL}/products", headers=HEADERS)
    products = res_all.json()
    if not products:
        pytest.skip("No products in DB")
    category = products[0].get("category")
    if not category:
        pytest.skip("Products have no category field")
    res = requests.get(f"{BASE_URL}/products", params={"category": category}, headers=HEADERS)
    assert res.status_code == 200
    for p in res.json():
        assert p["category"] == category


def test_product_search_by_name():
    """Search by name returns only matching products."""
    res_all = requests.get(f"{BASE_URL}/products", headers=HEADERS)
    products = res_all.json()
    if not products:
        pytest.skip("No products in DB")
    name_fragment = products[0]["name"][:4]
    res = requests.get(f"{BASE_URL}/products", params={"search": name_fragment}, headers=HEADERS)
    assert res.status_code == 200
    for p in res.json():
        assert name_fragment.lower() in p["name"].lower()


def test_product_sort_price_asc():
    """sort=price_asc returns prices in non-decreasing order."""
    res = requests.get(f"{BASE_URL}/products", params={"sort": "price_asc"}, headers=HEADERS)
    assert res.status_code == 200
    prices = [p["price"] for p in res.json()]
    assert prices == sorted(prices)


def test_product_sort_price_desc():
    """sort=price_desc returns prices in non-increasing order."""
    res = requests.get(f"{BASE_URL}/products", params={"sort": "price_desc"}, headers=HEADERS)
    assert res.status_code == 200
    prices = [p["price"] for p in res.json()]
    assert prices == sorted(prices, reverse=True)


def test_product_price_matches_db():
    """Price in list matches price on individual product endpoint."""
    res = requests.get(f"{BASE_URL}/products", headers=HEADERS)
    products = res.json()
    if not products:
        pytest.skip("No products in DB")
    p = products[0]
    res2 = requests.get(f"{BASE_URL}/products/{p['product_id']}", headers=HEADERS)
    assert res2.status_code == 200
    assert res2.json()["price"] == p["price"]


def test_cart_add_valid():
    """Adding an in-stock product to the cart returns HTTP 200."""
    payload = {"product_id": 1, "quantity": 2}
    res = requests.post(f"{BASE_URL}/cart/add", json=payload, headers=HEADERS)
    assert res.status_code == 200


def test_cart_add_zero_quantity():
    """Adding a product with quantity 0 returns HTTP 400."""
    payload = {"product_id": 1, "quantity": 0}
    res = requests.post(f"{BASE_URL}/cart/add", json=payload, headers=HEADERS)
    assert res.status_code == 400


def test_cart_add_negative_quantity():
    """Adding a product with a negative quantity returns HTTP 400."""
    payload = {"product_id": 1, "quantity": -1}
    res = requests.post(f"{BASE_URL}/cart/add", json=payload, headers=HEADERS)
    assert res.status_code == 400


def test_cart_add_invalid_product():
    """Adding a non-existent product returns HTTP 404."""
    payload = {"product_id": 9999, "quantity": 1}
    res = requests.post(f"{BASE_URL}/cart/add", json=payload, headers=HEADERS)
    assert res.status_code == 404


def test_cart_add_twice():
    """Adding the same product twice succeeds both times."""
    payload = {"product_id": 1, "quantity": 1}
    requests.post(f"{BASE_URL}/cart/add", json=payload, headers=HEADERS)
    res = requests.post(f"{BASE_URL}/cart/add", json=payload, headers=HEADERS)
    assert res.status_code == 200


def test_cart_remove_not_present():
    """Removing a product that is not in the cart returns HTTP 404."""
    payload = {"product_id": 9999}
    res = requests.post(f"{BASE_URL}/cart/remove", json=payload, headers=HEADERS)
    assert res.status_code == 404


def test_get_cart():
    """Fetching the cart returns HTTP 200."""
    res = get_cart()
    assert res.status_code == 200


def test_cart_subtotal_correct():
    """Each item's subtotal must equal quantity × unit price."""
    clear_cart()
    add_to_cart(1, 3)
    cart = get_cart().json()
    items = cart.get("items", [])
    assert len(items) > 0
    for item in items:
        expected = item["quantity"] * item["unit_price"]
        assert abs(item["subtotal"] - expected) < 0.01, (
            f"Subtotal mismatch: {item['subtotal']} != {expected}"
        )


def test_cart_total_is_sum_of_subtotals():
    """Cart total must equal the sum of all item subtotals."""
    clear_cart()
    add_to_cart(1, 2)
    cart = get_cart().json()
    items = cart.get("items", [])
    expected_total = sum(i["subtotal"] for i in items)
    assert abs(cart["total"] - expected_total) < 0.01


def test_cart_add_twice_quantities_accumulate():
    """Adding the same product twice sums the quantities, not replaces."""
    clear_cart()
    add_to_cart(1, 2)
    add_to_cart(1, 3)
    cart = get_cart().json()
    items = cart.get("items", [])
    product_item = next((i for i in items if i["product_id"] == 1), None)
    assert product_item is not None
    assert product_item["quantity"] == 5


def test_cart_update_valid():
    """Updating a cart item to a valid quantity returns HTTP 200."""
    clear_cart()
    add_to_cart(1, 2)
    res = requests.post(f"{BASE_URL}/cart/update",
                        json={"product_id": 1, "quantity": 5},
                        headers=HEADERS)
    assert res.status_code == 200


def test_cart_update_zero_quantity():
    """Updating a cart item to quantity 0 returns HTTP 400."""
    clear_cart()
    add_to_cart(1, 2)
    res = requests.post(f"{BASE_URL}/cart/update",
                        json={"product_id": 1, "quantity": 0},
                        headers=HEADERS)
    assert res.status_code == 400


def test_cart_clear():
    """Clearing the cart returns HTTP 200."""
    add_to_cart(1, 1)
    res = requests.delete(f"{BASE_URL}/cart/clear", headers=HEADERS)
    assert res.status_code == 200
    cart = get_cart().json()
    assert cart.get("items", []) == []


def test_cart_add_exceeds_stock():
    """Requesting more than available stock should return 400."""
    res = requests.post(f"{BASE_URL}/cart/add",
                        json={"product_id": 1, "quantity": 999999},
                        headers=HEADERS)
    assert res.status_code == 400


def test_checkout_invalid_payment():
    """Checking out with an unknown payment method returns HTTP 400."""
    payload = {"payment_method": "BITCOIN"}
    res = requests.post(f"{BASE_URL}/checkout", json=payload, headers=HEADERS)
    assert res.status_code == 400


def test_checkout_empty_cart():
    """Checking out with an empty cart returns HTTP 400."""
    requests.delete(f"{BASE_URL}/cart/clear", headers=HEADERS)
    payload = {"payment_method": "CARD"}
    res = requests.post(f"{BASE_URL}/checkout", json=payload, headers=HEADERS)
    assert res.status_code == 400


def test_checkout_cod_limit():
    """COD within limit must succeed; over 5000 must fail."""
    clear_cart()
    add_to_cart(1, 1)
    price = get_product_price(1)
    total_with_gst = price * 1.05
    payload = {"payment_method": "COD"}
    res = requests.post(f"{BASE_URL}/checkout", json=payload, headers=HEADERS)
    if total_with_gst <= 5000:
        assert res.status_code == 200
    else:
        assert res.status_code == 400


def test_checkout_card_payment_status_paid():
    """CARD checkout must produce an order with payment_status = PAID."""
    clear_cart()
    add_to_cart(1, 1)
    res = requests.post(f"{BASE_URL}/checkout",
                        json={"payment_method": "CARD"},
                        headers=HEADERS)
    assert res.status_code == 200
    assert res.json().get("payment_status") == "PAID"


def test_checkout_cod_payment_status_pending():
    """COD checkout (within limit) must produce payment_status = PENDING."""
    clear_cart()
    add_to_cart(1, 1)
    price = get_product_price(1)
    if price * 1.05 > 5000:
        pytest.skip("Product price too high for COD; pick a cheaper product_id")
    res = requests.post(f"{BASE_URL}/checkout",
                        json={"payment_method": "COD"},
                        headers=HEADERS)
    assert res.status_code == 200
    assert res.json().get("payment_status") == "PENDING"


def test_checkout_wallet_payment_status_pending():
    """WALLET checkout must produce payment_status = PENDING."""
    requests.post(f"{BASE_URL}/wallet/add", json={"amount": 50000}, headers=HEADERS)
    clear_cart()
    add_to_cart(1, 1)
    res = requests.post(f"{BASE_URL}/checkout",
                        json={"payment_method": "WALLET"},
                        headers=HEADERS)
    assert res.status_code == 200
    assert res.json().get("payment_status") == "PENDING"


def test_checkout_gst_is_5_percent():
    """Order total must be subtotal x 1.05 (5% GST applied exactly once)."""
    clear_cart()
    add_to_cart(1, 1)
    res = requests.post(f"{BASE_URL}/checkout",
                        json={"payment_method": "CARD"},
                        headers=HEADERS)
    assert res.status_code == 200
    order_id = res.json().get("order_id")
    invoice = requests.get(f"{BASE_URL}/orders/{order_id}/invoice", headers=HEADERS).json()
    subtotal = invoice.get("subtotal")
    order_total = invoice.get("total_amount")
    assert subtotal is not None and order_total is not None
    expected_total = round(subtotal * 1.05, 2)
    assert abs(order_total - expected_total) < 0.05, (
        f"Expected total ~{expected_total}, got {order_total}"
    )


def test_checkout_cod_exceeds_5000():
    """COD must be rejected when order total > 5000."""
    clear_cart()
    products = requests.get(f"{BASE_URL}/admin/products", headers=HEADERS).json()
    placed = False
    for p in sorted(products, key=lambda x: x["price"], reverse=True):
        if not p.get("is_active", True):
            continue
        price = p["price"]
        stock = p.get("stock_quantity", 0)
        qty = max(1, int(5000 / (price * 1.05)) + 2)
        if stock >= qty and price * qty * 1.05 > 5000:
            clear_cart()
            add_to_cart(p["product_id"], qty)
            placed = True
            break
    assert placed, "Could not find any product to push total above 5000"
    res = requests.post(f"{BASE_URL}/checkout",
                        json={"payment_method": "COD"},
                        headers=HEADERS)
    assert res.status_code == 400


def test_wallet_add_valid():
    """Topping up the wallet with a valid amount returns HTTP 200."""
    payload = {"amount": 100}
    res = requests.post(f"{BASE_URL}/wallet/add", json=payload, headers=HEADERS)
    assert res.status_code == 200


def test_wallet_add_zero():
    """Topping up the wallet with 0 returns HTTP 400."""
    payload = {"amount": 0}
    res = requests.post(f"{BASE_URL}/wallet/add", json=payload, headers=HEADERS)
    assert res.status_code == 400


def test_wallet_add_exceed():
    """Topping up the wallet above the maximum returns HTTP 400."""
    payload = {"amount": 200000}
    res = requests.post(f"{BASE_URL}/wallet/add", json=payload, headers=HEADERS)
    assert res.status_code == 400


def test_wallet_pay_insufficient():
    """Paying more than the wallet balance returns HTTP 400."""
    payload = {"amount": 999999}
    res = requests.post(f"{BASE_URL}/wallet/pay", json=payload, headers=HEADERS)
    assert res.status_code == 400


def test_get_wallet():
    """Fetching the wallet returns HTTP 200."""
    res = requests.get(f"{BASE_URL}/wallet", headers=HEADERS)
    assert res.status_code == 200
    assert "wallet_balance" in res.json()


def test_wallet_add_exact_max():
    """Amount of exactly 100000 should be accepted."""
    res = requests.post(f"{BASE_URL}/wallet/add", json={"amount": 100000}, headers=HEADERS)
    assert res.status_code == 200


def test_wallet_add_over_max():
    """Amount of 100001 must be rejected."""
    res = requests.post(f"{BASE_URL}/wallet/add", json={"amount": 100001}, headers=HEADERS)
    assert res.status_code == 400


def test_wallet_pay_deducts_correct_amount():
    """Exact amount requested is deducted — no more, no less."""
    requests.post(f"{BASE_URL}/wallet/add", json={"amount": 500}, headers=HEADERS)
    before = requests.get(f"{BASE_URL}/wallet", headers=HEADERS).json()["wallet_balance"]
    deduct = 50
    res = requests.post(f"{BASE_URL}/wallet/pay", json={"amount": deduct}, headers=HEADERS)
    assert res.status_code == 200
    after = requests.get(f"{BASE_URL}/wallet", headers=HEADERS).json()["wallet_balance"]
    assert abs((before - after) - deduct) < 0.1, (
        f"Expected deduction of {deduct}, actual change was {before - after}"
    )


def test_wallet_pay_zero():
    """Paying 0 must be rejected."""
    res = requests.post(f"{BASE_URL}/wallet/pay", json={"amount": 0}, headers=HEADERS)
    assert res.status_code == 400


def test_add_address_valid():
    """Adding a valid address returns HTTP 200."""
    payload = {
        "label": "HOME",
        "street": "123 Main Street",
        "city": "Chennai",
        "pincode": "600001"
    }
    res = requests.post(f"{BASE_URL}/addresses", json=payload, headers=HEADERS)
    assert res.status_code == 200


def test_add_address_invalid_label():
    """Adding an address with an unsupported label returns HTTP 400."""
    payload = {
        "label": "INVALID",
        "street": "123 Main Street",
        "city": "Chennai",
        "pincode": "600001"
    }
    res = requests.post(f"{BASE_URL}/addresses", json=payload, headers=HEADERS)
    assert res.status_code == 400


def test_address_invalid_pincode():
    """Adding an address with an invalid pincode returns HTTP 400."""
    payload = {
        "label": "HOME",
        "street": "Valid Street Name",
        "city": "Chennai",
        "pincode": "123"
    }
    res = requests.post(f"{BASE_URL}/addresses", json=payload, headers=HEADERS)
    assert res.status_code == 400


def test_get_addresses():
    """Listing addresses returns HTTP 200."""
    res = requests.get(f"{BASE_URL}/addresses", headers=HEADERS)
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_add_address_office_label():
    """Adding an address labelled OFFICE returns HTTP 200."""
    payload = {"label": "OFFICE", "street": "456 Business Park", "city": "Mumbai", "pincode": "400001"}
    res = requests.post(f"{BASE_URL}/addresses", json=payload, headers=HEADERS)
    assert res.status_code == 200


def test_add_address_other_label():
    """Adding an address labelled OTHER returns HTTP 200."""
    payload = {"label": "OTHER", "street": "789 Side Lane", "city": "Pune", "pincode": "411001"}
    res = requests.post(f"{BASE_URL}/addresses", json=payload, headers=HEADERS)
    assert res.status_code == 200


def test_add_address_response_structure():
    """Response must include address_id, label, street, city, pincode, is_default."""
    payload = {"label": "HOME", "street": "10 Garden Road", "city": "Chennai", "pincode": "600001"}
    res = requests.post(f"{BASE_URL}/addresses", json=payload, headers=HEADERS)
    assert res.status_code == 200
    data = res.json()
    for field in ["address_id", "label", "street", "city", "pincode", "is_default"]:
        assert field in data, f"Missing field: {field} — got keys: {list(data.keys())}"


def test_add_address_street_too_short():
    """Street under 5 characters must be rejected."""
    payload = {"label": "HOME", "street": "Hi", "city": "Chennai", "pincode": "600001"}
    res = requests.post(f"{BASE_URL}/addresses", json=payload, headers=HEADERS)
    assert res.status_code == 400


def test_add_address_city_too_short():
    """City under 2 characters must be rejected."""
    payload = {"label": "HOME", "street": "Valid Street Name", "city": "X", "pincode": "600001"}
    res = requests.post(f"{BASE_URL}/addresses", json=payload, headers=HEADERS)
    assert res.status_code == 400


def test_default_address_uniqueness():
    """Only one address can be default at a time."""
    payload1 = {"label": "HOME", "street": "First Default Street", "city": "Chennai", "pincode": "600001", "is_default": True}
    payload2 = {"label": "HOME", "street": "Second Default Street", "city": "Chennai", "pincode": "600002", "is_default": True}
    requests.post(f"{BASE_URL}/addresses", json=payload1, headers=HEADERS)
    requests.post(f"{BASE_URL}/addresses", json=payload2, headers=HEADERS)
    res = requests.get(f"{BASE_URL}/addresses", headers=HEADERS)
    defaults = [a for a in res.json() if a.get("is_default") is True]
    assert len(defaults) == 1


def _create_address_and_get_id():
    """Helper: create a HOME address in Chennai and return its id."""
    payload = {"label": "HOME", "street": "Test Street Chennai", "city": "Chennai", "pincode": "600001"}
    res = requests.post(f"{BASE_URL}/addresses", json=payload, headers=HEADERS)
    assert res.status_code == 200, f"Address creation failed: {res.json()}"
    data = res.json()
    address_id = data.get("address_id") or data.get("id") or data.get("addressId")
    assert address_id is not None, f"No id field in response: {list(data.keys())}"
    return address_id


def test_update_address_street():
    """PUT should update street and return the new data."""
    address_id = _create_address_and_get_id()
    put_res = requests.put(f"{BASE_URL}/addresses/{address_id}",
                           json={"street": "New Updated Street"},
                           headers=HEADERS)
    assert put_res.status_code == 200
    assert put_res.json()["street"] == "New Updated Street"


def test_delete_address():
    """Deleting an existing address returns HTTP 200."""
    address_id = _create_address_and_get_id()
    del_res = requests.delete(f"{BASE_URL}/addresses/{address_id}", headers=HEADERS)
    assert del_res.status_code == 200


def test_delete_address_not_found():
    """Deleting a non-existent address returns HTTP 404."""
    res = requests.delete(f"{BASE_URL}/addresses/9999", headers=HEADERS)
    assert res.status_code == 404


def test_review_invalid_rating():
    """Submitting a review with an out-of-range rating returns HTTP 400."""
    payload = {"rating": 6, "comment": "Bad"}
    res = requests.post(f"{BASE_URL}/products/1/reviews", json=payload, headers=HEADERS)
    assert res.status_code == 400


def test_review_valid():
    """Submitting a valid review returns HTTP 200."""
    payload = {"rating": 5, "comment": "Great product"}
    res = requests.post(f"{BASE_URL}/products/1/reviews", json=payload, headers=HEADERS)
    assert res.status_code == 200


def test_review_rating_zero():
    """Submitting a review with rating 0 returns HTTP 400."""
    payload = {"rating": 0, "comment": "Bad"}
    res = requests.post(f"{BASE_URL}/products/1/reviews", json=payload, headers=HEADERS)
    assert res.status_code == 400


def test_review_empty_comment():
    """Submitting a review with an empty comment returns HTTP 400."""
    payload = {"rating": 4, "comment": ""}
    res = requests.post(f"{BASE_URL}/products/1/reviews", json=payload, headers=HEADERS)
    assert res.status_code == 400


def test_get_reviews():
    """Listing a product's reviews returns HTTP 200."""
    res = requests.get(f"{BASE_URL}/products/1/reviews", headers=HEADERS)
    assert res.status_code == 200
    data = res.json()
    assert "reviews" in data
    assert isinstance(data["reviews"], list)


def test_review_rating_boundary_min():
    """Rating 1 (min valid) must be accepted."""
    res = requests.post(f"{BASE_URL}/products/1/reviews",
                        json={"rating": 1, "comment": "Terrible but valid"},
                        headers=HEADERS)
    assert res.status_code == 200


def test_review_rating_boundary_max():
    """Rating 5 (max valid) must be accepted."""
    res = requests.post(f"{BASE_URL}/products/1/reviews",
                        json={"rating": 5, "comment": "Perfect"},
                        headers=HEADERS)
    assert res.status_code == 200


def test_review_comment_too_long():
    """Comment over 200 characters must be rejected."""
    res = requests.post(f"{BASE_URL}/products/1/reviews",
                        json={"rating": 3, "comment": "A" * 201},
                        headers=HEADERS)
    assert res.status_code == 400


def test_review_comment_max_boundary():
    """Comment of exactly 200 characters must be accepted."""
    res = requests.post(f"{BASE_URL}/products/1/reviews",
                        json={"rating": 3, "comment": "B" * 200},
                        headers=HEADERS)
    assert res.status_code == 200


def test_review_average_rating_is_decimal():
    """Average rating must be a proper decimal, not a truncated integer."""
    requests.post(f"{BASE_URL}/products/1/reviews",
                  json={"rating": 4, "comment": "Good"}, headers=HEADERS)
    requests.post(f"{BASE_URL}/products/1/reviews",
                  json={"rating": 3, "comment": "Okay"}, headers=HEADERS)
    res = requests.get(f"{BASE_URL}/products/1/reviews", headers=HEADERS)
    data = res.json()
    reviews = data["reviews"]
    expected_avg = sum(r["rating"] for r in reviews) / len(reviews)
    actual_avg = data.get("average_rating")
    assert actual_avg is not None
    assert abs(actual_avg - expected_avg) < 0.01, (
        f"Average rating {actual_avg} does not match expected {expected_avg}"
    )


def test_review_average_no_reviews_is_zero():
    """A product with no reviews must report average_rating = 0."""
    products = requests.get(f"{BASE_URL}/products", headers=HEADERS).json()
    for p in products:
        pid = p["product_id"]
        reviews_res = requests.get(f"{BASE_URL}/products/{pid}/reviews", headers=HEADERS)
        data = reviews_res.json()
        if len(data.get("reviews", [])) == 0:
            assert data.get("average_rating") == 0, (
                f"Product {pid} has no reviews but average_rating is {data.get('average_rating')}, expected 0"
            )
            return
    pytest.skip("All products already have reviews")


def test_get_orders():
    """Listing orders returns HTTP 200."""
    res = requests.get(f"{BASE_URL}/orders", headers=HEADERS)
    assert res.status_code == 200


def test_cancel_invalid_order():
    """Cancelling a non-existent order returns HTTP 404."""
    res = requests.post(f"{BASE_URL}/orders/9999/cancel", headers=HEADERS)
    assert res.status_code == 404


def test_get_single_order():
    """Fetching an existing order returns HTTP 200."""
    order = _place_order()
    order_id = order["order_id"]
    res = requests.get(f"{BASE_URL}/orders/{order_id}", headers=HEADERS)
    assert res.status_code == 200
    assert res.json()["order_id"] == order_id


def test_cancel_order_success():
    """Cancelling a freshly placed order returns HTTP 200."""
    order = _place_order()
    res = requests.post(f"{BASE_URL}/orders/{order['order_id']}/cancel", headers=HEADERS)
    assert res.status_code == 200


def test_cancel_delivered_order_rejected():
    """Cancelling a DELIVERED order must return 400."""
    admin_res = requests.get(f"{BASE_URL}/admin/orders", headers=HEADERS)
    orders = admin_res.json()
    delivered = [o for o in orders if o.get("order_status") == "DELIVERED"]
    if not delivered:
        pytest.skip("No delivered orders in the entire DB")
    order = delivered[0]
    test_headers = {"X-Roll-Number": HEADERS["X-Roll-Number"],
                    "X-User-ID": str(order["user_id"])}
    res = requests.post(f"{BASE_URL}/orders/{order['order_id']}/cancel", headers=test_headers)
    assert res.status_code == 400


def test_cancel_order_restores_stock():
    """Cancelling an order must add the items back to product stock."""
    before = requests.get(f"{BASE_URL}/products/1", headers=HEADERS).json()
    stock_key = next((k for k in before if "stock" in k.lower()), None)
    assert stock_key is not None, f"No stock field in product response: {list(before.keys())}"
    stock_before = before[stock_key]
    order = _place_order()
    requests.post(f"{BASE_URL}/orders/{order['order_id']}/cancel", headers=HEADERS)
    stock_after = requests.get(f"{BASE_URL}/products/1", headers=HEADERS).json()[stock_key]
    assert stock_after == stock_before


def test_invoice_structure():
    """Invoice must include subtotal, gst_amount, and total_amount."""
    order = _place_order()
    res = requests.get(f"{BASE_URL}/orders/{order['order_id']}/invoice", headers=HEADERS)
    assert res.status_code == 200
    invoice = res.json()
    for field in ["subtotal", "gst_amount", "total_amount"]:
        assert field in invoice, f"Missing field: {field} — got: {list(invoice.keys())}"


def test_invoice_gst_math():
    """gst_amount must be subtotal × 0.05, total_amount must be subtotal + gst_amount."""
    order = _place_order()
    res = requests.get(f"{BASE_URL}/orders/{order['order_id']}/invoice", headers=HEADERS)
    invoice = res.json()
    subtotal = invoice["subtotal"]
    gst = invoice["gst_amount"]
    total = invoice["total_amount"]
    assert abs(gst - subtotal * 0.05) < 0.05, f"GST {gst} != subtotal {subtotal} × 0.05"
    assert abs(total - (subtotal + gst)) < 0.05


def test_get_profile():
    """Fetching the profile returns HTTP 200."""
    res = requests.get(f"{BASE_URL}/profile", headers=HEADERS)
    assert res.status_code == 200
    assert "name" in res.json()


def test_update_profile_valid():
    """Updating the profile with valid data returns HTTP 200."""
    res = requests.put(f"{BASE_URL}/profile",
                       json={"name": "Test User", "phone": "9876543210"},
                       headers=HEADERS)
    assert res.status_code == 200


def test_update_profile_name_too_short():
    """Updating the profile with a name that is too short returns HTTP 400."""
    res = requests.put(f"{BASE_URL}/profile",
                       json={"name": "A", "phone": "9876543210"},
                       headers=HEADERS)
    assert res.status_code == 400


def test_update_profile_name_too_long():
    """Updating the profile with a name that is too long returns HTTP 400."""
    res = requests.put(f"{BASE_URL}/profile",
                       json={"name": "A" * 51, "phone": "9876543210"},
                       headers=HEADERS)
    assert res.status_code == 400


def test_update_profile_name_boundary_min():
    """Name of exactly 2 characters must be accepted."""
    res = requests.put(f"{BASE_URL}/profile",
                       json={"name": "Jo", "phone": "9876543210"},
                       headers=HEADERS)
    assert res.status_code == 200


def test_update_profile_name_boundary_max():
    """Name of exactly 50 characters must be accepted."""
    res = requests.put(f"{BASE_URL}/profile",
                       json={"name": "A" * 50, "phone": "9876543210"},
                       headers=HEADERS)
    assert res.status_code == 200


def test_update_profile_phone_not_10_digits():
    """Phone number with fewer than 10 digits must be rejected."""
    res = requests.put(f"{BASE_URL}/profile",
                       json={"name": "Test User", "phone": "12345"},
                       headers=HEADERS)
    assert res.status_code == 400


def test_update_profile_phone_letters():
    """Non-numeric phone number must be rejected."""
    res = requests.put(f"{BASE_URL}/profile",
                       json={"name": "Test User", "phone": "abcdefghij"},
                       headers=HEADERS)
    assert res.status_code == 400


def _is_coupon_expired(coupon):
    """Check if coupon is expired by comparing expiry_date to now."""
    expiry = coupon.get("expiry_date", "")
    if not expiry:
        return False
    try:
        exp_dt = datetime.fromisoformat(expiry.replace("Z", "+00:00"))
        return exp_dt < datetime.now(timezone.utc)
    except (ValueError, TypeError):
        return False


def _get_valid_coupon():
    """Return a non-expired coupon, skipping the test if none exist."""
    res = requests.get(f"{BASE_URL}/admin/coupons", headers=HEADERS)
    valid = [c for c in res.json() if not _is_coupon_expired(c)]
    if not valid:
        pytest.skip("No valid (non-expired) coupons available in DB")
    return valid[0]


def _fill_cart_to_meet_value(target_value):
    """Add a single product to cart so price*qty >= target_value. Uses admin/products for stock."""
    clear_cart()
    products = requests.get(f"{BASE_URL}/admin/products", headers=HEADERS).json()
    for p in sorted(products, key=lambda x: x["price"], reverse=True):
        if not p.get("is_active", True):
            continue
        price = p["price"]
        stock = p.get("stock_quantity", 0)
        if stock <= 0 or price <= 0:
            continue
        qty = max(1, int(target_value / price) + 1)
        if stock >= qty:
            add_to_cart(p["product_id"], qty)
            return price * qty
    return 0


def test_apply_coupon_valid():
    """Applying a valid coupon to a cart that meets its minimum value returns HTTP 200."""
    coupon = _get_valid_coupon()
    min_val = coupon.get("min_cart_value", 0)
    filled = _fill_cart_to_meet_value(min_val)
    assert filled >= min_val, f"Could not fill cart to {min_val}, only got {filled}"
    res = requests.post(f"{BASE_URL}/coupon/apply",
                        json={"coupon_code": coupon["coupon_code"]},
                        headers=HEADERS)
    assert res.status_code == 200


def test_apply_expired_coupon():
    """Expired coupons must be rejected."""
    res = requests.get(f"{BASE_URL}/admin/coupons", headers=HEADERS)
    expired = [c for c in res.json() if _is_coupon_expired(c)]
    if not expired:
        pytest.skip("No expired coupons available")
    clear_cart()
    add_to_cart(1, 1)
    res2 = requests.post(f"{BASE_URL}/coupon/apply",
                         json={"coupon_code": expired[0]["coupon_code"]},
                         headers=HEADERS)
    assert res2.status_code == 400


def test_apply_coupon_below_min_cart_value():
    """Coupon with min cart value must be rejected when cart is too small."""
    res = requests.get(f"{BASE_URL}/admin/coupons", headers=HEADERS)
    high_min = [c for c in res.json() if not _is_coupon_expired(c)
                and c.get("min_cart_value", 0) > 0]
    if not high_min:
        pytest.skip("No coupon with min_cart_value to test")
    coupon = max(high_min, key=lambda c: c["min_cart_value"])
    clear_cart()
    products = requests.get(f"{BASE_URL}/products", headers=HEADERS).json()
    cheapest = min(products, key=lambda p: p["price"])
    add_to_cart(cheapest["product_id"], 1)
    if get_cart().json()["total"] >= coupon["min_cart_value"]:
        pytest.skip("Even cheapest product exceeds coupon min_cart_value")
    res2 = requests.post(f"{BASE_URL}/coupon/apply",
                         json={"coupon_code": coupon["coupon_code"]},
                         headers=HEADERS)
    assert res2.status_code == 400


def test_apply_coupon_percent_discount():
    """PERCENT coupon must reduce total by the correct percentage."""
    res = requests.get(f"{BASE_URL}/admin/coupons", headers=HEADERS)
    pct = [c for c in res.json() if c.get("discount_type") == "PERCENT"
           and not _is_coupon_expired(c)]
    if not pct:
        pytest.skip("No PERCENT coupon available")
    coupon = min(pct, key=lambda c: c.get("min_cart_value", 0))
    min_val = coupon.get("min_cart_value", 0)
    filled = _fill_cart_to_meet_value(min_val)
    assert filled >= min_val, f"Could not meet min_cart_value {min_val}"
    before_total = filled
    res2 = requests.post(f"{BASE_URL}/coupon/apply",
                         json={"coupon_code": coupon["coupon_code"]},
                         headers=HEADERS)
    assert res2.status_code == 200, f"Coupon apply failed: {res2.json()}"
    after_total = res2.json().get("new_total")
    discount = min(before_total * coupon["discount_value"] / 100,
                   coupon.get("max_discount") or float("inf"))
    assert abs(after_total - round(before_total - discount, 2)) < 0.05


def test_apply_coupon_fixed_discount():
    """FIXED coupon must reduce total by the flat amount."""
    res = requests.get(f"{BASE_URL}/admin/coupons", headers=HEADERS)
    fixed = [c for c in res.json() if c.get("discount_type") == "FIXED"
             and not _is_coupon_expired(c)]
    if not fixed:
        pytest.skip("No FIXED coupon available")
    coupon = min(fixed, key=lambda c: c.get("min_cart_value", 0))
    min_val = coupon.get("min_cart_value", 0)
    filled = _fill_cart_to_meet_value(min_val)
    assert filled >= min_val, f"Could not meet min_cart_value {min_val}"
    before_total = filled
    res2 = requests.post(f"{BASE_URL}/coupon/apply",
                         json={"coupon_code": coupon["coupon_code"]},
                         headers=HEADERS)
    assert res2.status_code == 200, f"Coupon apply failed: {res2.json()}"
    after_total = res2.json().get("new_total")
    assert abs(after_total - round(before_total - coupon["discount_value"], 2)) < 0.05


def test_remove_coupon():
    """Removing an applied coupon returns HTTP 200."""
    coupon = _get_valid_coupon()
    min_val = coupon.get("min_cart_value", 0)
    filled = _fill_cart_to_meet_value(min_val)
    requests.post(f"{BASE_URL}/coupon/apply", json={"coupon_code": coupon["coupon_code"]}, headers=HEADERS)
    res = requests.post(f"{BASE_URL}/coupon/remove", headers=HEADERS)
    assert res.status_code == 200


def test_get_loyalty_points():
    """Fetching loyalty points returns HTTP 200."""
    res = requests.get(f"{BASE_URL}/loyalty", headers=HEADERS)
    assert res.status_code == 200
    assert "loyalty_points" in res.json()


def test_redeem_zero_points():
    """Redeeming 0 points must be rejected."""
    res = requests.post(f"{BASE_URL}/loyalty/redeem", json={"points": 0}, headers=HEADERS)
    assert res.status_code == 400


def test_redeem_more_than_balance():
    """Redeeming more points than available must be rejected."""
    balance = requests.get(f"{BASE_URL}/loyalty", headers=HEADERS).json()["loyalty_points"]
    res = requests.post(f"{BASE_URL}/loyalty/redeem",
                        json={"points": balance + 9999},
                        headers=HEADERS)
    assert res.status_code == 400


def test_redeem_loyalty_points_valid():
    """Redeeming 1 point (if available) must succeed."""
    balance = requests.get(f"{BASE_URL}/loyalty", headers=HEADERS).json()["loyalty_points"]
    if balance < 1:
        pytest.skip("User has no loyalty points to redeem")
    res = requests.post(f"{BASE_URL}/loyalty/redeem", json={"points": 1}, headers=HEADERS)
    assert res.status_code == 200


def _create_ticket(subject="Test issue here", message="This is a test message for the ticket."):
    """Create a support ticket and return the response."""
    return requests.post(f"{BASE_URL}/support/ticket",
                         json={"subject": subject, "message": message},
                         headers=HEADERS)


def test_create_ticket_valid():
    """Creating a valid support ticket returns HTTP 200."""
    res = _create_ticket()
    assert res.status_code == 200


def test_create_ticket_starts_open():
    """Newly created ticket must have status OPEN."""
    res = _create_ticket()
    assert res.status_code == 200
    assert res.json().get("status") == "OPEN"


def test_get_tickets():
    """Listing support tickets returns HTTP 200."""
    res = requests.get(f"{BASE_URL}/support/tickets", headers=HEADERS)
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_ticket_subject_too_short():
    """Creating a ticket with a subject that is too short returns HTTP 400."""
    res = _create_ticket(subject="Hi")
    assert res.status_code == 400


def test_ticket_subject_too_long():
    """Creating a ticket with a subject that is too long returns HTTP 400."""
    res = _create_ticket(subject="A" * 101)
    assert res.status_code == 400


def test_ticket_message_empty():
    """Creating a ticket with an empty message returns HTTP 400."""
    res = _create_ticket(message="")
    assert res.status_code == 400


def test_ticket_message_too_long():
    """Creating a ticket with a message that is too long returns HTTP 400."""
    res = _create_ticket(message="A" * 501)
    assert res.status_code == 400


def test_ticket_message_saved_exactly():
    """Message must be stored exactly as written."""
    message = "Exact message content: special chars !@#$%"
    res = _create_ticket(message=message)
    assert res.status_code == 200
    ticket_id = res.json()["ticket_id"]
    admin_res = requests.get(f"{BASE_URL}/admin/tickets", headers=HEADERS)
    assert admin_res.status_code == 200
    tickets = admin_res.json()
    ticket = next((t for t in tickets if t.get("ticket_id") == ticket_id), None)
    assert ticket is not None, f"Ticket {ticket_id} not found in admin tickets"
    stored = ticket.get("message") or ticket.get("body") or ticket.get("description")
    assert stored is not None, f"No message field in ticket: {list(ticket.keys())}"
    assert stored == message


def test_ticket_transition_open_to_in_progress():
    """A ticket can move from OPEN to IN_PROGRESS."""
    res = _create_ticket()
    ticket_id = res.json()["ticket_id"]
    update = requests.put(f"{BASE_URL}/support/tickets/{ticket_id}",
                          json={"status": "IN_PROGRESS"},
                          headers=HEADERS)
    assert update.status_code == 200
    assert update.json().get("status") == "IN_PROGRESS"


def test_ticket_transition_in_progress_to_closed():
    """A ticket can move from IN_PROGRESS to CLOSED."""
    res = _create_ticket()
    ticket_id = res.json()["ticket_id"]
    requests.put(f"{BASE_URL}/support/tickets/{ticket_id}",
                 json={"status": "IN_PROGRESS"}, headers=HEADERS)
    update = requests.put(f"{BASE_URL}/support/tickets/{ticket_id}",
                          json={"status": "CLOSED"},
                          headers=HEADERS)
    assert update.status_code == 200
    assert update.json().get("status") == "CLOSED"


def test_ticket_invalid_transition_open_to_closed():
    """OPEN → CLOSED directly must be rejected."""
    res = _create_ticket()
    ticket_id = res.json()["ticket_id"]
    update = requests.put(f"{BASE_URL}/support/tickets/{ticket_id}",
                          json={"status": "CLOSED"},
                          headers=HEADERS)
    assert update.status_code == 400


def test_ticket_invalid_transition_backwards():
    """CLOSED → OPEN must be rejected."""
    res = _create_ticket()
    ticket_id = res.json()["ticket_id"]
    requests.put(f"{BASE_URL}/support/tickets/{ticket_id}",
                 json={"status": "IN_PROGRESS"}, headers=HEADERS)
    requests.put(f"{BASE_URL}/support/tickets/{ticket_id}",
                 json={"status": "CLOSED"}, headers=HEADERS)
    update = requests.put(f"{BASE_URL}/support/tickets/{ticket_id}",
                          json={"status": "OPEN"},
                          headers=HEADERS)
    assert update.status_code == 400
