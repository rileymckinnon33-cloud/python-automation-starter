import csv
import datetime
import json
import mimetypes
import os
import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Dict, List, Optional

import requests

from utils.logger import get_logger

BASE_DIR = os.path.dirname(__file__)
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
API_BASE = "https://openapi.etsy.com/v3/application"
REQUEST_TIMEOUT = 30

DEFAULTS: Dict[str, Any] = {
    "etsy_api_key": "",
    "etsy_access_token": "",
    "shop_id": None,
    "inventory_file": "inventory.csv",
    "images_dir": "images",
    "save_dir": "output",
    "default_currency": "USD",
    "default_who_made": "i_did",
    "default_when_made": "made_to_order",
    "default_is_supply": False,
    "default_taxonomy_id": None,
    "default_type": "physical",
    "shipping_profile_id": None,
    "return_policy_id": None,
    "production_partner_ids": [],
    "should_auto_renew": False,
    "dry_run": True,
}


# ---------- Config ----------
def load_config() -> Dict[str, Any]:
    cfg = DEFAULTS.copy()
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            user_cfg = json.load(f)
        if user_cfg:
            cfg.update(user_cfg)
    return cfg


def make_absolute(path: Optional[str]) -> Optional[str]:
    if not path:
        return None
    if os.path.isabs(path):
        return os.path.normpath(path)
    return os.path.normpath(os.path.join(BASE_DIR, path))


TRUE_VALUES = {"true", "1", "yes", "y"}
FALSE_VALUES = {"false", "0", "no", "n"}


def parse_optional_bool(value: Optional[str]) -> Optional[bool]:
    if value is None or value == "":
        return None
    val = value.strip().lower()
    if val in TRUE_VALUES:
        return True
    if val in FALSE_VALUES:
        return False
    raise ValueError(f"Cannot parse boolean value from '{value}'")


def parse_optional_int(value: Optional[str]) -> Optional[int]:
    if value is None or value == "":
        return None
    return int(value)


def split_list_field(value: Optional[str]) -> List[str]:
    if not value:
        return []
    parts = re.split(r"[;,]", value)
    return [part.strip() for part in parts if part.strip()]


def parse_price(value: Optional[str]) -> Decimal:
    if not value:
        raise ValueError("Price is required")
    try:
        price = Decimal(value)
    except (InvalidOperation, TypeError) as exc:
        raise ValueError(f"Invalid price '{value}'") from exc
    if price <= 0:
        raise ValueError("Price must be greater than zero")
    return price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def price_to_amount(price: Decimal) -> int:
    return int((price * 100).to_integral_value(rounding=ROUND_HALF_UP))


def resolve_image_path(filename: str, images_dir: Optional[str]) -> str:
    filename = filename.strip()
    if os.path.isabs(filename):
        return os.path.normpath(filename)
    base_dir = images_dir or BASE_DIR
    return os.path.normpath(os.path.join(base_dir, filename))


