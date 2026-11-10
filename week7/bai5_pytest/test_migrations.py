from pathlib import Path

from sqlalchemy import inspect

from product_api import create_app
from product_api.extensions import db


def test_migration_upgrade_downgrade_and_model_consistency(tmp_path):
    directory = Path(__file__).resolve().parents[1] / "migrations"
    application = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": f'sqlite:///{tmp_path / "migrated.db"}',
        "MIGRATIONS_DIR": str(directory),
        "LOG_LEVEL": "CRITICAL",
    })
    runner = application.test_cli_runner()
    try:
        upgraded = runner.invoke(args=["db", "upgrade"])
        assert upgraded.exit_code == 0, upgraded.output
        with application.app_context():
            inspector = inspect(db.engine)
            assert {"products", "orders", "order_items"} <= set(inspector.get_table_names())
            assert len(inspector.get_foreign_keys("order_items")) == 2
        checked = runner.invoke(args=["db", "check"])
        assert checked.exit_code == 0, checked.output

        client = application.test_client()
        product = client.post("/api/v1/products", json={"sku": "MIGRATED", "name": "Migrated", "price_cents": 100})
        assert product.status_code == 201, product.json
        assert product.json["qty_in_stock"] == 0 and product.json["archived"] is False
        downgraded = runner.invoke(args=["db", "downgrade", "base"])
        assert downgraded.exit_code == 0, downgraded.output
        with application.app_context():
            assert "products" not in inspect(db.engine).get_table_names()
        assert runner.invoke(args=["db", "upgrade"]).exit_code == 0
    finally:
        with application.app_context():
            db.session.remove()
            db.engine.dispose()
