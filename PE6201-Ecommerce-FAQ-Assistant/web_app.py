"""Streamlit web demo for the multilingual FAQ assistant.

This module provides the coursework demo UI: topic shortcuts, chat-style FAQ
answers, mixed-language clarification, simulated order lookup, FAQ preview, and
evidence panels for retrieval candidates, baseline comparison, evaluation
results, and single-run metrics. It is a local prototype, not a production store
plugin.
"""

import json
from pathlib import Path
from html import escape

import streamlit as st

from src.assistant import AssistantResponse, answer_question, refusal
from src.metrics import RunMetrics, estimate_cost, estimate_tokens, timer
from src.retrieval import FAQEntry, detect_language, load_faq, retrieve, score_entry, tokenize


ROOT = Path(__file__).parent
FAQ_PATH = ROOT / "data" / "faq.json"
EVAL_PATH = ROOT / "eval" / "eval_cases.json"


@st.cache_data
def cached_faq():
    return load_faq(FAQ_PATH)


@st.cache_data
def cached_eval_cases():
    return json.loads(EVAL_PATH.read_text(encoding="utf-8"))


def contains_all(answer: str, expected_terms: list[str]) -> bool:
    lowered = answer.lower()
    return all(term.lower() in lowered for term in expected_terms)


def find_eval_case(query: str) -> dict | None:
    normalized = query.strip().casefold()
    for case in cached_eval_cases():
        if case["question"].strip().casefold() == normalized:
            return case
    return None


def verdict_for_answer(source_id: str | None, answer: str, case: dict | None) -> str:
    if case is None:
        return "No fixed test case for this typed question."
    source_ok = source_id == case["expected_source_id"]
    content_ok = contains_all(answer, case["must_contain"])
    return "Correct on this eval case" if source_ok and content_ok else "Wrong on this eval case"


def top_retrieval_candidates(query: str, entries: list[FAQEntry], top_k: int = 3) -> list[tuple[float, FAQEntry]]:
    scored = sorted(((score_entry(query, entry), entry) for entry in entries), reverse=True, key=lambda item: item[0])
    return scored[:top_k]


def keyword_baseline_retrieve(query: str, entries: list[FAQEntry]) -> tuple[FAQEntry | None, float]:
    if detect_language(query) == "mixed":
        return None, 0.0
    query_terms = tokenize(query)
    if not query_terms:
        return None, 0.0
    scored = []
    for entry in entries:
        entry_terms = tokenize(f"{entry.question} {entry.answer}")
        score = len(query_terms & entry_terms) / len(query_terms)
        scored.append((score, entry))
    scored.sort(reverse=True, key=lambda item: item[0])
    if not scored or scored[0][0] < 0.18:
        return None, scored[0][0] if scored else 0.0
    return scored[0][1], scored[0][0]


def format_keyword_answer(query: str, entry: FAQEntry | None) -> str:
    language = detect_language(query)
    if entry is None:
        return refusal(language)
    if language == "zh":
        return f"{entry.answer}（来源：{entry.source}）"
    if language == "es" and entry.language == "es":
        return f"{entry.answer} Fuente: {entry.source}."
    return f"{entry.answer} Source: {entry.source}."


def answer_keyword_baseline(query: str, entries: list[FAQEntry]) -> dict:
    with timer() as elapsed:
        entry, confidence = keyword_baseline_retrieve(query, entries)
        answer = format_keyword_answer(query, entry)
    input_text = query
    if entry:
        input_text += " " + entry.question + " " + entry.answer
    input_tokens = estimate_tokens(input_text)
    output_tokens = estimate_tokens(answer)
    return {
        "answer": answer,
        "source_id": entry.id if entry else None,
        "source_name": entry.source if entry else None,
        "confidence": confidence,
        "metrics": RunMetrics(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_seconds=elapsed["elapsed"],
            estimated_cost_usd=estimate_cost(input_tokens, output_tokens),
        ),
    }


def mixed_language_prompt(language_choice: str) -> str:
    if language_choice == "中文":
        return "我识别到了混合语言。您希望我用英语、中文还是西班牙语继续回答您？"
    if language_choice == "Español":
        return "He detectado una mezcla de idiomas. ¿Desea que continúe respondiendo en inglés, chino o español?"
    return (
        "I detected mixed languages. Should I continue answering you in English, Chinese, or Spanish?"
    )


def affirmative_intent(text: str) -> bool:
    normalized = text.strip().casefold()
    affirmative_terms = {
        "yes", "y", "ok", "okay", "sure", "continue", "go ahead", "fine",
        "是", "可以", "好", "好的", "好吧", "继续", "不用改", "无需更改", "没问题",
        "sí", "si", "vale", "claro", "continúa", "continuar",
    }
    return normalized in affirmative_terms


