"""
Ingests all registered products from the NAFDAC Greenbook
(https://greenbook.nafdac.gov.ng/) into PostgreSQL.

There is no public REST API — data is server-rendered HTML.

Strategy:
1. Fetch each category listing page (one request per category) to discover
   all product IDs + summary fields (name, form, ingredients, strength, NRN).
2. Concurrently fetch individual product detail pages for the full field set
   (ROA, applicant, manufacturer, approval date, SMPC link, etc.).
3. Upsert all records into nafdac_products.

Usage:
    python ingest_nafdac.py                    # full ingest (~11 700 products)
    python ingest_nafdac.py --listing-only     # summary fields only, ~6 requests
    python ingest_nafdac.py --workers 15       # tune concurrency (default: 10)
    python ingest_nafdac.py --category 1       # single category
"""

import argparse
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

sys.path.insert(0, "../..")
from shared.db import get_connection

BASE_URL = "https://greenbook.nafdac.gov.ng"

CATEGORIES: dict[int, str] = {
    1:  "Drugs",
    2:  "Vaccines and Biologics",
    5:  "Medical Devices",
    6:  "Veterinary",
    7:  "Herbals and Nutraceuticals",
    12: "Disinfectants",
}


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class Product:
    product_id: int
    category_id: int
    category_name: str
    product_name: str
    pharmaceutical_form: Optional[str] = None
    active_ingredients: Optional[str] = None
    strength: Optional[str] = None
    nrn: Optional[str] = None
    # enriched from detail page
    roa: Optional[str] = None
    applicant_name: Optional[str] = None
    status: Optional[str] = None
    smpc_url: Optional[str] = None
    composition: Optional[str] = None
    atc_code: Optional[str] = None
    marketing_category: Optional[str] = None
    pack_size: Optional[str] = None
    product_description: Optional[str] = None
    manufacturer_name: Optional[str] = None
    manufacturer_country: Optional[str] = None
    approval_date: Optional[str] = None
    expiry_date: Optional[str] = None


# ---------------------------------------------------------------------------
# HTTP helpers (thread-local sessions for safe concurrent use)
# ---------------------------------------------------------------------------

_local = threading.local()


def _session() -> requests.Session:
    if not hasattr(_local, "s"):
        s = requests.Session()
        retry = Retry(
            total=3,
            backoff_factor=1.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
        )
        s.mount("https://", HTTPAdapter(max_retries=retry))
        _local.s = s
    return _local.s


# ---------------------------------------------------------------------------
# HTML parsing helpers
# ---------------------------------------------------------------------------

