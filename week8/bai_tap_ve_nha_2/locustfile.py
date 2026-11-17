"""Load test the existing week 7 product-list endpoint."""

import random

from locust import HttpUser, between, task


class ProductBrowser(HttpUser):
    # Simulate browsing, including the pause between requests.
    wait_time = between(1, 3)

    @task
    def list_products(self):
        page = random.randint(1, 50)
        with self.client.get(
            "/api/v1/products",
            params={"page": page, "size": 20},
            name="/api/v1/products",
            timeout=5,
            allow_redirects=False,
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"Expected HTTP 200, got {response.status_code}")
                return
            try:
                body = response.json()
            except ValueError:
                response.failure("Response is not valid JSON")
                return
            if not isinstance(body, dict):
                response.failure("Response must be a JSON object")
                return
            items = body.get("items")
            if (
                not isinstance(items, list)
                or len(items) != 20
                or body.get("page") != page
                or body.get("size") != 20
                or body.get("total") != 1000
            ):
                response.failure("Unexpected pagination or missing seeded products")
                return
            for item in items:
                if (
                    not isinstance(item, dict)
                    or type(item.get("id")) is not int
                    or not isinstance(item.get("sku"), str)
                    or not isinstance(item.get("name"), str)
                    or type(item.get("price_cents")) is not int
                    or type(item.get("qty_in_stock")) is not int
                    or item.get("archived") is not False
                ):
                    response.failure("Invalid product fields in HTTP 200 response")
                    return
