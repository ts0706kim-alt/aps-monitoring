# -*- coding: utf-8 -*-
"""
Buds4 Daily Monitoring - 9개 채널 리뷰, 평점, 가격, 프로모션 모니터링
"""
import sys
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

"""
US/UK/DE × Best Buy, Amazon, Samsung.com, Currys, Mediamarkt
"""

import json
import re
import time
import random
import csv
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup


# === 설정 ===
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}
REQUEST_DELAY = (2, 5)
OUTPUT_DIR = Path(__file__).parent / "monitoring_results"
HISTORY_FILE = OUTPUT_DIR / "monitoring_history.csv"


def ensure_output_dir():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def get_channel_from_url(url: str) -> str:
    """URL에서 채널 식별"""
    d = urlparse(url).netloc.lower()
    if "bestbuy" in d:
        return "bestbuy"
    if "amazon" in d:
        return "amazon"
    if "samsung" in d:
        return "samsung"
    if "currys" in d:
        return "currys"
    if "mediamarkt" in d:
        return "mediamarkt"
    return "unknown"


def fetch_page(url: str, retries: int = 3) -> str | None:
    """페이지 HTML 가져오기 (재시도 포함)"""
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            if r.status_code == 200 and "captcha" not in r.text.lower():
                return r.text
        except Exception as e:
            print(f"  [시도 {attempt+1}] 오류: {e}")
        time.sleep(random.uniform(*REQUEST_DELAY))
    return None


def _extract_json_ld(html: str) -> dict | None:
    """JSON-LD에서 Product 스키마 추출"""
    soup = BeautifulSoup(html, "html.parser")
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "{}")
            if isinstance(data, list):
                for item in data:
                    if item.get("@type") in ("Product", "AggregateRating"):
                        return item
            elif data.get("@type") in ("Product", "AggregateRating"):
                return data
        except (json.JSONDecodeError, TypeError):
            continue
    return None


def _extract_jsonld_product(html: str) -> dict | None:
    """JSON-LD에서 Product 스키마 추출 (가격, 리뷰 수, 평점) - Best Buy용"""
    soup = BeautifulSoup(html, "html.parser")
    for script in soup.find_all("script", type="application/ld+json"):
        text = script.string or script.get_text(strip=True)
        if not text:
            continue
        try:
            data = json.loads(text)
        except (json.JSONDecodeError, TypeError):
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            if isinstance(item, dict) and item.get("@type") == "Product":
                rating = item.get("aggregateRating", {}) or {}
                offers = item.get("offers", {})
                if isinstance(offers, list) and offers:
                    offers = offers[0]
                offers = offers if isinstance(offers, dict) else {}
                return {
                    "name": item.get("name"),
                    "price": offers.get("price"),
                    "currency": offers.get("priceCurrency"),
                    "rating_value": rating.get("ratingValue"),
                    "review_count": rating.get("reviewCount"),
                }
    return None


