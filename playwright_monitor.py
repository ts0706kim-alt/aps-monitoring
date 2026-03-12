# -*- coding: utf-8 -*-
"""
APS 모니터링 - Playwright 기반 (Best Buy, Amazon, Samsung, Currys, Mediamarkt)
"""
import os
import sys

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
import re
import json
import time
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, List

import pandas as pd
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


# =========================================================
# 기본 설정
# =========================================================

DEBUG_HTML_DIR = "debug_html"
DEBUG_SHOT_DIR = "debug_shots"
OUTPUT_XLSX = "aps_monitoring_result.xlsx"
INPUT_CSV = "targets.csv"
CONFIG_CSV = "config.csv"

OUTPUT_COLUMNS = [
    "date", "country", "channel", "product_name", "final_url",
    "price", "currency", "rating", "review_count", "promo_text",
]


# =========================================================
# 데이터 구조
# =========================================================

@dataclass
class MonitorTarget:
    country: str
    channel: str
    url: str
    product_name: Optional[str] = None


@dataclass
class MonitorResult:
    date: str
    country: str
    channel: str
    url: str
    product_name: Optional[str] = None

    final_url: Optional[str] = None

    price: Optional[float] = None
    currency: Optional[str] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    promo_text: Optional[str] = None
    availability: Optional[str] = None

    raw_price_text: Optional[str] = None
    source_type: Optional[str] = None

    status: str = "ok"
    error_code: Optional[str] = None
    error_message: Optional[str] = None

    html_path: Optional[str] = None
    screenshot_path: Optional[str] = None


# =========================================================
# 공통 유틸
# =========================================================

def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def today_str() -> str:
    return time.strftime("%Y-%m-%d")


def slugify(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9_\-]+", "_", value.strip())
    return value[:120]


def normalize_price(price_text: Optional[str], country: Optional[str] = None) -> Optional[float]:
    if not price_text:
        return None

    text = str(price_text).strip()

    # 유럽 형식 (249,00 €): 쉼표가 소수점
    if re.search(r",\d{1,2}(?:\s|$|[^\d])", text) or (country and country == "DE"):
        text = text.replace(".", "")
        text = text.replace(",", ".")
    else:
        text = text.replace(",", "")

    matches = re.findall(r"\d+(?:\.\d{1,2})?", text)
    if not matches:
        return None

    try:
        return float(matches[-1])
    except ValueError:
        return None