# ---------- Inventory parsing ----------
def read_inventory(csv_path: str, images_dir: Optional[str], logger) -> List[Dict[str, Any]]:
    products: List[Dict[str, Any]] = []
    if not os.path.exists(csv_path):
        logger.error("Inventory file not found: %s", csv_path)
        return products

    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for line_no, row in enumerate(reader, start=2):
            title = (row.get("title") or "").strip()
            if not title:
                logger.warning("Row %s is missing a title. Skipping.", line_no)
                continue

            description = (row.get("description") or "").strip()
            if not description:
                logger.error("Row %s ('%s') is missing a description. Skipping.", line_no, title)
                continue

            try:
                price = parse_price(row.get("price"))
            except ValueError as exc:
                logger.error("Row %s ('%s') has an invalid price: %s", line_no, title, exc)
                continue

            try:
                quantity = int((row.get("quantity") or "0").strip())
            except ValueError:
                logger.error("Row %s ('%s') has an invalid quantity. Skipping.", line_no, title)
                continue
            if quantity < 0:
                logger.error("Row %s ('%s') has a negative quantity. Skipping.", line_no, title)
                continue

            product: Dict[str, Any] = {
                "title": title,
                "description": description,
                "price": price,
                "price_amount": price_to_amount(price),
                "quantity": quantity,
                "tags": split_list_field(row.get("tags")),
                "materials": split_list_field(row.get("materials")),
                "sku": (row.get("sku") or "").strip() or None,
                "taxonomy_id": None,
                "who_made": (row.get("who_made") or "").strip() or None,
                "when_made": (row.get("when_made") or "").strip() or None,
                "is_supply": None,
                "shipping_profile_id": None,
                "return_policy_id": None,
                "shop_section_id": None,
                "production_partner_ids": [],
                "type": (row.get("type") or "").strip() or None,
                "image_paths": [],
            }

            try:
                product["taxonomy_id"] = parse_optional_int((row.get("taxonomy_id") or "").strip() or None)
            except ValueError:
                logger.warning("Row %s ('%s') has an invalid taxonomy_id. Ignoring value.", line_no, title)

            try:
                parsed_supply = parse_optional_bool(row.get("is_supply"))
            except ValueError:
                logger.warning("Row %s ('%s') has an invalid is_supply value. Ignoring value.", line_no, title)
                parsed_supply = None
            product["is_supply"] = parsed_supply

            for key in ("shipping_profile_id", "return_policy_id", "shop_section_id"):
                try:
                    product[key] = parse_optional_int((row.get(key) or "").strip() or None)
                except ValueError:
                    logger.warning("Row %s ('%s') has an invalid %s. Ignoring value.", line_no, title, key)

            partner_values: List[int] = []
            if row.get("production_partner_ids"):
                for raw in split_list_field(row.get("production_partner_ids")):
                    try:
                        partner_values.append(int(raw))
                    except ValueError:
                        logger.warning(
                            "Row %s ('%s') has an invalid production_partner_id '%s'. Ignoring value.",
                            line_no,
                            title,
                            raw,
                        )
            product["production_partner_ids"] = partner_values

            image_field = row.get("image_filename") or row.get("images")
            if image_field:
                paths: List[str] = []
                for raw_name in split_list_field(image_field):
                    resolved = resolve_image_path(raw_name, images_dir)
                    if os.path.exists(resolved):
                        paths.append(resolved)
                    else:
                        logger.warning(
                            "Row %s ('%s') references missing image: %s",
                            line_no,
                            title,
                            resolved,
                        )
                product["image_paths"] = paths

            products.append(product)
    return products