def _parse_amazon(html: str, country: str) -> dict:
    """Amazon 상품 페이지 파싱"""
    soup = BeautifulSoup(html, "html.parser")
    result = {
        "country": country,
        "channel": "Amazon",
        "review_count": None,
        "rating": None,
        "price": None,
        "list_price": None,
        "discount_percent": None,
        "promotion_text": None,
        "timestamp": datetime.now().isoformat(),
    }

    # 리뷰 수
    for sel in [{"id": "acrCustomerReviewText"}, {"id": "acrCustomerReviewCount"}]:
        el = soup.find("span", sel)
        if el:
            m = re.search(r"[\d,]+", el.get_text(strip=True).replace(",", ""))
            if m:
                result["review_count"] = int(m.group().replace(",", ""))
                break

    # 평점
    for sel in [{"data-hook": "rating-out-of-text"}, {"class": "a-icon-alt"}]:
        el = soup.find("span", sel)
        if el:
            m = re.search(r"(\d+[.,]?\d*)", el.get_text(strip=True))
            if m:
                result["rating"] = float(m.group(1).replace(",", "."))
                break

    # 가격
    price_el = soup.find("span", class_="a-price-whole")
    if price_el:
        cents = soup.find("span", class_="a-price-fraction")
        s = price_el.get_text(strip=True).replace(",", "")
        if cents:
            s += "." + cents.get_text(strip=True)
        m = re.search(r"[\d.]+", s)
        if m:
            result["price"] = m.group()
    if not result["price"]:
        off = soup.find("span", class_="a-offscreen")
        if off and (m := re.search(r"[\d.,]+", off.get_text(strip=True))):
            result["price"] = m.group().replace(",", "")

    # 정가
    lp = soup.find("span", class_="a-price a-text-price")
    if lp and (m := re.search(r"[\d.,]+", lp.get_text(strip=True))):
        result["list_price"] = m.group().replace(",", "")

    # 할인율
    if result["price"] and result["list_price"]:
        try:
            p, lp = float(result["price"]), float(result["list_price"])
            if lp > 0:
                result["discount_percent"] = round((1 - p / lp) * 100, 1)
        except ValueError:
            pass

    # 프로모션
    for sel in ["promoPriceBlockMessage", "savingsPercentage", "instantPayments_feature_div"]:
        el = soup.find(id=sel) or soup.find(class_=re.compile(sel, re.I))
        if el and (t := el.get_text(strip=True)) and len(t) > 2:
            result["promotion_text"] = t[:200]
            break

    return result


def _parse_amazon_search(html: str, country: str) -> dict:
    """Amazon 검색 결과 페이지 (UK 등) - 첫 번째 상품 또는 N/A"""
    soup = BeautifulSoup(html, "html.parser")
    result = {
        "country": country,
        "channel": "Amazon",
        "review_count": None,
        "rating": None,
        "price": None,
        "list_price": None,
        "discount_percent": None,
        "promotion_text": None,
        "timestamp": datetime.now().isoformat(),
    }
    # 검색 결과에서 첫 상품 정보 시도
    cards = soup.select("[data-component-type='s-search-result']")
    for card in cards[:3]:
        r_el = card.select_one(".a-size-base.s-underline-text")
        if r_el and (m := re.search(r"[\d,]+", r_el.get_text(strip=True))):
            result["review_count"] = int(m.group().replace(",", ""))
        r2 = card.select_one("span.a-icon-alt")
        if r2 and (m := re.search(r"(\d+[.,]?\d*)", r2.get_text(strip=True))):
            result["rating"] = float(m.group(1).replace(",", "."))
        p_el = card.select_one(".a-price .a-offscreen")
        if p_el and (m := re.search(r"[\d.,]+", p_el.get_text(strip=True))):
            result["price"] = m.group().replace(",", "")
        if result["review_count"] or result["rating"] or result["price"]:
            break
    return result