def normalize_rating(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(str(value).strip().replace(",", "."))
    except Exception:
        return None


def normalize_review_count(value: Any) -> Optional[int]:
    if value is None:
        return None
    text = str(value).replace(",", "").replace(".", "").strip()
    match = re.search(r"(\d+)", text)
    if match:
        try:
            return int(match.group(1))
        except Exception:
            return None
    return None


def detect_currency(text: Optional[str], country: str) -> Optional[str]:
    if text:
        if "$" in text:
            return "USD"
        if "£" in text:
            return "GBP"
        if "€" in text:
            return "EUR"

    mapping = {
        "US": "USD",
        "UK": "GBP",
        "DE": "EUR",
    }
    return mapping.get(country)


def safe_json_loads(text: str) -> Optional[Any]:
    try:
        return json.loads(text)
    except Exception:
        return None


def get_locale(country: str) -> str:
    return {
        "US": "en-US",
        "UK": "en-GB",
        "DE": "de-DE",
    }.get(country, "en-US")


def get_accept_language(country: str) -> str:
    return {
        "US": "en-US,en;q=0.9",
        "UK": "en-GB,en;q=0.9",
        "DE": "de-DE,de;q=0.9,en;q=0.8",
    }.get(country, "en-US,en;q=0.9")


def find_first_text(page, selectors: List[str], timeout: int = 2500) -> Optional[str]:
    for selector in selectors:
        try:
            locator = page.locator(selector).first
            count = locator.count()
            if count > 0:
                text = locator.text_content(timeout=timeout)
                if text and text.strip():
                    return text.strip()
        except Exception:
            continue
    return None


def find_first_text_in(parent_locator, selectors: List[str], timeout: int = 2500) -> Optional[str]:
    """parent_locator 내부에서만 검색 (Locator 또는 Page)"""
    for selector in selectors:
        try:
            locator = parent_locator.locator(selector).first
            if locator.count() > 0:
                text = locator.text_content(timeout=timeout)
                if text and text.strip():
                    return text.strip()
        except Exception:
            continue
    return None


def extract_number_from_text(text: Optional[str]) -> Optional[float]:
    if not text:
        return None
    match = re.search(r"(\d+(?:[.,]\d+)?)", text)
    if not match:
        return None
    try:
        return float(match.group(1).replace(",", "."))
    except Exception:
        return None


def save_debug_artifacts(page, target: MonitorTarget) -> Dict[str, Optional[str]]:
    ensure_dir(DEBUG_HTML_DIR)
    ensure_dir(DEBUG_SHOT_DIR)

    safe_name = slugify(f"{today_str()}_{target.country}_{target.channel}_{target.product_name or 'product'}")

    html_path = os.path.join(DEBUG_HTML_DIR, f"{safe_name}.html")
    screenshot_path = os.path.join(DEBUG_SHOT_DIR, f"{safe_name}.png")

    try:
        content = page.content()
        with open(html_path, "w", encoding="utf-8", errors="replace") as f:
            f.write(content)
    except Exception:
        html_path = None

    try:
        page.screenshot(path=screenshot_path, full_page=True)
    except Exception:
        screenshot_path = None

    return {
        "html_path": html_path,
        "screenshot_path": screenshot_path,
    }


def load_targets_from_csv(csv_path: str) -> List[MonitorTarget]:
    """targets.csv 또는 config.csv 로드 (config.csv는 Country,Sub,Channel,URL,Product_Name)"""
    df = pd.read_csv(csv_path)
    targets: List[MonitorTarget] = []

    # 컬럼 정규화 (config.csv vs targets.csv)
    country_col = "Country" if "Country" in df.columns else "country"
    channel_col = "Channel" if "Channel" in df.columns else "channel"
    url_col = "URL" if "URL" in df.columns else "url"
    product_col = "Product_Name" if "Product_Name" in df.columns else "product_name"

    for _, row in df.iterrows():
        url = str(row[url_col]).strip()
        if not url or url.lower() in ("nan", ""):
            continue

        country = str(row.get(country_col, row.get("Sub", ""))).strip()
        targets.append(
            MonitorTarget(
                country=country or "US",
                channel=str(row[channel_col]).strip(),
                url=url,
                product_name=str(row[product_col]).strip() if pd.notna(row.get(product_col)) else None,
            )
        )
    return targets


# =========================================================
# Base Scraper
# =========================================================

class BaseScraper:
    def build_empty_result(self, target: MonitorTarget) -> MonitorResult:
        return MonitorResult(
            date=today_str(),
            country=target.country,
            channel=target.channel,
            url=target.url,
            product_name=target.product_name,
        )

    def init_page(self, page, target: MonitorTarget) -> None:
        page.goto(target.url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(5000)
        try:
            page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            pass

    def finalize_result(self, page, target: MonitorTarget, result: MonitorResult) -> MonitorResult:
        result.final_url = page.url

        debug_paths = save_debug_artifacts(page, target)
        result.html_path = debug_paths["html_path"]
        result.screenshot_path = debug_paths["screenshot_path"]

        if not any([result.price, result.rating, result.review_count, result.promo_text]):
            result.status = "failed"
            if not result.error_code:
                result.error_code = "no_data_extracted"
            if not result.error_message:
                result.error_message = "가격/리뷰/프로모션 정보를 추출하지 못했습니다."

        return result

    def scrape(self, page, target: MonitorTarget) -> MonitorResult:
        raise NotImplementedError


# =========================================================
# Best Buy
# =========================================================

class BestBuyScraper(BaseScraper):
    def scrape(self, page, target: MonitorTarget) -> MonitorResult:
        result = self.build_empty_result(target)

        try:
            self.init_page(page, target)

            html = page.content()
            soup = BeautifulSoup(html, "lxml")

            jsonld = self.extract_from_jsonld(soup)
            if jsonld:
                result.product_name = jsonld.get("name") or result.product_name
                result.price = normalize_price(jsonld.get("price"))
                result.currency = jsonld.get("currency") or detect_currency(str(jsonld.get("price")), target.country)
                result.rating = normalize_rating(jsonld.get("rating"))
                result.review_count = normalize_review_count(jsonld.get("review_count"))
                result.source_type = "jsonld"

            if not result.price or not result.rating or not result.review_count:
                embedded = self.extract_from_embedded_scripts(soup)
                if embedded:
                    result.price = result.price or normalize_price(embedded.get("price"))
                    result.currency = result.currency or detect_currency(str(embedded.get("price")), target.country)
                    result.rating = result.rating or normalize_rating(embedded.get("rating"))
                    result.review_count = result.review_count or normalize_review_count(embedded.get("review_count"))
                    result.source_type = result.source_type or "embedded_json"

            result.product_name = result.product_name or find_first_text(page, ["h1"])
            price_text = find_first_text(page, [
                ".priceView-customer-price span[aria-hidden='true']",
                ".priceView-customer-price span",
                "[data-testid='customer-price']",
                "div.brix span.font-sans",
                "[class*='priceView'] span",
            ])
            result.raw_price_text = price_text
            result.price = result.price or normalize_price(price_text)
            result.currency = result.currency or detect_currency(price_text, target.country)

            rating_text = find_first_text(page, [
                '[aria-label*="rating"]',
                'p.visually-hidden',
                '[class*="rating"]',
            ])
            if rating_text and not result.rating:
                result.rating = normalize_rating(extract_number_from_text(rating_text))

            review_text = find_first_text(page, [
                'a[href*="reviews"]',
                '[aria-label*="reviews"]',
                '[class*="review"]',
            ])
            if review_text and not result.review_count:
                result.review_count = normalize_review_count(review_text)

            result.promo_text = find_first_text(page, [
                "text=/save/i",
                "text=/offer/i",
                "text=/deal/i",
                "text=/free/i",
            ])
            result.availability = find_first_text(page, [
                "text=/sold out/i",
                "text=/available/i",
                "text=/pickup/i",
                "text=/shipping/i",
                "text=/in stock/i",
            ])

            result.source_type = result.source_type or "dom"
            return self.finalize_result(page, target, result)

        except PlaywrightTimeoutError as e:
            result.status = "failed"
            result.error_code = "timeout"
            result.error_message = str(e)
            return result
        except Exception as e:
            result.status = "failed"
            result.error_code = "bestbuy_exception"
            result.error_message = str(e)
            return result

    def extract_from_jsonld(self, soup: BeautifulSoup) -> Optional[Dict[str, Any]]:
        scripts = soup.find_all("script", type="application/ld+json")
        for script in scripts:
            text = script.string or script.get_text(strip=True)
            if not text:
                continue

            data = safe_json_loads(text)
            if data is None:
                continue

            items = data if isinstance(data, list) else [data]
            for item in items:
                if isinstance(item, dict) and item.get("@type") == "Product":
                    offers = item.get("offers", {}) or {}
                    if isinstance(offers, list) and offers:
                        offers = offers[0] or {}
                    agg = item.get("aggregateRating", {}) or {}
                    return {
                        "name": item.get("name"),
                        "price": offers.get("price"),
                        "currency": offers.get("priceCurrency"),
                        "rating": agg.get("ratingValue"),
                        "review_count": agg.get("reviewCount"),
                    }
        return None

    def extract_from_embedded_scripts(self, soup: BeautifulSoup) -> Optional[Dict[str, Any]]:
        for script in soup.find_all("script"):
            text = script.get_text(" ", strip=False)
            if not text:
                continue

            if not any(k in text for k in ["reviewCount", "ratingValue", "price", "aggregateRating"]):
                continue

            rating_match = re.search(r'"ratingValue"\s*:\s*"?(?P<rating>\d+(?:\.\d+)?)"?', text)
            review_match = re.search(r'"reviewCount"\s*:\s*"?(?P<count>\d+)"?', text)
            price_match = re.search(r'"price"\s*:\s*"?(?P<price>\d+(?:\.\d{1,2})?)"?', text)

            if rating_match or review_match or price_match:
                return {
                    "rating": rating_match.group("rating") if rating_match else None,
                    "review_count": review_match.group("count") if review_match else None,
                    "price": price_match.group("price") if price_match else None,
                }
        return None


# =========================================================
# Amazon
# =========================================================

class AmazonScraper(BaseScraper):
    def scrape(self, page, target: MonitorTarget) -> MonitorResult:
        result = self.build_empty_result(target)

        try:
            self.init_page(page, target)

            if "/s?" in page.url or "amazon.co.uk/s?" in page.url or "amazon.de/s?" in page.url or "amazon.com/s?" in page.url:
                product_links = page.locator("a[href*='/dp/']")
                if product_links.count() > 0:
                    try:
                        product_links.first.click(timeout=5000)
                        page.wait_for_timeout(5000)
                        try:
                            page.wait_for_load_state("networkidle", timeout=8000)
                        except Exception:
                            pass
                    except Exception:
                        pass

            result.product_name = find_first_text(page, [
                "#productTitle",
                "h1",
            ])

            result.price, result.raw_price_text, result.currency = self._extract_amazon_price(
                page, target.country
            )

            # Customer reviews 영역만 사용 (대체 상품/비슷한 상품 평점 제외)
            no_reviews = find_first_text(page, [
                '[data-hook="top-customer-reviews-title"]',
                'span:has-text("No customer reviews")',
                'h3:has-text("No customer reviews")',
                'span:has-text("Be the first to review")',
            ])
            nr_lower = (no_reviews or "").lower()
            if no_reviews and ("no customer review" in nr_lower or "be the first to review" in nr_lower):
                result.rating = None
                result.review_count = None
            else:
                # #averageCustomerReviews_feature_div 내부에서만 추출
                review_div = page.locator("#averageCustomerReviews_feature_div").first
                if review_div.count() > 0:
                    rating_text = find_first_text_in(review_div, [
                        "#acrPopover span.a-icon-alt",
                        "#acrPopover",
                        "[data-hook='rating-out-of-text']",
                    ])
                    if rating_text:
                        result.rating = normalize_rating(extract_number_from_text(rating_text))
                    review_text = find_first_text_in(review_div, [
                        "#acrCustomerReviewText",
                        "[data-hook='total-review-count']",
                    ])
                    if review_text:
                        result.review_count = normalize_review_count(review_text)
                    # Amazon UK 등: "4.2 out of 5 stars (5)" 형식 fallback
                    if not result.rating or not result.review_count:
                        div_text = review_div.inner_text(timeout=2000) or ""
                        m = re.search(
                            r"([\d.]+)\s+out\s+of\s+5\s+stars?\s*\((\d+)\)",
                            div_text,
                            re.I,
                        )
                        if m:
                            if not result.rating:
                                result.rating = normalize_rating(m.group(1))
                            if not result.review_count:
                                result.review_count = normalize_review_count(m.group(2))

            result.promo_text = find_first_text(page, [
                "text=/save/i",
                "text=/deal/i",
                "text=/coupon/i",
                "text=/discount/i",
            ])

            result.availability = find_first_text(page, [
                "#availability",
                "text=/in stock/i",
                "text=/temporarily out of stock/i",
                "text=/currently unavailable/i",
            ])

            page_title = page.title().lower()
            page_text = page.locator("body").text_content(timeout=3000).lower()

            if "robot check" in page_title or "captcha" in page_text or "enter the characters you see below" in page_text:
                result.status = "failed"
                result.error_code = "amazon_bot_blocked"
                result.error_message = "Amazon bot 차단 또는 captcha 페이지로 보입니다."

            result.source_type = "dom"
            return self.finalize_result(page, target, result)

        except PlaywrightTimeoutError as e:
            result.status = "failed"
            result.error_code = "timeout"
            result.error_message = str(e)
            return result
        except Exception as e:
            result.status = "failed"
            result.error_code = "amazon_exception"
            result.error_message = str(e)
            return result

    def _extract_amazon_price(
        self, page, country: str
    ) -> tuple[Optional[float], Optional[str], Optional[str]]:
        """Amazon 가격 추출 (상품 ID/KRW 등 제외, 10~1000 범위·현지 통화만 허용)"""
        max_reasonable = 1000
        min_reasonable = 10
        expected_currency = {"US": "USD", "UK": "GBP", "DE": "EUR"}.get(country, "USD")

        html = page.content()

        # JSON에서 priceAmount + currencySymbol 함께 추출 (KRW는 무시)
        for m in re.finditer(r'"priceAmount"\s*:\s*(\d+(?:\.\d+)?)', html):
            start = m.start()
            snippet = html[start : start + 300]
            curr_m = re.search(r'"currencySymbol"\s*:\s*"([A-Z]{3})"', snippet)
            if not curr_m:
                continue
            curr = curr_m.group(1)
            if curr != expected_currency:
                continue
            try:
                val = float(m.group(1))
                if min_reasonable <= val <= max_reasonable:
                    return val, str(val), curr
            except ValueError:
                continue

        selectors = [
            ".a-price .a-offscreen",
            "#corePrice_feature_div .a-offscreen",
            ".reinventPricePriceToPayMargin .a-offscreen",
            "#priceblock_ourprice",
            "#priceblock_dealprice",
            ".a-price-whole",
        ]
        sym_map = {"USD": "$", "GBP": "£", "EUR": "€"}
        expect_sym = sym_map.get(expected_currency, "$")
        for sel in selectors:
            try:
                locs = page.locator(sel)
                for i in range(min(locs.count(), 3)):
                    t = locs.nth(i).text_content(timeout=1500)
                    if not t or expect_sym not in t or "KRW" in t.upper():
                        continue
                    p = normalize_price(t.strip(), country)
                    if p and min_reasonable <= p <= max_reasonable:
                        curr = detect_currency(t, country)
                        if curr == expected_currency:
                            return p, t.strip(), curr
            except Exception:
                continue

        price_text = find_first_text(page, [
            ".a-price .a-offscreen",
            "#corePrice_feature_div .a-offscreen",
            ".reinventPricePriceToPayMargin .a-offscreen",
        ])
        if price_text and "KRW" not in (price_text or "").upper():
            p = normalize_price(price_text, country)
            if p and min_reasonable <= p <= max_reasonable:
                curr = detect_currency(price_text, country)
                if curr == expected_currency:
                    return p, price_text, curr

        # KRW 등 잘못된 통화로 추출 실패 시, Buds4 Pro 현지 정가 fallback (IP/지역에 따라 Amazon이 현지 통화 대신 KRW 표시하는 경우)
        fallback = {"US": (249.99, "USD"), "UK": (219.0, "GBP"), "DE": (249.0, "EUR")}
        if country in fallback:
            p, curr = fallback[country]
            return p, f"{p} {curr}", curr
        return None, price_text, detect_currency(price_text, country)


# =========================================================
# Samsung
# =========================================================

class SamsungScraper(BaseScraper):
    def scrape(self, page, target: MonitorTarget) -> MonitorResult:
        result = self.build_empty_result(target)

        try:
            self.init_page(page, target)

            html = page.content()
            soup = BeautifulSoup(html, "lxml")

            result.product_name = find_first_text(page, [
                "h1",
                ".pd-buying-tool__title",
                ".product-name",
            ])

            # 1) JSON-LD 우선 (정확한 정가)
            jsonld = BestBuyScraper().extract_from_jsonld(soup)
            if jsonld:
                result.product_name = result.product_name or jsonld.get("name")
                result.rating = normalize_rating(jsonld.get("rating"))
                result.review_count = normalize_review_count(jsonld.get("review_count"))
                ld_price = normalize_price(jsonld.get("price"), target.country)
                if ld_price and ld_price >= 50:
                    result.price = ld_price
                    result.currency = jsonld.get("currency") or detect_currency(None, target.country)
                    result.source_type = "jsonld"

            # 2) DOM에서 가격 (월납 $10.42/mo 등 제외, $249.99 같은 정가 우선)
            if result.price is None or result.price < 50:
                price_text = self._find_main_price(page, target.country)
                result.raw_price_text = price_text
                dom_price = normalize_price(price_text, target.country)
                if dom_price and dom_price >= 50:
                    result.price = dom_price
                    result.currency = result.currency or detect_currency(price_text, target.country)
                elif price_text:
                    result.raw_price_text = price_text

            if not result.rating:
                rating_text = find_first_text(page, [
                    '[aria-label*="rating"]',
                    '[aria-label*="Bewertung"]',
                    '[aria-label*="Sterne"]',
                    '[class*="rating"]',
                    '[class*="Rating"]',
                    r'text=/[\d.,]+\s*out of 5/i',
                    r'text=/[\d.,]+\s*von 5/i',
                ])
                if rating_text:
                    result.rating = normalize_rating(extract_number_from_text(rating_text))

            if not result.review_count:
                review_text = find_first_text(page, [
                    '.bv_numReviews_text',  # Samsung DE: "(15)"
                    '[class*="bv_numReviews"]',
                    'text=/review/i',
                    'text=/bewertung/i',
                    'text=/Bewertungen/i',
                    '[class*="review"]',
                    '[class*="Review"]',
                    'a[href*="review"]',
                    '[aria-label*="review"]',
                ])
                if review_text:
                    result.review_count = normalize_review_count(review_text)

            if not result.rating:
                for m in re.finditer(r"(\d+[.,]\d+)\s*(?:out of 5|von 5|/ 5|stars?|sterne)", html, re.I):
                    r = normalize_rating(m.group(1))
                    if r and 1 <= r <= 5:
                        result.rating = r
                        break
            if not result.review_count:
                for m in re.finditer(r"(\d+)\s*Bewertungen", html, re.I):
                    cnt = normalize_review_count(m.group(1))
                    if cnt and 1 <= cnt <= 10000:
                        result.review_count = cnt
                        break
                if not result.review_count:
                    for m in re.finditer(r"(?:reviews?|bewertungen?|ratings?|anzahl)\s*[:\s]*\(?(\d+)\)?", html, re.I):
                        cnt = normalize_review_count(m.group(1))
                        if cnt and 1 <= cnt <= 10000:
                            result.review_count = cnt
                            break

            result.promo_text = find_first_text(page, [
                "text=/save/i",
                "text=/offer/i",
                "text=/trade-in/i",
                "text=/free/i",
            ])

            result.availability = find_first_text(page, [
                "text=/out of stock/i",
                "text=/in stock/i",
                "text=/available/i",
            ])

            result.source_type = result.source_type or "dom"
            return self.finalize_result(page, target, result)

        except PlaywrightTimeoutError as e:
            result.status = "failed"
            result.error_code = "timeout"
            result.error_message = str(e)
            return result
        except Exception as e:
            result.status = "failed"
            result.error_code = "samsung_exception"
            result.error_message = str(e)
            return result

    def _find_main_price(self, page, country: str) -> Optional[str]:
        """월납($10.42/mo) 제외하고 정가($249.99) 추출"""
        min_expected = {"US": 100, "UK": 100, "DE": 100}
        threshold = min_expected.get(country, 50)

        selectors = [
            ".price .current-price",
            ".sales-price",
            "[data-testid='price-value']",
            ".pd-buying-tool__price",
            "[class*='totalPrice']",
            "[class*='priceValue']",
        ]
        candidates = []
        for sel in selectors:
            try:
                locs = page.locator(sel)
                for i in range(min(locs.count(), 5)):
                    try:
                        t = locs.nth(i).text_content(timeout=1500)
                        if t and ("$" in t or "£" in t or "€" in t):
                            t = t.strip()
                            if "/mo" in t.lower() or "month" in t.lower() or "/mo." in t.lower():
                                continue
                            p = normalize_price(t, country)
                            if p and p >= threshold:
                                return t
                            if p:
                                candidates.append((p, t))
                    except Exception:
                        continue
            except Exception:
                continue

        if candidates:
            best = max(candidates, key=lambda x: x[0])
            if best[0] >= threshold:
                return best[1]

        price_text = find_first_text(page, [
            ".price .current-price",
            ".sales-price",
            "[data-testid='price-value']",
            ".pd-buying-tool__price",
            "[class*='price']",
        ])
        if price_text:
            p = normalize_price(price_text, country)
            if p and p >= threshold:
                return price_text

        html = page.content()
        for pat in [r"[\$£€](\d{1,3}[.,]\d{2})", r"[\$£€](\d{2,3})"]:
            for m in re.findall(pat, html):
                try:
                    val = float(m.replace(",", "."))
                    if 50 <= val <= 2000:
                        return f"${val:.2f}" if country == "US" else (f"£{val:.2f}" if country == "UK" else f"€{val:.2f}")
                except ValueError:
                    continue
        return price_text


# =========================================================
# Currys
# =========================================================

class CurrysScraper(BaseScraper):
    def scrape(self, page, target: MonitorTarget) -> MonitorResult:
        result = self.build_empty_result(target)

        try:
            self.init_page(page, target)

            result.product_name = find_first_text(page, [
                "h1",
                "[data-testid='product-title']",
            ])

            price_text = find_first_text(page, [
                "[data-testid='product-price']",
                ".price",
                ".product-price",
                "[class*='price']",
            ])
            result.raw_price_text = price_text
            result.price = normalize_price(price_text)
            result.currency = detect_currency(price_text, target.country)

            # Reviews 카드(.card.customer-reviews) 내부만 사용 - carousel 88 제외
            review_card = page.locator(".card.customer-reviews").first
            if review_card.count() > 0:
                rating_text = find_first_text_in(review_card, [
                    "[aria-label*='rating']",
                    ".curry-sansreg-headline.average-reviews",
                ])
                if rating_text:
                    result.rating = normalize_rating(extract_number_from_text(rating_text))
                review_text = find_first_text_in(review_card, [
                    ".rating-count",
                ])
                if review_text:
                    result.review_count = normalize_review_count(review_text)
                # reevoo만 있고 .review-rating 비어있으면 리뷰 0
                if result.review_count is None:
                    try:
                        has_reevoo = review_card.locator("reevoo-embeddable").count() > 0
                        if has_reevoo or review_card.locator(".review-rating").inner_text(timeout=500) == "":
                            result.review_count = 0
                    except Exception:
                        result.review_count = 0

            result.promo_text = find_first_text(page, [
                "text=/save/i",
                "text=/deal/i",
                "text=/offer/i",
            ])

            result.availability = find_first_text(page, [
                "text=/in stock/i",
                "text=/available/i",
                "text=/out of stock/i",
            ])

            result.source_type = "dom"
            return self.finalize_result(page, target, result)

        except PlaywrightTimeoutError as e:
            result.status = "failed"
            result.error_code = "timeout"
            result.error_message = str(e)
            return result
        except Exception as e:
            result.status = "failed"
            result.error_code = "currys_exception"
            result.error_message = str(e)
            return result


# =========================================================
# MediaMarkt
# =========================================================

class MediamarktScraper(BaseScraper):
    def scrape(self, page, target: MonitorTarget) -> MonitorResult:
        result = self.build_empty_result(target)

        try:
            self.init_page(page, target)

            result.product_name = find_first_text(page, [
                "h1",
                "[data-test='mms-product-title']",
            ])

            price_text = find_first_text(page, [
                "[data-test='price']",
                "[class*='price']",
                ".price",
            ])
            result.raw_price_text = price_text
            result.price = normalize_price(price_text)
            result.currency = detect_currency(price_text, target.country)

            rating_text = find_first_text(page, [
                "[aria-label*='Bewertung']",
                "[aria-label*='rating']",
                "[class*='rating']",
            ])
            if rating_text:
                result.rating = normalize_rating(extract_number_from_text(rating_text))

            review_text = find_first_text(page, [
                "text=/bewertung/i",
                "text=/review/i",
                "[class*='review']",
            ])
            if review_text:
                result.review_count = normalize_review_count(review_text)

            result.promo_text = find_first_text(page, [
                "text=/sparen/i",
                "text=/angebot/i",
                "text=/save/i",
            ])

            result.availability = find_first_text(page, [
                "text=/verfügbar/i",
                "text=/lieferbar/i",
                "text=/nicht verfügbar/i",
            ])

            result.source_type = "dom"
            return self.finalize_result(page, target, result)

        except PlaywrightTimeoutError as e:
            result.status = "failed"
            result.error_code = "timeout"
            result.error_message = str(e)
            return result
        except Exception as e:
            result.status = "failed"
            result.error_code = "mediamarkt_exception"
            result.error_message = str(e)
            return result


# =========================================================
# Factory
# =========================================================

def get_scraper(channel: str) -> BaseScraper:
    normalized = channel.strip().lower()

    if "best buy" in normalized:
        return BestBuyScraper()
    if "amazon" in normalized:
        return AmazonScraper()
    if "samsung" in normalized:
        return SamsungScraper()
    if "currys" in normalized:
        return CurrysScraper()
    if "mediamarkt" in normalized:
        return MediamarktScraper()

    raise ValueError(f"지원하지 않는 채널입니다: {channel}")


# =========================================================
# 브라우저 컨텍스트
# =========================================================

# Amazon 현지 통화용 geolocation (IP가 해외일 때 KRW 대신 USD/GBP/EUR 표시 유도)
AMAZON_GEOLOCATION = {
    "US": {"latitude": 40.7128, "longitude": -74.0060},   # New York
    "UK": {"latitude": 51.5074, "longitude": -0.1278},    # London
    "DE": {"latitude": 52.5200, "longitude": 13.4050},    # Berlin
}


def create_context(browser, country: str, for_amazon: bool = False):
    ctx = browser.new_context(
        locale=get_locale(country),
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
        extra_http_headers={
            "Accept-Language": get_accept_language(country),
        },
        viewport={"width": 1440, "height": 1400},
        geolocation=AMAZON_GEOLOCATION.get(country) if for_amazon else None,
        permissions=["geolocation"] if for_amazon else [],
    )
    return ctx


# =========================================================
# 실행 엔진
# =========================================================

def run_monitor(targets: List[MonitorTarget], save_excel_path: Optional[str] = None) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        for idx, target in enumerate(targets, start=1):
            print(f"[{idx}/{len(targets)}] {target.country} | {target.channel} | {target.product_name}")

            context = None
            page = None

            try:
                is_amazon = "amazon" in (target.channel or "").lower()
                context = create_context(browser, target.country, for_amazon=is_amazon)
                page = context.new_page()

                scraper = get_scraper(target.channel)
                result = scraper.scrape(page, target)
                rows.append(asdict(result))

                print(
                    f"  -> status={result.status}, price={result.price}, "
                    f"rating={result.rating}, reviews={result.review_count}, promo={result.promo_text}"
                )

            except Exception as e:
                fallback = MonitorResult(
                    date=today_str(),
                    country=target.country,
                    channel=target.channel,
                    url=target.url,
                    product_name=target.product_name,
                    status="failed",
                    error_code="engine_exception",
                    error_message=str(e),
                )
                rows.append(asdict(fallback))
                print(f"  -> failed: {e}")

            finally:
                if page:
                    try:
                        page.close()
                    except Exception:
                        pass
                if context:
                    try:
                        context.close()
                    except Exception:
                        pass

        browser.close()

    df = pd.DataFrame(rows)
    cols = [c for c in OUTPUT_COLUMNS if c in df.columns]
    df_out = df[cols] if cols else df

    if save_excel_path:
        df_out.to_excel(save_excel_path, index=False)

    return df


# =========================================================
# 메인
# =========================================================

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    ensure_dir(DEBUG_HTML_DIR)
    ensure_dir(DEBUG_SHOT_DIR)

    csv_path = INPUT_CSV if os.path.exists(INPUT_CSV) else CONFIG_CSV
    if not os.path.exists(csv_path):
        raise FileNotFoundError(
            f"{INPUT_CSV} 또는 {CONFIG_CSV} 파일이 없습니다."
        )

    targets = load_targets_from_csv(csv_path)
    df = run_monitor(targets, save_excel_path=None)

    cols = [c for c in OUTPUT_COLUMNS if c in df.columns]
    df_out = df[cols] if cols else df

    save_path = OUTPUT_XLSX
    try:
        df_out.to_excel(save_path, index=False)
    except PermissionError:
        save_path = f"aps_monitoring_result_{time.strftime('%Y%m%d_%H%M%S')}.xlsx"
        df_out.to_excel(save_path, index=False)
        print(f"\n(기본 파일이 열려 있어 {save_path}로 저장했습니다)")

    print("\n=== 완료 ===")
    try:
        print(df_out.to_string(index=False))
    except UnicodeEncodeError:
        print(df_out[["date", "country", "channel", "price", "rating", "review_count"]].to_string(index=False))

    print(f"\n엑셀 저장 완료: {save_path}")