def requested_reply_language(text: str) -> str | None:
    normalized = text.strip().casefold()
    spanish_terms = ["用西班牙语", "西班牙语回复", "用西语", "西语回复", "answer in spanish", "reply in spanish"]
    english_terms = ["用英语", "英语回复", "answer in english", "reply in english"]
    chinese_terms = ["用中文", "中文回复", "answer in chinese", "reply in chinese"]
    if any(term in normalized for term in spanish_terms):
        return "Español"
    if any(term in normalized for term in english_terms):
        return "English"
    if any(term in normalized for term in chinese_terms):
        return "中文"
    return None


def format_retrieved_answer_for_language(entry: FAQEntry | None, language_choice: str) -> str:
    if entry is None:
        if language_choice == "中文":
            return "我无法从现有FAQ中可靠回答这个问题。请联系人工客服。转人工客服。"
        if language_choice == "Español":
            return "No puedo responder de forma fiable con la FAQ disponible. Contacta con soporte. Derivar a soporte humano."
        return "I cannot answer this reliably from the available FAQ. Please contact customer support. Route to human support."
    if language_choice == "中文":
        return f"{entry.answer}（来源：{entry.source}）"
    if language_choice == "Español":
        return f"{entry.answer} Fuente: {entry.source}."
    return f"{entry.answer} Source: {entry.source}."


def answer_mixed_followup(query: str, entries: list[FAQEntry], language_choice: str) -> AssistantResponse:
    with timer() as elapsed:
        entry, confidence = retrieve(query, entries)
        answer = format_retrieved_answer_for_language(entry, language_choice)
    input_text = query
    if entry:
        input_text += " " + entry.question + " " + entry.answer
    input_tokens = estimate_tokens(input_text)
    output_tokens = estimate_tokens(answer)
    return AssistantResponse(
        answer=answer,
        source_id=entry.id if entry else None,
        source_name=entry.source if entry else None,
        confidence=confidence,
        metrics=RunMetrics(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_seconds=elapsed["elapsed"],
            estimated_cost_usd=estimate_cost(input_tokens, output_tokens),
        ),
    )


CITY_TRANSLATIONS = {
    "Singapore": {"zh": "新加坡", "es": "Singapur"},
    "Kuala Lumpur": {"zh": "吉隆坡", "es": "Kuala Lumpur"},
    "Shanghai": {"zh": "上海", "es": "Shanghái"},
    "Bangkok": {"zh": "曼谷", "es": "Bangkok"},
    "Jakarta": {"zh": "雅加达", "es": "Yakarta"},
    "Seoul": {"zh": "首尔", "es": "Seúl"},
}

ORDER_TRANSLATIONS = {
    "Paid": {"zh": "已付款", "es": "Pagado"},
    "Unpaid": {"zh": "未付款", "es": "No pagado"},
    "Delivered": {"zh": "已送达", "es": "Entregado"},
    "In transit": {"zh": "运输中", "es": "En tránsito"},
    "Payment pending": {"zh": "等待付款", "es": "Pago pendiente"},
    "Dispatch pending": {"zh": "等待发货", "es": "Pendiente de despacho"},
    "Delivery attempted": {"zh": "已尝试派送", "es": "Intento de entrega"},
    "Return requested": {"zh": "已申请退货", "es": "Devolución solicitada"},
    "Refund processing": {"zh": "退款处理中", "es": "Reembolso en proceso"},
    "Address confirmation needed": {"zh": "需要确认地址", "es": "Se necesita confirmar la dirección"},
    "Customs review": {"zh": "海关审核中", "es": "Revisión de aduanas"},
    "Cancelled": {"zh": "已取消", "es": "Cancelado"},
    "Delivered and received": {"zh": "已送达并签收", "es": "Entregado y recibido"},
    "Estimated delivery in 2-4 days": {"zh": "预计 2-4 天内送达", "es": "Entrega estimada en 2-4 días"},
    "Payment is required before dispatch": {"zh": "发货前需要先完成付款", "es": "Se requiere el pago antes del despacho"},
    "Preparing for dispatch": {"zh": "正在准备发货", "es": "Preparando el despacho"},
    "Courier will attempt delivery again": {"zh": "快递员将再次尝试派送", "es": "El mensajero intentará entregar de nuevo"},
    "Return request is under review": {"zh": "退货申请正在审核中", "es": "La solicitud de devolución está en revisión"},
    "Refund is being processed": {"zh": "退款正在处理中", "es": "El reembolso se está procesando"},
    "Please confirm the delivery address": {"zh": "请确认收货地址", "es": "Confirme la dirección de entrega"},
    "Shipment is under customs review": {"zh": "包裹正在接受海关审核", "es": "El envío está en revisión de aduanas"},
    "Order was cancelled before dispatch": {"zh": "订单已在发货前取消", "es": "El pedido fue cancelado antes del despacho"},
}