def _parse_bestbuy(html: str, country: str) -> dict:
    """Best Buy 상품 페이지 파싱 - JSON-LD Product 스키마 우선"""
    result = {
        "country": country,
        "channel": "Best Buy",
        "review_count": None,
        "rating": None,
        "price": None,
        "list_price": None,
        "discount_percent": None,
        "promotion_text": None,
        "timestamp": datetime.now().isoformat(),
    }
    soup = BeautifulSoup(html, "html.parser")

    # JSON-LD Product 스키마에서 가격, 리뷰 수, 평점 추출
    prod = _extract_jsonld_product(html)
    if prod:
        if prod.get("price") is not None:
            result["price"] = str(prod["price"])
        if prod.get("review_count") is not None:
            try:
                result["review_count"] = int(prod["review_count"])
            except (ValueError, TypeError):
                pass
        if prod.get("rating_value") is not None:
            try:
                result["rating"] = float(prod["rating_value"])
            except (ValueError, TypeError):
                pass

    # Volume(리뷰 개수) - HTML 폴백
    if result["review_count"] is None:
        for sel in ["c-reviews", "reviews-rating", "ratings-reviews", "h-reviews", "reviews"]:
            el = soup.find(class_=re.compile(sel, re.I)) or soup.find(attrs={"data-lid": re.compile(r"reviews?", re.I)})
            if el:
                t = el.get_text()
                if m := re.search(r"([\d,]+)\s*reviews?", t, re.I):
                    result["review_count"] = int(m.group(1).replace(",", ""))
                    break
        if result["review_count"] is None:
            for el in soup.find_all(string=re.compile(r"[\d,]+[\s]*reviews?", re.I)):
                if m := re.search(r"([\d,]+)", str(el)):
                    result["review_count"] = int(m.group(1).replace(",", ""))
                    break

    # Rating 폴백
    if result["rating"] is None:
        for sel in ["c-reviews", "reviews-rating", "ratings-reviews"]:
            el = soup.find(class_=re.compile(sel, re.I))
            if el:
                t = el.get_text()
                if m := re.search(r"(\d+[.,]?\d*)\s*out of 5", t, re.I):
                    result["rating"] = float(m.group(1).replace(",", "."))
                    break

    # 가격 - HTML 폴백
    if result["price"] is None:
        price_selectors = [
            "div.brix span.font-sans.text-default.text-style-body-md-400.font-500.text-7.leading-7",
            "span.font-sans.text-default.text-style-body-md-400.font-500.text-7.leading-7",
            "div.brix span.font-sans",
            "[data-testid='customer-price']",
        ]
        for sel in price_selectors:
            el = soup.select_one(sel)
            if el and (m := re.search(r"[\d.,]+", el.get_text(strip=True))):
                result["price"] = m.group().replace(",", "")
                break
    if result["price"] is None:
        el = soup.find(class_=re.compile("priceView|pricing-price", re.I))
        if el and (m := re.search(r"[\d.,]+", el.get_text(strip=True))):
            result["price"] = m.group().replace(",", "")
    # 프로모션 (e-gift card 등)
    for txt in ["gift card", "e-gift", "save", "offer", "promo"]:
        el = soup.find(string=re.compile(txt, re.I))
        if el and el.parent:
            t = el.parent.get_text(strip=True) if hasattr(el.parent, "get_text") else str(el)[:150]
            if len(t) > 5:
                result["promotion_text"] = t[:200]
                break
    return result


def _parse_samsung(html: str, country: str) -> dict:
    """Samsung.com 상품 페이지 파싱"""
    result = {
        "country": country,
        "channel": "Samsung.com",
        "review_count": None,
        "rating": None,
        "price": None,
        "list_price": None,
        "discount_percent": None,
        "promotion_text": None,
        "timestamp": datetime.now().isoformat(),
    }
    soup = BeautifulSoup(html, "html.parser")

    ld = _extract_json_ld(html)
    if ld:
        if "aggregateRating" in ld:
            ar = ld["aggregateRating"]
            result["rating"] = float(ar.get("ratingValue", 0) or 0)
            result["review_count"] = int(ar.get("reviewCount", 0) or 0)
        if "offers" in ld:
            o = ld["offers"] if isinstance(ld["offers"], dict) else (ld["offers"][0] if ld["offers"] else {})
            if isinstance(o, dict) and "price" in o:
                result["price"] = str(o.get("price", ""))

    # HTML 폴백
    if result["price"] is None:
        for pat in [r'\$[\d,]+\.?\d*', r'£[\d,]+\.?\d*', r'€[\d,]+\.?\d*', r'[\d,]+\.?\d*\s*[€$£]']:
            m = re.search(pat, html)
            if m:
                result["price"] = re.sub(r'[^\d.]', '', m.group())
                break
    return result


