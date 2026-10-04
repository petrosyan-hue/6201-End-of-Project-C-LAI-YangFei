"""FAQ loading, language detection, and retrieval scoring.

The retrieval layer is intentionally small and inspectable for the coursework
prototype. It loads structured FAQ records, tokenises English/Chinese/Spanish
questions, applies topic-keyword and phrase boosts, and returns the strongest FAQ
record only when it passes a relevance threshold.
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path


TOKEN_RE = re.compile(r"[a-z0-9]+|[\u4e00-\u9fff]+", re.IGNORECASE)
STOPWORDS = {
    "a", "an", "and", "are", "can", "do", "does", "for", "has", "have", "how",
    "i", "if", "in", "is", "it", "my", "of", "on", "or", "the", "to", "what",
    "when", "where", "which", "who", "with", "you", "your"
}

TOPIC_KEYWORDS = {
    "returns": {"return", "returns", "devolución", "devolver", "unused", "packaging", "退货", "退"},
    "refunds": {"refund", "refunds", "reembolso", "money", "sent", "back", "退款", "到账"},
    "shipping": {"shipping", "delivery", "international", "overseas", "working", "days", "envío", "物流", "配送"},
    "lost_package": {"lost", "package", "parcel", "tracking", "delivered", "door", "seguimiento", "paquete", "包裹", "丢", "送达"},
    "cancellation": {"cancel", "stop", "leaves", "warehouse", "cancelar", "cancellation", "取消", "pedido", "订单"},
    "customs": {"customs", "duties", "taxes", "border", "tax", "import", "impuestos", "关税", "进口税"},
    "payment": {"payment", "pay", "card", "cards", "wallet", "methods", "tarjetas", "pago", "付款", "电子钱包"},
    "warranty": {"warranty", "cover", "factory", "faults", "garantía", "defects", "electronics", "保修", "制造缺陷"},
    "address_change": {"address", "house", "typed", "delivery", "change", "修改", "地址", "收货地址"},
    "coupons": {"coupon", "discount", "promotion", "voucher", "code", "优惠码", "促销"},
    "size_exchange": {"exchange", "swap", "larger", "size", "shirt", "return", "换货", "尺码"},
    "support_hours": {"support", "service", "speak", "available", "hours", "客服", "时间"},
    "damaged_item": {"damaged", "broken", "cracked", "box", "photos", "损坏", "坏", "照片"},
    "wrong_item": {"wrong", "another", "received", "blue", "black", "equivocado", "otro", "发错", "错"},
    "split_shipment": {"half", "part", "missing", "separate", "shipments", "少", "分开发货", "多个物流单号"},
    "preorder": {"preorder", "pre-order", "release", "preventa", "lanzamiento", "预售", "发售"},
    "account_login": {"login", "log", "sign", "password", "account", "登录", "账号", "密码"},
    "invoice": {"invoice", "receipt", "company", "billing", "factura", "facturación", "发票"},
    "gift_card": {"gift", "giftcard", "balance", "voucher", "coupon", "礼品卡", "叠加"},
    "privacy": {"delete", "remove", "personal", "records", "data", "privacy", "删除", "资料", "数据"},
    "payment_failure": {"failed", "declined", "rejected", "card", "payment", "falló", "pago", "支付失败", "拒绝"},
    "product_authenticity": {"authentic", "original", "branded", "suppliers", "authenticity", "正品", "证明"},
}

TOPIC_PHRASES = {
    "returns": {"return an item", "after two weeks", "退货", "devolver un producto"},
    "customs": {"border tax", "import tax", "customs duties", "关税", "impuestos de importación"},
    "payment": {"payment methods", "pay with a wallet", "wallet instead", "电子钱包", "tarjetas de crédito"},
    "coupons": {"discount code", "coupon code", "other promotion", "其他促销", "优惠码"},
    "gift_card": {"gift card", "gift balance", "礼品卡"},
}


@dataclass
class FAQEntry:
    id: str
    topic: str
    language: str
    question: str
    answer: str
    source: str


def load_faq(path: str | Path) -> list[FAQEntry]:
    with open(path, encoding="utf-8") as f:
        rows = json.load(f)
    return [FAQEntry(**row) for row in rows]


def tokenize(text: str) -> set[str]:
    text = text.lower()
    tokens = {token for token in TOKEN_RE.findall(text) if token not in STOPWORDS}
    # Add single Chinese characters as fallback so Chinese questions can still match.
    for char in text:
        if "\u4e00" <= char <= "\u9fff":
            tokens.add(char)
    return tokens


def detect_language(text: str) -> str:
    has_chinese = any("\u4e00" <= char <= "\u9fff" for char in text)
    has_latin_words = bool(re.search(r"[a-zA-Z]{3,}", text))
    if has_chinese and has_latin_words:
        return "mixed"
    if has_chinese:
        return "zh"
    spanish_marks = {
        "¿", "¡", "pedido", "envío", "cancelar", "cuánto", "factura", "pago",
        "preventa", "paquete", "llegó", "quiero", "tarjetas", "crédito", "exacto"
    }
    lowered = text.lower()
    if any(mark in lowered for mark in spanish_marks):
        return "es"
    return "en"


def score_entry(query: str, entry: FAQEntry) -> float:
    query_terms = tokenize(query)
    doc_terms = tokenize(f"{entry.topic} {entry.question} {entry.answer}")
    if not query_terms or not doc_terms:
        return 0.0
    overlap = len(query_terms & doc_terms)
    base = overlap / len(query_terms)
    topic_terms = TOPIC_KEYWORDS.get(entry.topic, set())
    if query_terms & topic_terms:
        base += 0.35
    query_lower = query.lower()
    if any(phrase in query_lower for phrase in TOPIC_PHRASES.get(entry.topic, set())):
        base += 0.40
    # Prefer entries in the user's language when evidence strength is otherwise similar.
    if detect_language(query) == entry.language:
        base += 0.15
    return base


def retrieve(query: str, entries: list[FAQEntry], threshold: float = 0.18) -> tuple[FAQEntry | None, float]:
    scored = sorted(((score_entry(query, entry), entry) for entry in entries), reverse=True, key=lambda x: x[0])
    if not scored or scored[0][0] < threshold:
        return None, scored[0][0] if scored else 0.0
    return scored[0][1], scored[0][0]