def translate_order_value(value: str, language: str) -> str:
    return ORDER_TRANSLATIONS.get(value, {}).get(language, value)


def translate_route(route: str, language: str) -> str:
    parts = [part.strip() for part in route.split("→")]
    translated = [CITY_TRANSLATIONS.get(part, {}).get(language, part) for part in parts]
    return " → ".join(translated)


def format_order_answer(order_number: str, order: dict | None) -> str:
    if order is None:
        return (
            f"I could not find demo order {order_number}. Please try a sample order such as SE-2026-001, "
            "SE-2026-002 or SE-2026-003.\n\n"
            f"我没有找到演示订单 {order_number}。您可以试试 SE-2026-001、SE-2026-002 或 SE-2026-003。\n\n"
            f"No encontré el pedido de demostración {order_number}. Puede probar SE-2026-001, SE-2026-002 o SE-2026-003."
        )
    return (
        f"Yes, I found demo order {order_number}.\n"
        f"Route: {order['route']}\n"
        f"Payment: {order['payment']}\n"
        f"Status: {order['status']} - {order['detail']}\n"
        "What would you like to ask about this order?\n\n"
        f"已找到演示订单 {order_number}。\n"
        f"路线：{translate_route(order['route'], 'zh')}\n"
        f"付款：{translate_order_value(order['payment'], 'zh')}\n"
        f"状态：{translate_order_value(order['status'], 'zh')} - {translate_order_value(order['detail'], 'zh')}\n"
        "关于这个订单，您还想问什么？\n\n"
        f"Sí, encontré el pedido de demostración {order_number}.\n"
        f"Ruta: {translate_route(order['route'], 'es')}\n"
        f"Pago: {translate_order_value(order['payment'], 'es')}\n"
        f"Estado: {translate_order_value(order['status'], 'es')} - {translate_order_value(order['detail'], 'es')}\n"
        "¿Qué desea preguntar sobre este pedido?"
    )


def append_chat(customer_text: str, answer_text: str) -> None:
    st.session_state.setdefault("chat_history", []).append((customer_text, answer_text))


st.set_page_config(page_title="ShopEase Support", page_icon="🤖", layout="wide")

BOT_ICON = """
<span class="bot-icon" aria-label="ShopEase support bot">
    <svg viewBox="0 0 64 64" role="img" focusable="false">
        <circle class="bot-ring" cx="32" cy="32" r="29"></circle>
        <rect class="bot-head" x="17" y="20" width="30" height="24" rx="11"></rect>
        <circle class="bot-eye" cx="27" cy="33" r="3.8"></circle>
        <circle class="bot-eye" cx="38" cy="33" r="3.8"></circle>
        <path class="bot-smile" d="M24 43 C29 47, 37 47, 42 43"></path>
    </svg>
</span>
"""