def _parse_currys(html: str, country: str) -> dict:
    """Currys UK 상품 페이지 파싱"""
    result = {
        "country": country,
        "channel": "Currys",
        "review_count": None,
        "rating": None,
        "price": None,
        "list_price": None,
        "discount_percent": None,
        "promotion_text": None,
        "timestamp": datetime.now().isoformat(),
    }
    soup = BeautifulSoup(html, "html.parser")

    ld = _extract_json_ld(html)
    if ld:
        if "aggregateRating" in ld:
            ar = ld["aggregateRating"]
            result["rating"] = float(ar.get("ratingValue", 0) or 0)
            result["review_count"] = int(ar.get("reviewCount", 0) or 0)
        if "offers" in ld:
            o = ld["offers"] if isinstance(ld["offers"], dict) else (ld["offers"][0] if ld["offers"] else {})
            if isinstance(o, dict) and "price" in o:
                result["price"] = str(o.get("price", ""))

    # HTML 폴백
    if result["price"] is None:
        el = soup.find(class_=re.compile("price|Amount", re.I))
        if el and (m := re.search(r"[\d.,]+", el.get_text(strip=True))):
            result["price"] = m.group().replace(",", "")
    # 프로모션 (30% D/C 등)
    for txt in ["D/C", "discount", "offer", "save", "%"]:
        el = soup.find(string=re.compile(txt, re.I))
        if el and el.parent:
            t = el.parent.get_text(strip=True) if hasattr(el.parent, "get_text") else str(el)[:150]
            if len(t) > 3:
                result["promotion_text"] = t[:200]
                break
    return result


def _parse_mediamarkt(html: str, country: str) -> dict:
    """Mediamarkt DE 상품 페이지 파싱"""
    result = {
        "country": country,
        "channel": "Mediamarkt",
        "review_count": None,
        "rating": None,
        "price": None,
        "list_price": None,
        "discount_percent": None,
        "promotion_text": None,
        "timestamp": datetime.now().isoformat(),
    }
    soup = BeautifulSoup(html, "html.parser")

    ld = _extract_json_ld(html)
    if ld:
        if "aggregateRating" in ld:
            ar = ld["aggregateRating"]
            result["rating"] = float(ar.get("ratingValue", 0) or 0)
            result["review_count"] = int(ar.get("reviewCount", 0) or 0)
        if "offers" in ld:
            o = ld["offers"] if isinstance(ld["offers"], dict) else (ld["offers"][0] if ld["offers"] else {})
            if isinstance(o, dict) and "price" in o:
                result["price"] = str(o.get("price", ""))

    if result["price"] is None:
        el = soup.find(class_=re.compile("price|Price", re.I))
        if el and (m := re.search(r"[\d.,]+", el.get_text(strip=True))):
            result["price"] = m.group().replace(",", "")
    return result


def parse_product(html: str, url: str, country: str, channel: str) -> dict:
    """URL/채널에 맞는 파서 호출"""
    ch = get_channel_from_url(url)
    is_amazon_search = "amazon" in url and "/s?" in url

    if ch == "amazon":
        data = _parse_amazon_search(html, country) if is_amazon_search else _parse_amazon(html, country)
    elif ch == "bestbuy":
        data = _parse_bestbuy(html, country)
    elif ch == "samsung":
        data = _parse_samsung(html, country)
    elif ch == "currys":
        data = _parse_currys(html, country)
    elif ch == "mediamarkt":
        data = _parse_mediamarkt(html, country)
    else:
        data = {
            "country": country,
            "channel": channel or "Unknown",
            "review_count": None,
            "rating": None,
            "price": None,
            "list_price": None,
            "discount_percent": None,
            "promotion_text": None,
            "timestamp": datetime.now().isoformat(),
        }

    data["channel"] = channel or data.get("channel", "Unknown")
    return data


