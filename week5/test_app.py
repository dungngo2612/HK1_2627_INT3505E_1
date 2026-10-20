import unittest

from week5.app import Book, create_app, db


class BookPaginationTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(
            {
                "TESTING": True,
                "SQLALCHEMY_DATABASE_URI": "sqlite://",
                "SEED_BOOKS": False,
            }
        )
        with self.app.app_context():
            db.create_all()
            db.session.add_all(
                [
                    Book(
                        title="Alpha",
                        author="A Author",
                        genre="technology",
                        isbn="0000000000001",
                        price_vnd=900,
                        published_year=2020,
                    ),
                    Book(
                        title="Bravo",
                        author="B Author",
                        genre="technology",
                        isbn="0000000000002",
                        price_vnd=900,
                        published_year=2021,
                    ),
                    Book(
                        title="Charlie",
                        author="C Author",
                        genre="technology",
                        isbn="0000000000003",
                        price_vnd=1200,
                        published_year=2022,
                    ),
                    Book(
                        title="Delta",
                        author="D Author",
                        genre="fiction",
                        isbn="0000000000004",
                        price_vnd=500,
                        published_year=2018,
                    ),
                    Book(
                        title="Echo",
                        author="E Author",
                        genre="technology",
                        isbn="0000000000005",
                        price_vnd=700,
                        published_year=2019,
                    ),
                    Book(
                        title="Foxtrot",
                        author="F Author",
                        genre="fiction",
                        isbn="0000000000006",
                        price_vnd=900,
                        published_year=2023,
                    ),
                    Book(
                        title="Alpha",
                        author="G Author",
                        genre="technology",
                        isbn="0000000000007",
                        price_vnd=900,
                        published_year=2024,
                    ),
                ]
            )
            db.session.commit()
        self.client = self.app.test_client()
        self.addCleanup(self._drop_database)

    def _drop_database(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_offset_pagination_filters_genre_and_sorts_multiple_fields(self):
        response = self.client.get(
            "/api/v1/books",
            query_string={
                "strategy": "offset",
                "offset": 1,
                "limit": 2,
                "genre": "TECHNOLOGY",
                "sort": "-price_vnd,title",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [book["id"] for book in response.json["data"]], [1, 7]
        )
        self.assertEqual(
            response.json["page"],
            {
                "strategy": "offset",
                "offset": 1,
                "limit": 2,
                "total": 5,
                "has_more": True,
                "next_offset": 3,
            },
        )

    def test_cursor_pages_cover_sorted_collection_without_duplicates(self):
        ids = []
        titles = []
        cursor = None
        while True:
            query = {"strategy": "cursor", "limit": 2, "sort": "-price_vnd,title"}
            if cursor is not None:
                query["cursor"] = cursor
            response = self.client.get("/books", query_string=query)
            self.assertEqual(response.status_code, 200)
            ids.extend(book["id"] for book in response.json["data"])
            titles.extend(book["title"] for book in response.json["data"])
            page = response.json["page"]
            self.assertEqual(page["has_more"], page["next_cursor"] is not None)
            cursor = page["next_cursor"]
            if cursor is None:
                break

        self.assertEqual(
            titles, ["Charlie", "Alpha", "Alpha", "Bravo", "Foxtrot", "Echo", "Delta"]
        )
        self.assertEqual(ids, [3, 1, 7, 2, 6, 5, 4])
        self.assertEqual(len(ids), len(set(ids)))

    def test_cursor_is_bound_to_sort_and_genre(self):
        first_page = self.client.get(
            "/books?strategy=cursor&limit=1&sort=-price_vnd,title"
        ).json
        cursor = first_page["page"]["next_cursor"]

        changed_sort = self.client.get(
            "/books",
            query_string={
                "strategy": "cursor",
                "limit": 1,
                "sort": "title",
                "cursor": cursor,
            },
        )
        changed_genre = self.client.get(
            "/books",
            query_string={
                "strategy": "cursor",
                "limit": 1,
                "sort": "-price_vnd,title",
                "genre": "technology",
                "cursor": cursor,
            },
        )
        self.assertEqual(changed_sort.status_code, 400)
        self.assertEqual(changed_genre.status_code, 400)
        self.assertEqual(changed_sort.json["error"]["code"], "invalid-cursor")

    def test_invalid_pagination_and_sort_parameters_return_400(self):
        invalid_queries = [
            "strategy=page",
            "strategy=offset&offset=-1",
            "strategy=cursor&limit=101",
            "strategy=offset&limit=NaN",
            "strategy=cursor&sort=title,unknown",
            "strategy=cursor&sort=title,title",
            "strategy=cursor&genre=%20",
            "strategy=cursor&cursor=not-a-cursor",
        ]
        for query in invalid_queries:
            with self.subTest(query=query):
                self.assertEqual(self.client.get(f"/books?{query}").status_code, 400)


if __name__ == "__main__":
    unittest.main()