st.markdown(
    """
    <style>
    header[data-testid="stHeader"], div[data-testid="stToolbar"], div[data-testid="stDecoration"],
    div[data-testid="stStatusWidget"], .stDeployButton, #MainMenu, footer {
        display: none !important;
        height: 0 !important;
        visibility: hidden !important;
        opacity: 0 !important;
    }
    .stApp {
        background:
            radial-gradient(circle at 14% 10%, rgba(20, 184, 166, 0.18), transparent 28%),
            radial-gradient(circle at 88% 4%, rgba(96, 165, 250, 0.20), transparent 26%),
            linear-gradient(90deg, rgba(15, 118, 110, 0.06) 1px, transparent 1px),
            linear-gradient(180deg, rgba(37, 99, 235, 0.05) 1px, transparent 1px),
            linear-gradient(180deg, #f8fbff 0%, #eef7f4 42%, #f8fafc 100%);
        background-size: auto, auto, 42px 42px, 42px 42px, auto;
    }
    .block-container {
        background:
            radial-gradient(circle at 100% 18%, rgba(245, 158, 11, 0.10), transparent 16%),
            radial-gradient(circle at 0% 92%, rgba(20, 184, 166, 0.10), transparent 18%);
        padding-top: 0.2rem;
        color: #111827 !important;
    }
    .stApp, .stApp p, .stApp li, .stApp span, .stApp label,
    .stMarkdown, .stMarkdown p, .stMarkdown li,
    div[data-testid="stMarkdownContainer"], div[data-testid="stMarkdownContainer"] p,
    div[data-testid="stCaptionContainer"], div[data-testid="stCaptionContainer"] p,
    h1, h2, h3, h4 {
        color: #111827 !important;
    }
    .hero {
        background:
            linear-gradient(135deg, rgba(15, 118, 110, 0.94) 0%, rgba(22, 78, 99, 0.96) 100%),
            radial-gradient(circle at 90% 20%, rgba(255, 255, 255, 0.20), transparent 22%);
        color: #ffffff;
        border-radius: 22px;
        padding: 24px 28px;
        margin-bottom: 22px;
        box-shadow: 0 18px 50px rgba(15, 23, 42, 0.18);
        border: 1px solid rgba(255, 255, 255, 0.18);
    }
    .hero h1, .hero p {
        color: #ffffff !important;
        margin-bottom: 6px;
    }
    .hero h1 span, .hero p span {
        color: #ffffff !important;
    }
    .hero h1 {
        font-size: 2.55rem;
    }
    .project-name {
        font-size: 1.65rem;
        font-weight: 700;
        color: #dbeafe !important;
        white-space: nowrap;
        overflow-x: auto;
    }
    .bot-title {
        font-size: 1.55rem;
        font-weight: 800;
        display: flex;
        align-items: center;
        gap: 12px;
        white-space: nowrap;
        overflow-x: auto;
        color: #111827 !important;
        margin: 0 0 8px 0;
    }
    .bot-icon {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 52px;
        height: 52px;
        flex: 0 0 52px;
        border-radius: 50%;
        background: #eff6ff;
        box-shadow: 0 10px 24px rgba(37, 99, 235, 0.18);
    }
    .bot-icon svg {
        width: 100%;
        height: 100%;
    }
    .bot-ring {
        fill: #eff6ff;
        stroke: #60a5fa;
        stroke-width: 4;
    }
    .bot-head {
        fill: #0f766e;
    }
    .bot-eye {
        fill: #ecfeff;
    }
    .bot-smile {
        fill: none;
        stroke: #ecfeff;
        stroke-width: 3;
        stroke-linecap: round;
    }
    .hero .bot-icon {
        width: 52px;
        height: 52px;
        flex: 0 0 52px;
        display: inline-flex;
        vertical-align: -0.22em;
        margin-left: 10px;
        transform: translateY(-1px);
    }
    .chat-history {
        max-height: 520px;
        overflow-y: auto;
        padding: 12px;
        background: #f8fafc;
        border: 1px solid #cbd5e1;
        border-radius: 18px;
    }
    .store-panel {
        background: #ffffff;
        color: #111827;
        border: 1px solid #d1d5db;
        border-radius: 20px;
        padding: 22px;
        min-height: 420px;
    }
    .store-panel h3, .store-panel p, .store-panel li {
        color: #111827 !important;
    }
    .chat-window {
        background: #ffffff;
        color: #111827;
        border: 2px solid #0f766e;
        border-radius: 24px;
        padding: 0;
        overflow: hidden;
        box-shadow: 0 18px 50px rgba(15, 23, 42, 0.18);
    }
    .chat-top {
        background: #0f766e;
        color: #ffffff !important;
        padding: 16px 20px;
        font-weight: 800;
        font-size: 1.18rem;
    }
    .chat-top, .chat-top * {
        color: #ffffff !important;
    }
    .chat-body {
        background: #ffffff;
        padding: 22px;
        min-height: 260px;
    }
    .bot-bubble, .user-bubble {
        color: #111827 !important;
        border-radius: 16px;
        padding: 13px 15px;
        margin: 10px 0;
        line-height: 1.55;
    }
    .bot-bubble {
        background: #dbeafe;
        border: 1px solid #60a5fa;
        margin-right: 42px;
    }
    .user-bubble {
        background: #fef3c7;
        border: 1px solid #f59e0b;
        margin-left: 42px;
    }
    .chat-input-area {
        background: #ffffff;
        border-top: 1px solid #e5e7eb;
        padding: 16px 18px;
    }
    .evidence-card {
        background: #ffffff;
        color: #111827;
        border: 1px solid #d1d5db;
        border-radius: 16px;
        padding: 16px;
        margin-bottom: 10px;
    }
    .evidence-card p, .evidence-card li, .evidence-card strong {
        color: #111827 !important;
    }
    .small-muted {
        color: #4b5563 !important;
        font-size: 0.94rem;
    }
    div[data-testid="stTextInputRootElement"],
    div[data-testid="stTextAreaRootElement"],
    div[data-baseweb="input"],
    div[data-baseweb="base-input"],
    div[data-baseweb="textarea"],
    div[data-baseweb="input"] > div,
    div[data-baseweb="base-input"] > div,
    div[data-baseweb="textarea"] > div {
        background: #ffffff !important;
        color: #111827 !important;
        border: 2px solid #94a3b8 !important;
        border-radius: 24px !important;
        box-shadow: none !important;
    }
    input[data-testid="stTextInputField"],
    div[data-baseweb="input"] input,
    div[data-baseweb="base-input"] input {
        background: #ffffff !important;
        color: #111827 !important;
        -webkit-text-fill-color: #111827 !important;
        font-size: 1.2rem !important;
    }
    textarea,
    div[data-baseweb="textarea"] textarea {
        background: #ffffff !important;
        color: #111827 !important;
        -webkit-text-fill-color: #111827 !important;
        font-size: 1.15rem !important;
        min-height: 120px !important;
        border-radius: 28px !important;
        border: 2px solid #94a3b8 !important;
        padding: 16px 20px !important;
    }
    label[data-testid="stWidgetLabel"] p { font-size: 1.3rem !important; font-weight: 700 !important; }
    div.stButton > button,
    div[data-testid="stDownloadButton"] > button,
    [data-testid="stFileUploaderDropzone"] button,
    [data-testid="stBaseButton-secondary"],
    section[data-testid="stFileUploader"] button,
    [data-testid="stFileUploaderDropzone"],
    [data-testid="stFileUploaderDropzone"] > div,
    [data-testid="stFileUploaderDropzoneInstructions"] {
        background: #ffffff !important;
        color: #111827 !important;
        border: 1.5px solid #cbd5e1 !important;
        border-radius: 14px !important;
        box-shadow: 0 8px 18px rgba(15, 23, 42, 0.06) !important;
    }
    div.stButton > button *,
    div[data-testid="stDownloadButton"] > button *,
    [data-testid="stFileUploaderDropzone"] button *,
    [data-testid="stBaseButton-secondary"] *,
    section[data-testid="stFileUploader"] button *,
    [data-testid="stFileUploaderDropzone"] *,
    [data-testid="stFileUploaderDropzoneInstructions"] * {
        color: #111827 !important;
    }
    div.stButton > button[kind="primary"] {
        background: #ef4444 !important;
        color: #ffffff !important;
        border-color: #ef4444 !important;
        font-weight: 800 !important;
    }
    div.stButton > button[kind="primary"] * {
        color: #ffffff !important;
    }
    .chat-row { display: flex; align-items: flex-end; gap: 14px; margin: 18px 0; width: 100%; }
    .chat-row.user-row { justify-content: flex-end; }
    .chat-avatar {
        width: 58px; height: 58px; border-radius: 50%; display: flex;
        align-items: center; justify-content: center; flex: 0 0 58px;
        font-size: 2rem; border: 2px solid #94a3b8;
    }
    .bot-avatar { background: transparent; border: 0; }
    .user-avatar { background: #fef3c7; border-color: #f59e0b; }
    .chat-message {
        max-width: 78%; padding: 18px 22px; border-radius: 22px;
        color: #111827 !important; font-size: 1.12rem; line-height: 1.65;
        box-shadow: 0 4px 12px rgba(15, 23, 42, 0.12);
    }
    .bot-message { background: #ffffff; border: 2px solid #60a5fa; border-bottom-left-radius: 6px; }
    .user-message { background: #fff7d6; border: 2px solid #f59e0b; border-bottom-right-radius: 6px; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    f"""
    <div class="hero">
        <h1>🛍️ ShopEase Help Centre {BOT_ICON}</h1>
        <p class="project-name">AI Multilingual FAQ Assistant for Cross-Border E-commerce (PE6201 End-of-Course Project)</p>
        <p>ShopEase Multilingual Support Bot · English · 中文 · Español</p>
    </div>
    """,
    unsafe_allow_html=True,
)

examples = [
    "Where is my money after I sent the item back?",
    "I typed the wrong house address.",
    "我的包裹显示已送达但没收到怎么办？",
    "¿Dónde descargo la factura?",
    "SE-2026-002",
    "Where is my 金钱 after I sent the 东西 back?",
    "Why did my payment fail?",
    "Can I return an item after 14 days?",
    "¿Qué métodos de pago aceptan?",
    "How can I delete my account?",
    "My box arrived cracked. What should I do?",
    "Can you recommend the best laptop for gaming?",
]

routes = [
    ("Singapore", "Kuala Lumpur"),
    ("Shanghai", "Singapore"),
    ("Bangkok", "Singapore"),
    ("Jakarta", "Singapore"),
    ("Seoul", "Singapore"),
]
statuses = [
    ("Delivered", "Paid", "Delivered and received"),
    ("In transit", "Paid", "Estimated delivery in 2-4 days"),
    ("Payment pending", "Unpaid", "Payment is required before dispatch"),
    ("Dispatch pending", "Paid", "Preparing for dispatch"),
    ("Delivery attempted", "Paid", "Courier will attempt delivery again"),
    ("Return requested", "Paid", "Return request is under review"),
    ("Refund processing", "Paid", "Refund is being processed"),
    ("Address confirmation needed", "Paid", "Please confirm the delivery address"),
    ("Customs review", "Paid", "Shipment is under customs review"),
    ("Cancelled", "Unpaid", "Order was cancelled before dispatch"),
]
demo_orders = {}
for number in range(1, 51):
    origin, destination = routes[(number - 1) % len(routes)]
    status, payment, detail = statuses[(number - 1) % len(statuses)]
    demo_orders[f"SE-2026-{number:03d}"] = {
        "route": f"{origin} → {destination}",
        "status": status,
        "payment": payment,
        "detail": detail,
    }

left, right = st.columns([0.8, 1.2], gap="large")

with left:
    st.markdown("### 🛍️ ShopEase Support")
    st.caption("Choose a topic or type your question in the chat.")
    topic_questions = {
        "↩️ Refunds / 退款 / Reembolsos": [
            "Where is my money after I sent the item back?",
            "Can I return an item after 14 days?",
            "我的退款还没有到账怎么办？",
        ],
        "📦 Delivery / 配送 / Entrega": [
            "Where is my parcel and what if it is lost?",
            "我的包裹显示已送达但没收到怎么办？",
            "Can I change my delivery address?",
        ],
        "💳 Payment / 支付 / Pago": [
            "Why did my payment fail?",
            "Why was I charged twice?",
            "¿Qué métodos de pago aceptan?",
        ],
        "🧾 Invoice / 发票 / Factura": [
            "¿Dónde descargo la factura?",
            "How can I correct my invoice details?",
        ],
        "🔐 Account / 账户 / Cuenta": [
            "How can I change my account password?",
            "How can I delete my account?",
        ],
    }
    for label, questions in topic_questions.items():
        if st.button(label, use_container_width=True):
            if st.session_state.get("selected_topic") == label:
                st.session_state.pop("selected_topic", None)
            else:
                st.session_state["selected_topic"] = label
    selected_topic = st.session_state.get("selected_topic")
    if selected_topic:
        st.markdown(f"**Related questions / 相关问题: {selected_topic}**")
        for index, question in enumerate(topic_questions[selected_topic]):
            if st.button(question, key=f"topic_{selected_topic}_{index}", use_container_width=True):
                st.session_state["message_input"] = question
                st.session_state.pop("selected_topic", None)

    st.markdown("### Order details")
    st.caption("This prototype temporarily does not connect to a real store.")
    st.text_input("Order number / 订单号 / Número de pedido", placeholder="Example: SE-2026-001", key="order_number")
    st.file_uploader("Upload an order screenshot (optional)", type=["png", "jpg", "jpeg"], key="order_image")
    check_order = st.button("Check order status / 查询订单状态", use_container_width=True)
    if check_order:
        order_number = st.session_state.get("order_number", "").strip().upper()
        st.session_state["checked_order"] = order_number
        if order_number:
            append_chat(order_number, format_order_answer(order_number, demo_orders.get(order_number)))
    checked_order = st.session_state.get("checked_order")
    if checked_order:
        order = demo_orders.get(checked_order)
        if order:
            st.success(f"Order {checked_order} · {order['status']}")
            st.markdown(
                f"**Route / 路线:** {order['route']}  \n"
                f"**Payment / 付款:** {order['payment']}  \n"
                f"**Update / 状态:** {order['detail']}"
            )
        else:
            st.warning("Demo order not found. Try SE-2026-001, SE-2026-002 or SE-2026-003.")

with right:
    st.markdown(f'<div class="bot-title">{BOT_ICON} ShopEase Multilingual Support Bot</div>', unsafe_allow_html=True)
    st.caption("Online demo assistant · English · 中文 · Español")
    with st.container(border=True):
        st.markdown(
            "**Hi! Ask me about orders, delivery, returns, refunds or payments. "
            "I answer from the approved FAQ only.**\n\n"
            "嗨！如果您有关于订单、配送、退货、退款或付款的问题，请随时向我咨询。\n\n"
            "Hola. Puedo ayudarle con pedidos, entregas, devoluciones, reembolsos y pagos. "
            "Solo respondo usando las preguntas frecuentes aprobadas."
        )
        history = st.session_state.get("chat_history", [])
        chat_parts = ['<div class="chat-history">']
        if not history:
            chat_parts.append(
                f'<div class="chat-row"><div class="chat-avatar bot-avatar">{BOT_ICON}</div>'
                '<div class="chat-message bot-message">How can I help with your order today?<br>'
                '今天我可以怎样帮助您？<br>¿En qué puedo ayudarle hoy?</div></div>'
            )
        for customer_text, answer_text in history:
            safe_customer = escape(customer_text).replace("\n", "<br>")
            safe_answer = escape(answer_text).replace("\n", "<br>")
            chat_parts.append(
                f'<div class="chat-row user-row"><div class="chat-message user-message">{safe_customer}</div>'
                '<div class="chat-avatar user-avatar">👤</div></div>'
            )
            chat_parts.append(
                f'<div class="chat-row"><div class="chat-avatar bot-avatar">{BOT_ICON}</div>'
                f'<div class="chat-message bot-message">{safe_answer}</div></div>'
            )
        chat_parts.append('</div>')
        st.markdown("".join(chat_parts), unsafe_allow_html=True)

    if st.session_state.pop("clear_message_input", False):
        st.session_state["message_input"] = ""
    st.session_state.setdefault("message_input", "")
    query = st.text_area(
        "Your Message / 您的问题 / Su pregunta",
        height=140,
        placeholder="Type your question here... / 请在这里输入问题...",
        key="message_input",
    )
    preferred_reply_language = st.radio(
        "For mixed-language messages only: which language should I use to answer you?",
        ["English", "中文", "Español"],
        horizontal=True,
    )
    send = st.button("Send message", type="primary", use_container_width=True)
    with st.expander("Example customer questions"):
        for example in examples:
            st.write(f"• {example}")

faq_entries = cached_faq()
total_faq_entries = len(faq_entries)
preview_faq_entries = 12
st.markdown(
    f"### 📚 FAQ knowledge base / FAQ 知识库 / Base de conocimiento "
    f"({total_faq_entries} total entries / 共 {total_faq_entries} 条 / {total_faq_entries} entradas en total)"
)
st.caption("This local FAQ file is the retrieval source used by the prototype.")
st.download_button(
    "Open or download the 50-entry FAQ dataset",
    data=FAQ_PATH.read_bytes(),
    file_name="faq.json",
    mime="application/json",
    use_container_width=True,
)
with st.expander("Preview sample FAQ records / 预览部分 FAQ 案例 / Vista previa de FAQ"):
    st.caption(
        f"Showing {preview_faq_entries} representative records on this page. "
        f"The full dataset contains {total_faq_entries} FAQ records and is available from the download button above."
    )
    for entry in faq_entries[:preview_faq_entries]:
        st.markdown(f"**{entry.id} · {entry.source}**")
        st.write(entry.question)
        st.caption(entry.answer)

if send:
    normalized_query = query.strip().upper()
    pending_mixed_query = st.session_state.get("pending_mixed_query")
    explicit_language = requested_reply_language(query)
    if pending_mixed_query and (affirmative_intent(query) or explicit_language):
        response = answer_mixed_followup(
            pending_mixed_query,
            cached_faq(),
            explicit_language or preferred_reply_language,
        )
        baseline = answer_keyword_baseline(pending_mixed_query, cached_faq())
        append_chat(query, response.answer)
        st.session_state["last_query"] = pending_mixed_query
        st.session_state["last_answer"] = response.answer
        st.session_state["last_response"] = response
        st.session_state["last_baseline"] = baseline
        st.session_state.pop("pending_mixed_query", None)
        st.session_state.pop("pending_mixed_language", None)
        st.session_state["clear_message_input"] = True
        st.rerun()
    if normalized_query in demo_orders:
        answer_text = format_order_answer(normalized_query, demo_orders[normalized_query])
        metrics = RunMetrics(
            input_tokens=estimate_tokens(query),
            output_tokens=estimate_tokens(answer_text),
            latency_seconds=0.0,
            estimated_cost_usd=estimate_cost(estimate_tokens(query), estimate_tokens(answer_text)),
        )
        response = AssistantResponse(
            answer=answer_text,
            source_id="ORDER-LOOKUP",
            source_name="Simulated order lookup tool",
            confidence=1.0,
            metrics=metrics,
        )
    elif detect_language(query) == "mixed":
        answer_text = mixed_language_prompt(preferred_reply_language)
        st.session_state["pending_mixed_query"] = query
        st.session_state["pending_mixed_language"] = preferred_reply_language
        metrics = RunMetrics(
            input_tokens=estimate_tokens(query),
            output_tokens=estimate_tokens(answer_text),
            latency_seconds=0.0,
            estimated_cost_usd=estimate_cost(estimate_tokens(query), estimate_tokens(answer_text)),
        )
        response = AssistantResponse(
            answer=answer_text,
            source_id=None,
            source_name=None,
            confidence=0.0,
            metrics=metrics,
        )
    else:
        response = answer_question(query, cached_faq())
    baseline = answer_keyword_baseline(query, cached_faq())
    append_chat(query, response.answer)
    st.session_state["last_query"] = query
    st.session_state["last_answer"] = response.answer
    st.session_state["last_response"] = response
    st.session_state["last_baseline"] = baseline
    st.session_state["clear_message_input"] = True
    st.rerun()

show_details = st.toggle("For Details / 查看课程证据 / Ver detalles", value=False)

if "last_response" in st.session_state and show_details:
    response = st.session_state["last_response"]
    baseline = st.session_state["last_baseline"]
    current_query = st.session_state["last_query"]
    current_case = find_eval_case(current_query)
    faq_entries = cached_faq()

    st.divider()
    st.subheader("For the Coursework Demo: Evidence and Testing")
    st.write("These panels are hidden in a real customer view, but they help prove the prototype is grounded and evaluated.")
    result_col1, result_col2, result_col3 = st.columns(3)
    result_col1.metric("Assistant", "50/50", "100% pass")
    result_col2.metric("Keyword baseline", "33/50", "66% pass")
    result_col3.metric("Language match", "50/50", "100%")

    with st.expander("1. Show RAG / FAQ evidence", expanded=True):
        st.markdown("**Current customer question**")
        st.info(current_query)
        if response.source_id == "ORDER-LOOKUP":
            st.write("This answer came from the simulated order lookup tool, not from the FAQ retrieval database.")
            st.write(f"Tool source: `{response.source_name}`")
            st.write(f"Tool confidence: `{response.confidence:.2f}`")
        elif response.source_id:
            st.write("The assistant did not answer from memory. It retrieved this FAQ record first:")
            st.write(f"Retrieved FAQ ID: `{response.source_id}`")
            st.write(f"FAQ source: `{response.source_name}`")
            st.write(f"Retrieval confidence: `{response.confidence:.2f}`")
        else:
            st.write("No FAQ record was strong enough, so the assistant refused to answer.")
        if response.source_id != "ORDER-LOOKUP":
            st.write("Top retrieved FAQ candidates:")
            st.table(
                [
                    {
                        "rank": index + 1,
                        "faq_id": entry.id,
                        "topic": entry.topic,
                        "language": entry.language,
                        "score": f"{score:.2f}",
                    }
                    for index, (score, entry) in enumerate(top_retrieval_candidates(current_query, faq_entries))
                ]
            )

    with st.expander("2. Compare assistant vs keyword baseline", expanded=True):
        st.markdown("**Current customer question**")
        st.info(current_query)
        if current_case:
            st.write(f"This typed question is in the eval set: `{current_case['id']}`")
            st.write(f"Expected source ID: `{current_case['expected_source_id']}`")
            st.write(f"Expected language: `{current_case['expected_language']}`")
            st.write(f"Required answer terms: `{', '.join(current_case['must_contain'])}`")
        else:
            st.write("This exact typed question is not in the fixed eval set, so the page shows sources and answers but does not mark pass/fail.")
        assistant_col, keyword_col = st.columns(2)
        with assistant_col:
            st.markdown("**Assistant answer**")
            st.write(f"Source ID: `{response.source_id}`")
            st.write(f"Confidence: `{response.confidence:.2f}`")
            st.success(verdict_for_answer(response.source_id, response.answer, current_case))
            st.info(response.answer)
        with keyword_col:
            st.markdown("**Keyword baseline answer**")
            st.write(f"Source ID: `{baseline['source_id']}`")
            st.write(f"Confidence: `{baseline['confidence']:.2f}`")
            st.warning(verdict_for_answer(baseline["source_id"], baseline["answer"], current_case))
            st.info(baseline["answer"])

    with st.expander("3. Show evaluation results"):
        col1, col2, col3 = st.columns(3)
        col1.metric("Assistant", "50/50", "100% pass")
        col2.metric("Keyword baseline", "33/50", "66% pass")
        col3.metric("Language match", "50/50", "100%")
        st.write(
            "The assistant performs better because it adds topic phrases, language preference, "
            "source citation and safe refusal. The keyword baseline is slightly cheaper in raw "
            "estimated tokens, but it misses more natural customer wording."
        )

    with st.expander("4. Show single-run metrics"):
        st.write(
            "These figures are estimated for the current typed question only. "
            "The token-cost estimate uses GPT-4o API pricing as the reference: "
            "USD 2.50 per 1M input tokens and USD 10.00 per 1M output tokens. "
            "A real production deployment would also include monitoring, "
            "human fallback cost and maintenance cost."
        )
        st.table(
            {
                "Metric": ["Input tokens", "Output tokens", "Latency", "Estimated cost"],
                "Value": [
                    response.metrics.input_tokens,
                    response.metrics.output_tokens,
                    f"{response.metrics.latency_seconds:.4f}s",
                    f"${response.metrics.estimated_cost_usd:.8f}",
                ],
            }
        )