def _strip(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _clean_html(fragment: str) -> str:
    text = re.sub(r"<[^>]+>", "", fragment)
    text = text.replace("&nbsp;", " ").replace("&#039;", "'").replace("&amp;", "&")
    return _strip(text)


def _field_after_label(html: str, label: str) -> Optional[str]:
    """Return the text of the <p> that immediately follows a labelled <h1>."""
    pattern = re.escape(label) + r"\s*</h1>\s*<p[^>]*>(.*?)</p>"
    m = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
    if not m:
        return None
    return _clean_html(m.group(1)) or None


# ---------------------------------------------------------------------------
# Listing-page scraper
# ---------------------------------------------------------------------------

# Each product card in the listing page looks like:
#   <a href=".../products/details/{id}">
#     <div class="card-body">
#       <h5>Name## <span class="form">Form</span></h5>
#       <span>Ingredient(s)</span><br/>
#       <span>Strength</span><br/>
#       <span>NRN: A4-XXXXXX</span>
#     </div>
#   </a>
_CARD_RE = re.compile(
    r'href="[^"]*/products/details/(\d+)"[^>]*>([\s\S]*?)</a>',
)


def _parse_listing(html: str, category_id: int) -> list[Product]:
    products = []
    for m in _CARD_RE.finditer(html):
        pid = int(m.group(1))
        body = m.group(2)

        # Product name + pharmaceutical form from <h5>
        h5_m = re.search(r"<h5>(.*?)</h5>", body, re.DOTALL)
        product_name: Optional[str] = None
        pharmaceutical_form: Optional[str] = None
        if h5_m:
            h5_inner = h5_m.group(1)
            form_m = re.search(r'<span class="form">(.*?)</span>', h5_inner)
            pharmaceutical_form = _clean_html(form_m.group(1)) if form_m else None
            # Remove the form span first so its text doesn't bleed into the name,
            # then strip remaining tags and trailing flag chars (##, **, #, *)
            h5_no_form = re.sub(r'<span class="form">.*?</span>', "", h5_inner, flags=re.DOTALL)
            raw_name = re.sub(r"<[^>]+>", "", h5_no_form)
            product_name = _strip(re.sub(r"\s*[#*]+\s*$", "", raw_name))

        # Bare <span> tags hold ingredients, then strength, then NRN
        bare_spans = [_strip(s) for s in re.findall(r"<span>([^<]+)</span>", body)]
        non_nrn = [s for s in bare_spans if s and not s.startswith("NRN:")]
        active_ingredients = non_nrn[0] if non_nrn else None
        strength = non_nrn[1] if len(non_nrn) > 1 else None

        nrn_m = re.search(r"NRN:\s*([\w/\-]+)", body)
        nrn = nrn_m.group(1) if nrn_m else None

        products.append(Product(
            product_id=pid,
            category_id=category_id,
            category_name=CATEGORIES[category_id],
            product_name=product_name or "",
            pharmaceutical_form=pharmaceutical_form,
            active_ingredients=active_ingredients,
            strength=strength,
            nrn=nrn,
        ))
    return products


def _fetch_category(category_id: int) -> list[Product]:
    url = f"{BASE_URL}/productCategory/products/{category_id}"
    resp = _session().get(url, timeout=60)
    resp.raise_for_status()
    return _parse_listing(resp.text, category_id)


# ---------------------------------------------------------------------------
# Detail-page enrichment
# ---------------------------------------------------------------------------

def _enrich(product: Product) -> Product:
    url = f"{BASE_URL}/products/details/{product.product_id}"
    try:
        resp = _session().get(url, timeout=20)
        resp.raise_for_status()
        html = resp.text
    except Exception as exc:
        print(f"  ! ID {product.product_id}: {exc}", flush=True)
        return product

    product.roa                = _field_after_label(html, "ROA")
    product.applicant_name     = _field_after_label(html, "Applicant Name")
    product.status             = _field_after_label(html, "Status")
    product.composition        = _field_after_label(html, "Composition")
    product.atc_code           = _field_after_label(html, "ATC Code/ATCvet Code")
    product.marketing_category = _field_after_label(html, "Marketing Category")
    product.pack_size          = _field_after_label(html, "Packsize")
    product.product_description= _field_after_label(html, "Product Description")
    product.manufacturer_name  = _field_after_label(html, "Manufacturer Name")
    product.manufacturer_country = _field_after_label(html, "Manufacturer Country")
    product.approval_date      = _field_after_label(html, "Approval Date")
    product.expiry_date        = _field_after_label(html, "Expiry Date")

    smpc_m = re.search(r'<a\s+href="([^"]+)"[^>]*>SMPC</a>', html)
    product.smpc_url = smpc_m.group(1) if smpc_m else None

    return product


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS nafdac_products (
    product_id           INTEGER      PRIMARY KEY,
    category_id          SMALLINT     NOT NULL,
    category_name        VARCHAR(100) NOT NULL,
    product_name         VARCHAR(500) NOT NULL,
    pharmaceutical_form  VARCHAR(100),
    active_ingredients   TEXT,
    strength             VARCHAR(200),
    nrn                  VARCHAR(50),
    roa                  VARCHAR(200),
    applicant_name       VARCHAR(500),
    status               VARCHAR(50),
    smpc_url             TEXT,
    composition          TEXT,
    atc_code             VARCHAR(50),
    marketing_category   VARCHAR(200),
    pack_size            VARCHAR(500),
    product_description  TEXT,
    manufacturer_name    VARCHAR(500),
    manufacturer_country VARCHAR(100),
    approval_date        DATE,
    expiry_date          DATE,
    ingested_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""

_UPSERT = """
INSERT INTO nafdac_products (
    product_id, category_id, category_name, product_name,
    pharmaceutical_form, active_ingredients, strength, nrn,
    roa, applicant_name, status, smpc_url, composition,
    atc_code, marketing_category, pack_size, product_description,
    manufacturer_name, manufacturer_country, approval_date, expiry_date
) VALUES (
    %s, %s, %s, %s,  %s, %s, %s, %s,
    %s, %s, %s, %s, %s,  %s, %s, %s, %s,
    %s, %s, %s, %s
)
ON CONFLICT (product_id) DO UPDATE SET
    category_id          = EXCLUDED.category_id,
    category_name        = EXCLUDED.category_name,
    product_name         = EXCLUDED.product_name,
    pharmaceutical_form  = EXCLUDED.pharmaceutical_form,
    active_ingredients   = EXCLUDED.active_ingredients,
    strength             = EXCLUDED.strength,
    nrn                  = EXCLUDED.nrn,
    roa                  = EXCLUDED.roa,
    applicant_name       = EXCLUDED.applicant_name,
    status               = EXCLUDED.status,
    smpc_url             = EXCLUDED.smpc_url,
    composition          = EXCLUDED.composition,
    atc_code             = EXCLUDED.atc_code,
    marketing_category   = EXCLUDED.marketing_category,
    pack_size            = EXCLUDED.pack_size,
    product_description  = EXCLUDED.product_description,
    manufacturer_name    = EXCLUDED.manufacturer_name,
    manufacturer_country = EXCLUDED.manufacturer_country,
    approval_date        = EXCLUDED.approval_date,
    expiry_date          = EXCLUDED.expiry_date,
    ingested_at          = CURRENT_TIMESTAMP
"""


def _safe_date(val: Optional[str]) -> Optional[str]:
    if not val:
        return None
    m = re.match(r"(\d{4}-\d{2}-\d{2})", val)
    return m.group(1) if m else None


def _upsert_batch(products: list[Product]) -> int:
    conn = get_connection()
    cur = conn.cursor()
    n = 0
    try:
        cur.execute(_CREATE_TABLE)
        for p in products:
            cur.execute(_UPSERT, (
                p.product_id, p.category_id, p.category_name, p.product_name,
                p.pharmaceutical_form, p.active_ingredients, p.strength, p.nrn,
                p.roa, p.applicant_name, p.status, p.smpc_url, p.composition,
                p.atc_code, p.marketing_category, p.pack_size, p.product_description,
                p.manufacturer_name, p.manufacturer_country,
                _safe_date(p.approval_date), _safe_date(p.expiry_date),
            ))
            n += 1
        conn.commit()
    except Exception as exc:
        conn.rollback()
        raise RuntimeError(f"DB error: {exc}") from exc
    finally:
        cur.close()
        conn.close()
    return n


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def ingest(
    category_ids: list[int],
    listing_only: bool = False,
    workers: int = 10,
    batch_size: int = 500,
) -> None:
    # --- Phase 1: discover product IDs from category listing pages ----------
    all_products: list[Product] = []
    for cat_id in category_ids:
        print(f"Fetching category {cat_id} ({CATEGORIES[cat_id]})...")
        products = _fetch_category(cat_id)
        print(f"  {len(products)} products")
        all_products.extend(products)

    total = len(all_products)
    print(f"\n{total} products discovered across {len(category_ids)} category(s)")

    # --- Phase 2: enrich with individual detail pages -----------------------
    if not listing_only and total > 0:
        print(f"Fetching detail pages with {workers} workers "
              f"(estimated {total / (workers * 2):.0f}s at ~2 req/s/worker)...")
        t0 = time.monotonic()
        enriched: dict[int, Product] = {}

        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(_enrich, p): p.product_id for p in all_products}
            done = 0
            for future in as_completed(futures):
                p = future.result()
                enriched[p.product_id] = p
                done += 1
                if done % 500 == 0:
                    elapsed = time.monotonic() - t0
                    rate = done / elapsed
                    eta_min = (total - done) / rate / 60 if rate else 0
                    print(f"  {done}/{total}  {rate:.0f} req/s  ETA {eta_min:.1f} min",
                          flush=True)

        all_products = [enriched.get(p.product_id, p) for p in all_products]
        elapsed = time.monotonic() - t0
        print(f"  Done in {elapsed / 60:.1f} min")

    # --- Phase 3: upsert to PostgreSQL --------------------------------------
    if not all_products:
        print("Nothing to upsert.")
        return

    print(f"\nUpserting to PostgreSQL (batch size {batch_size})...")
    total_upserted = 0
    for i in range(0, len(all_products), batch_size):
        batch = all_products[i : i + batch_size]
        n = _upsert_batch(batch)
        total_upserted += n

    print(f"\n✓ {total_upserted} records upserted to nafdac_products")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Ingest the NAFDAC Greenbook into PostgreSQL"
    )
    parser.add_argument(
        "--listing-only",
        action="store_true",
        help="Only scrape category listing pages (~6 requests, fewer fields, much faster)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=10,
        metavar="N",
        help="Concurrent workers for detail page fetching (default: 10)",
    )
    parser.add_argument(
        "--category",
        type=int,
        choices=sorted(CATEGORIES),
        metavar="ID",
        help=(
            "Ingest a single category: "
            + ", ".join(f"{k}={v}" for k, v in sorted(CATEGORIES.items()))
        ),
    )
    args = parser.parse_args()

    cats = [args.category] if args.category else sorted(CATEGORIES)
    ingest(cats, listing_only=args.listing_only, workers=args.workers)