def load_config(csv_path: str | Path) -> list[dict]:
    """모니터링 대상 로드"""
    config_path = Path(csv_path)
    if not config_path.exists():
        raise FileNotFoundError(f"설정 파일 없음: {config_path}")
    rows = []
    with open(config_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("URL", "").strip():
                rows.append(row)
    return rows


def append_history(records: list[dict]):
    if not records:
        return
    file_exists = HISTORY_FILE.exists()
    fieldnames = ["country", "channel", "review_count", "rating", "price", "list_price",
                  "discount_percent", "promotion_text", "timestamp", "url", "product_name"]
    with open(HISTORY_FILE, "a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        if not file_exists:
            writer.writeheader()
        for r in records:
            writer.writerow(r)


def _get_currency_symbol(country: str) -> str:
    """국가별 통화 기호"""
    m = {"US": "$", "UK": "£", "DE": "€"}
    return m.get(str(country).upper(), "")


def format_price_display(price: str | None, country: str) -> str:
    """가격 포맷 (통화 기호 포함) - 웹/엑셀 표시용"""
    if not price:
        return "N/A"
    try:
        num = float(str(price).replace(",", ""))
        sym = _get_currency_symbol(country)
        return f"{sym}{num:,.2f}"
    except (ValueError, TypeError):
        return str(price) or "N/A"


def run_monitoring_return_results(config_path: str | Path = None, verbose: bool = False) -> list[dict] | None:
    """모니터링 실행 후 결과 리스트 반환 (웹/엑셀용)"""
    ensure_output_dir()
    if config_path is None:
        config_path = Path(__file__).parent / "config.csv"
    if not Path(config_path).exists():
        return None

    rows = load_config(config_path)
    if verbose:
        print(f"모니터링 대상: {len(rows)}개 채널")
        print("-" * 60)

    all_results = []
    for row in rows:
        country = row.get("Country", row.get("Sub", "?"))
        sub = row.get("Sub", country)
        channel = row.get("Channel", "?")
        url = row.get("URL", "").strip()
        product = row.get("Product_Name", "Buds4 Pro")

        if verbose:
            print(f"[{country}] {channel} - {product}")
        html = fetch_page(url)
        if not html:
            if verbose:
                print(f"  ❌ 페이지 로드 실패")
            data = {
                "country": country, "channel": channel, "review_count": None, "rating": None,
                "price": None, "list_price": None, "discount_percent": None, "promotion_text": None,
                "timestamp": datetime.now().isoformat(), "url": url, "product_name": product,
            }
            all_results.append(data)
            continue

        data = parse_product(html, url, country, channel)
        data["url"] = url
        data["product_name"] = product
        all_results.append(data)

        if verbose:
            rc = data["review_count"] if data["review_count"] is not None else "N/A"
            rt = data["rating"] if data["rating"] is not None else "N/A"
            pr = data["price"] if data["price"] else "N/A"
            dc = data["discount_percent"] if data["discount_percent"] is not None else "-"
            print(f"  리뷰: {rc} | 평점: {rt} | 가격: {pr} | 할인: {dc}%")
            if data.get("promotion_text"):
                print(f"  프로모션: {str(data['promotion_text'])[:70]}...")

        time.sleep(random.uniform(*REQUEST_DELAY))

    if all_results:
        date_str = datetime.now().strftime("%Y%m%d")
        report_path = OUTPUT_DIR / f"report_{date_str}.csv"
        fieldnames = ["country", "channel", "review_count", "rating", "price", "list_price",
                      "discount_percent", "promotion_text", "timestamp", "url", "product_name"]
        with open(report_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(all_results)
        append_history(all_results)
        if verbose:
            print("-" * 60)
            print(f"✅ 리포트 저장: {report_path}")
            print(f"✅ 히스토리 추가: {HISTORY_FILE}")

    return all_results


def run_monitoring(config_path: str | Path = None):
    """데일리 모니터링 실행 (CLI)"""
    run_monitoring_return_results(config_path, verbose=True)


if __name__ == "__main__":
    run_monitoring()