# ---------- Etsy client ----------
class EtsyClient:
    def __init__(self, api_key: str, access_token: str, shop_id: Any, logger) -> None:
        if not api_key:
            raise ValueError("Missing 'etsy_api_key' in config")
        if not access_token:
            raise ValueError("Missing 'etsy_access_token' in config")
        if not shop_id:
            raise ValueError("Missing 'shop_id' in config")

        self.shop_id = str(shop_id)
        self.logger = logger
        self.session = requests.Session()
        self.session.headers.update(
            {
                "x-api-key": api_key,
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            }
        )

    @staticmethod
    def _unwrap(data: Any) -> Dict[str, Any]:
        if isinstance(data, dict) and "data" in data and isinstance(data["data"], dict):
            return data["data"]
        if isinstance(data, dict):
            return data
        raise ValueError("Unexpected response format from Etsy API")

    def create_draft_listing(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{API_BASE}/shops/{self.shop_id}/listings"
        request_payload = dict(payload)
        request_payload.setdefault("state", "draft")
        response = self.session.post(url, json=request_payload, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = self._unwrap(response.json())
        return data

    def upload_images(self, listing_id: Any, image_paths: List[str]) -> List[Any]:
        if not image_paths:
            return []

        uploaded: List[Any] = []
        for position, path in enumerate(image_paths, start=1):
            if not os.path.exists(path):
                self.logger.warning("Image path no longer exists: %s", path)
                continue
            mime_type = mimetypes.guess_type(path)[0] or "application/octet-stream"
            url = f"{API_BASE}/shops/{self.shop_id}/listings/{listing_id}/images"
            with open(path, "rb") as fh:
                files = {"image": (os.path.basename(path), fh, mime_type)}
                data = {"rank": position}
                response = self.session.post(url, data=data, files=files, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            payload = self._unwrap(response.json())
            uploaded.append(payload.get("listing_image_id") or payload.get("image_id"))
        return uploaded


# ---------- Payload building ----------
def resolve_listing_value(product: Dict[str, Any], config: Dict[str, Any], key: str) -> Any:
    if product.get(key) is not None:
        return product[key]
    return config.get(key)


def build_listing_payload(product: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "quantity": product["quantity"],
        "title": product["title"],
        "description": product["description"],
        "who_made": product.get("who_made") or config["default_who_made"],
        "when_made": product.get("when_made") or config["default_when_made"],
        "is_supply": (
            product["is_supply"]
            if product["is_supply"] is not None
            else config["default_is_supply"]
        ),
        "type": product.get("type") or config["default_type"],
        "should_auto_renew": config.get("should_auto_renew", False),
        "state": "draft",
        "price": {
            "amount": product["price_amount"],
            "currency_code": config.get("default_currency", "USD"),
        },
    }

    taxonomy_id = product.get("taxonomy_id") or config.get("default_taxonomy_id")
    if taxonomy_id:
        payload["taxonomy_id"] = taxonomy_id

    for list_field in ("tags", "materials"):
        if product[list_field]:
            payload[list_field] = product[list_field]

    for field in ("shipping_profile_id", "return_policy_id", "shop_section_id"):
        value = resolve_listing_value(product, config, field)
        if value:
            payload[field] = value

    partners = product.get("production_partner_ids") or config.get("production_partner_ids")
    if partners:
        payload["production_partner_ids"] = partners

    if product.get("sku"):
        payload.setdefault("inventory", {"products": []})
        payload["inventory"]["products"].append(
            {
                "sku": product["sku"],
                "property_values": [],
                "offerings": [
                    {
                        "price": {
                            "amount": product["price_amount"],
                            "currency_code": config.get("default_currency", "USD"),
                        },
                        "quantity": product["quantity"],
                        "is_enabled": True,
                    }
                ],
            }
        )

    return payload


def save_run_summary(results: List[Dict[str, Any]], dry_run: bool, save_dir: str) -> str:
    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    summary = {
        "run_at": datetime.datetime.now().isoformat(),
        "dry_run": dry_run,
        "results": results,
    }
    os.makedirs(save_dir, exist_ok=True)
    path = os.path.join(save_dir, f"etsy_run_{timestamp}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    return path


# ---------- Main ----------
def main() -> None:
    logger = get_logger()
    config = load_config()

    inventory_path = make_absolute(config.get("inventory_file")) or ""
    images_dir = make_absolute(config.get("images_dir"))
    save_dir = make_absolute(config.get("save_dir")) or os.path.join(BASE_DIR, "output")
    os.makedirs(save_dir, exist_ok=True)

    products = read_inventory(inventory_path, images_dir, logger)
    if not products:
        logger.warning("No valid products found. Nothing to do.")
        return

    results: List[Dict[str, Any]] = []
    client: Optional[EtsyClient] = None

    if not config.get("dry_run", True):
        try:
            client = EtsyClient(
                api_key=config.get("etsy_api_key", ""),
                access_token=config.get("etsy_access_token", ""),
                shop_id=config.get("shop_id"),
                logger=logger,
            )
        except ValueError as exc:
            logger.error("Configuration error: %s", exc)
            return

    for product in products:
        try:
            payload = build_listing_payload(product, config)
        except Exception as exc:  # Catch unexpected data issues per row
            logger.exception("Failed to build payload for '%s': %s", product["title"], exc)
            results.append(
                {
                    "title": product["title"],
                    "status": "error",
                    "error": str(exc),
                }
            )
            continue

        if config.get("dry_run", True):
            logger.info(
                "Dry run: would create listing '%s' (qty=%s, price=%s %s)",
                product["title"],
                product["quantity"],
                product["price"],
                config.get("default_currency", "USD"),
            )
            results.append(
                {
                    "title": product["title"],
                    "status": "dry_run",
                    "quantity": product["quantity"],
                    "price": str(product["price"]),
                }
            )
            continue

        if client is None:
            logger.error("Etsy client is not initialized. Aborting run.")
            return

        try:
            listing_data = client.create_draft_listing(payload)
            listing_id = listing_data.get("listing_id") or listing_data.get("id")
            logger.info("Created Etsy listing %s for '%s'", listing_id, product["title"])
            entry: Dict[str, Any] = {
                "title": product["title"],
                "status": "created",
                "listing_id": listing_id,
                "quantity": product["quantity"],
                "price": str(product["price"]),
            }

            if product.get("image_paths"):
                try:
                    uploaded = client.upload_images(listing_id, product["image_paths"])
                    entry["images_uploaded"] = uploaded
                    logger.info(
                        "Uploaded %s image(s) for listing %s", len(uploaded), listing_id
                    )
                except requests.HTTPError as exc:
                    logger.exception(
                        "Failed to upload images for listing %s ('%s'): %s",
                        listing_id,
                        product["title"],
                        exc,
                    )
                    entry["image_error"] = str(exc)
            results.append(entry)
        except requests.HTTPError as exc:
            logger.exception("Etsy API error for '%s': %s", product["title"], exc)
            results.append(
                {
                    "title": product["title"],
                    "status": "error",
                    "error": str(exc),
                }
            )
        except Exception as exc:
            logger.exception("Unexpected error for '%s': %s", product["title"], exc)
            results.append(
                {
                    "title": product["title"],
                    "status": "error",
                    "error": str(exc),
                }
            )

    summary_path = save_run_summary(results, config.get("dry_run", True), save_dir)
    logger.info("Run summary saved to %s", summary_path)


if __name__ == "__main__":
    main()
