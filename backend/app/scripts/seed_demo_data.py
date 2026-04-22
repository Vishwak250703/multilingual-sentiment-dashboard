"""
Seed ~150 realistic demo reviews to showcase the dashboard.
Reviews span multiple languages, sources, sentiments, products, and date ranges.
Safe to run multiple times — exits immediately if reviews already exist.

Usage:
    python -m app.scripts.seed_demo_data
    docker compose exec backend python -m app.scripts.seed_demo_data
    docker compose -f docker-compose.prod.yml exec backend python -m app.scripts.seed_demo_data
"""
import uuid
import sys
import os
import random
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.tenant import Tenant
from app.models.review import Review

# ─── Seed configuration ───────────────────────────────────────
TOTAL_REVIEWS = 150
DATE_SPREAD_DAYS = 30

SOURCES = ["csv", "api", "webhook", "app_review", "social"]
PRODUCTS = ["mobile-app", "web-platform", "api-service", "enterprise-plan"]
BRANCHES = ["branch-north", "branch-south", "branch-east", "branch-west", None]

# ─── Review templates ─────────────────────────────────────────
# Each template: raw_text, lang, translated_text (or None for English),
# sentiment, score (-1 to 1), confidence, aspects dict, keywords list.

TEMPLATES = [
    # ── ENGLISH · POSITIVE ───────────────────────────────────
    {
        "raw_text": "The product quality exceeded my expectations. Fast delivery and great customer support. Will definitely order again!",
        "lang": "en", "translated_text": None,
        "sentiment": "positive", "score": 0.82, "confidence": 0.91,
        "aspects": {"quality": "positive", "delivery": "positive", "support": "positive"},
        "keywords": ["quality", "fast", "delivery", "support"],
    },
    {
        "raw_text": "Outstanding service! The team resolved my issue within 24 hours. Very professional and helpful.",
        "lang": "en", "translated_text": None,
        "sentiment": "positive", "score": 0.79, "confidence": 0.89,
        "aspects": {"service": "positive", "support": "positive"},
        "keywords": ["service", "professional", "helpful", "resolved"],
    },
    {
        "raw_text": "Best decision I've made this year. The mobile app is incredibly intuitive and has all the features I need.",
        "lang": "en", "translated_text": None,
        "sentiment": "positive", "score": 0.87, "confidence": 0.93,
        "aspects": {"usability": "positive", "performance": "positive"},
        "keywords": ["intuitive", "features", "mobile", "best"],
    },
    {
        "raw_text": "Extremely satisfied with my purchase. The product is high quality and worth every penny.",
        "lang": "en", "translated_text": None,
        "sentiment": "positive", "score": 0.84, "confidence": 0.90,
        "aspects": {"quality": "positive", "price": "positive"},
        "keywords": ["satisfied", "quality", "worth", "purchase"],
    },
    {
        "raw_text": "The customer support team is exceptional! They went above and beyond to help me solve a complex issue.",
        "lang": "en", "translated_text": None,
        "sentiment": "positive", "score": 0.91, "confidence": 0.95,
        "aspects": {"support": "positive", "service": "positive"},
        "keywords": ["support", "exceptional", "helpful", "above and beyond"],
    },
    {
        "raw_text": "Amazing platform! Performance is superb, no downtime in 6 months, and the analytics are outstanding.",
        "lang": "en", "translated_text": None,
        "sentiment": "positive", "score": 0.88, "confidence": 0.92,
        "aspects": {"performance": "positive", "usability": "positive"},
        "keywords": ["performance", "analytics", "platform", "uptime"],
    },
    {
        "raw_text": "Quick response times and excellent service. The product does exactly what is advertised.",
        "lang": "en", "translated_text": None,
        "sentiment": "positive", "score": 0.75, "confidence": 0.87,
        "aspects": {"service": "positive", "quality": "positive"},
        "keywords": ["quick", "service", "advertised", "response"],
    },
    {
        "raw_text": "I've been using this for 6 months and it keeps getting better. Regular updates show they truly care about users.",
        "lang": "en", "translated_text": None,
        "sentiment": "positive", "score": 0.77, "confidence": 0.88,
        "aspects": {"usability": "positive", "service": "positive"},
        "keywords": ["updates", "users", "improving", "months"],
    },
    {
        "raw_text": "Very happy with the API integration. Documentation is clear and the support team was incredibly helpful.",
        "lang": "en", "translated_text": None,
        "sentiment": "positive", "score": 0.81, "confidence": 0.90,
        "aspects": {"usability": "positive", "support": "positive"},
        "keywords": ["API", "documentation", "integration", "clear"],
    },
    {
        "raw_text": "Great value for money. Has all the features of competitors at half the price. Switching was the right call.",
        "lang": "en", "translated_text": None,
        "sentiment": "positive", "score": 0.80, "confidence": 0.89,
        "aspects": {"price": "positive", "usability": "positive"},
        "keywords": ["value", "features", "price", "switching"],
    },
    {
        "raw_text": "The onboarding process was seamless and the team helped us get set up within a day. Excellent experience.",
        "lang": "en", "translated_text": None,
        "sentiment": "positive", "score": 0.83, "confidence": 0.91,
        "aspects": {"service": "positive", "support": "positive"},
        "keywords": ["onboarding", "setup", "seamless", "excellent"],
    },
    {
        "raw_text": "Incredible product! Our team productivity has increased by 40% since adopting this platform.",
        "lang": "en", "translated_text": None,
        "sentiment": "positive", "score": 0.89, "confidence": 0.93,
        "aspects": {"performance": "positive", "usability": "positive"},
        "keywords": ["productivity", "incredible", "platform", "team"],
    },
    {
        "raw_text": "Five stars! The latest update added everything I had been requesting. Love how they listen to feedback.",
        "lang": "en", "translated_text": None,
        "sentiment": "positive", "score": 0.85, "confidence": 0.92,
        "aspects": {"usability": "positive", "service": "positive"},
        "keywords": ["update", "feedback", "listen", "stars"],
    },
    {
        "raw_text": "Reliable, fast, and easy to use. Exactly what our business needed. Highly recommend to anyone.",
        "lang": "en", "translated_text": None,
        "sentiment": "positive", "score": 0.78, "confidence": 0.89,
        "aspects": {"performance": "positive", "usability": "positive"},
        "keywords": ["reliable", "fast", "easy", "business"],
    },
    {
        "raw_text": "Exceptional experience from day one. The training resources are comprehensive and the UI is polished.",
        "lang": "en", "translated_text": None,
        "sentiment": "positive", "score": 0.76, "confidence": 0.88,
        "aspects": {"service": "positive", "usability": "positive"},
        "keywords": ["training", "experience", "UI", "polished"],
    },
    # ── ENGLISH · NEGATIVE ───────────────────────────────────
    {
        "raw_text": "Terrible experience. The app crashed three times and I lost all my work. Completely unacceptable for a paid service.",
        "lang": "en", "translated_text": None,
        "sentiment": "negative", "score": -0.88, "confidence": 0.94,
        "aspects": {"performance": "negative", "usability": "negative"},
        "keywords": ["crashed", "terrible", "lost", "unacceptable"],
    },
    {
        "raw_text": "Customer support is a joke. Waited 5 days for a response and the issue still isn't resolved.",
        "lang": "en", "translated_text": None,
        "sentiment": "negative", "score": -0.81, "confidence": 0.92,
        "aspects": {"support": "negative", "service": "negative"},
        "keywords": ["support", "waited", "unresolved", "slow"],
    },
    {
        "raw_text": "Very disappointed with the product quality. It broke after just 2 weeks of normal use.",
        "lang": "en", "translated_text": None,
        "sentiment": "negative", "score": -0.76, "confidence": 0.90,
        "aspects": {"quality": "negative"},
        "keywords": ["disappointed", "quality", "broke", "defective"],
    },
    {
        "raw_text": "The pricing is outrageous for what you get. Many better alternatives available at half the cost.",
        "lang": "en", "translated_text": None,
        "sentiment": "negative", "score": -0.72, "confidence": 0.88,
        "aspects": {"price": "negative"},
        "keywords": ["pricing", "expensive", "alternatives", "overpriced"],
    },
    {
        "raw_text": "Misleading features listed on the website. The actual product doesn't deliver half of what's promised.",
        "lang": "en", "translated_text": None,
        "sentiment": "negative", "score": -0.79, "confidence": 0.91,
        "aspects": {"quality": "negative", "usability": "negative"},
        "keywords": ["misleading", "features", "promised", "disappointing"],
    },
    {
        "raw_text": "Repeated billing errors that took months to resolve. Very frustrating experience overall.",
        "lang": "en", "translated_text": None,
        "sentiment": "negative", "score": -0.74, "confidence": 0.89,
        "aspects": {"service": "negative", "support": "negative"},
        "keywords": ["billing", "errors", "frustrating", "months"],
    },
    {
        "raw_text": "The delivery was 3 weeks late and the package arrived damaged. No compensation was offered.",
        "lang": "en", "translated_text": None,
        "sentiment": "negative", "score": -0.83, "confidence": 0.92,
        "aspects": {"delivery": "negative", "service": "negative"},
        "keywords": ["delivery", "late", "damaged", "compensation"],
    },
    {
        "raw_text": "Performance has been degrading with each update. The latest version is nearly unusable.",
        "lang": "en", "translated_text": None,
        "sentiment": "negative", "score": -0.77, "confidence": 0.90,
        "aspects": {"performance": "negative"},
        "keywords": ["performance", "update", "degrading", "unusable"],
    },
    {
        "raw_text": "Support team promised a fix within 48 hours. It has been 2 weeks and nothing has changed.",
        "lang": "en", "translated_text": None,
        "sentiment": "negative", "score": -0.80, "confidence": 0.91,
        "aspects": {"support": "negative", "service": "negative"},
        "keywords": ["support", "promised", "fix", "weeks"],
    },
    {
        "raw_text": "Very poor onboarding experience. No documentation, no support, left to figure everything out alone.",
        "lang": "en", "translated_text": None,
        "sentiment": "negative", "score": -0.71, "confidence": 0.88,
        "aspects": {"service": "negative", "usability": "negative"},
        "keywords": ["onboarding", "documentation", "poor", "alone"],
    },
    {
        "raw_text": "The platform goes down almost every weekend. Completely unreliable for any serious business use.",
        "lang": "en", "translated_text": None,
        "sentiment": "negative", "score": -0.85, "confidence": 0.93,
        "aspects": {"performance": "negative"},
        "keywords": ["downtime", "unreliable", "platform", "weekend"],
    },
    {
        "raw_text": "Not worth the price. Basic features are missing and the UI is outdated and confusing to navigate.",
        "lang": "en", "translated_text": None,
        "sentiment": "negative", "score": -0.70, "confidence": 0.87,
        "aspects": {"price": "negative", "usability": "negative"},
        "keywords": ["price", "features", "confusing", "outdated"],
    },
    # ── ENGLISH · NEUTRAL ────────────────────────────────────
    {
        "raw_text": "Product is okay. Does the basic stuff but lacks some advanced features that competitors offer.",
        "lang": "en", "translated_text": None,
        "sentiment": "neutral", "score": 0.02, "confidence": 0.71,
        "aspects": {"usability": "neutral"},
        "keywords": ["basic", "features", "okay"],
    },
    {
        "raw_text": "Average customer service. They eventually solved my problem but it took longer than expected.",
        "lang": "en", "translated_text": None,
        "sentiment": "neutral", "score": 0.05, "confidence": 0.68,
        "aspects": {"service": "neutral", "support": "neutral"},
        "keywords": ["average", "service", "eventually"],
    },
    {
        "raw_text": "Decent value for the price. Nothing spectacular but it gets the job done reliably.",
        "lang": "en", "translated_text": None,
        "sentiment": "neutral", "score": 0.10, "confidence": 0.72,
        "aspects": {"price": "neutral", "quality": "neutral"},
        "keywords": ["decent", "value", "reliable"],
    },
    {
        "raw_text": "Interface is clean but some features are hard to find. Could use better documentation.",
        "lang": "en", "translated_text": None,
        "sentiment": "neutral", "score": 0.03, "confidence": 0.70,
        "aspects": {"usability": "neutral"},
        "keywords": ["interface", "features", "documentation"],
    },
    {
        "raw_text": "Works as advertised. Not the best on the market but reasonable for the price point.",
        "lang": "en", "translated_text": None,
        "sentiment": "neutral", "score": 0.08, "confidence": 0.69,
        "aspects": {"quality": "neutral", "price": "neutral"},
        "keywords": ["advertised", "reasonable", "price"],
    },
    {
        "raw_text": "Some aspects are great, others need significant improvement. Overall a mixed experience.",
        "lang": "en", "translated_text": None,
        "sentiment": "neutral", "score": -0.02, "confidence": 0.66,
        "aspects": {"quality": "neutral", "service": "neutral"},
        "keywords": ["mixed", "improvement", "aspects"],
    },
    {
        "raw_text": "The product is functional but the mobile experience could be significantly improved.",
        "lang": "en", "translated_text": None,
        "sentiment": "neutral", "score": 0.04, "confidence": 0.67,
        "aspects": {"usability": "neutral", "performance": "neutral"},
        "keywords": ["functional", "mobile", "improved"],
    },
    {
        "raw_text": "Customer support was helpful but the resolution process took much longer than it should have.",
        "lang": "en", "translated_text": None,
        "sentiment": "neutral", "score": 0.06, "confidence": 0.70,
        "aspects": {"support": "neutral", "service": "neutral"},
        "keywords": ["support", "helpful", "resolution", "slow"],
    },
    # ── SPANISH ──────────────────────────────────────────────
    {
        "raw_text": "¡Excelente servicio al cliente! Resolvieron mi problema en menos de una hora. Muy recomendado.",
        "lang": "es",
        "translated_text": "Excellent customer service! They resolved my problem in less than an hour. Highly recommended.",
        "sentiment": "positive", "score": 0.82, "confidence": 0.90,
        "aspects": {"service": "positive", "support": "positive"},
        "keywords": ["excelente", "servicio", "recomendado"],
    },
    {
        "raw_text": "El producto es de muy buena calidad y llegó antes de lo esperado. Muy satisfecho con mi compra.",
        "lang": "es",
        "translated_text": "The product is of very good quality and arrived before expected. Very satisfied with my purchase.",
        "sentiment": "positive", "score": 0.78, "confidence": 0.89,
        "aspects": {"quality": "positive", "delivery": "positive"},
        "keywords": ["calidad", "satisfecho", "compra"],
    },
    {
        "raw_text": "Muy decepcionado con el servicio. Tardaron dos semanas en responder y no resolvieron mi problema.",
        "lang": "es",
        "translated_text": "Very disappointed with the service. They took two weeks to respond and did not resolve my problem.",
        "sentiment": "negative", "score": -0.71, "confidence": 0.88,
        "aspects": {"service": "negative", "support": "negative"},
        "keywords": ["decepcionado", "servicio", "semanas"],
    },
    {
        "raw_text": "La aplicación funciona bien en general, aunque le faltan algunas funciones avanzadas.",
        "lang": "es",
        "translated_text": "The app works well in general, although it lacks some advanced features.",
        "sentiment": "neutral", "score": 0.05, "confidence": 0.67,
        "aspects": {"usability": "neutral"},
        "keywords": ["aplicación", "funciones", "avanzadas"],
    },
    {
        "raw_text": "Precio razonable para lo que ofrece. El soporte podría ser más rápido pero es aceptable.",
        "lang": "es",
        "translated_text": "Reasonable price for what it offers. Support could be faster but acceptable.",
        "sentiment": "neutral", "score": 0.12, "confidence": 0.70,
        "aspects": {"price": "neutral", "support": "neutral"},
        "keywords": ["precio", "razonable", "soporte"],
    },
    # ── FRENCH ───────────────────────────────────────────────
    {
        "raw_text": "Très satisfait de mon achat! La qualité du produit est excellente et la livraison très rapide.",
        "lang": "fr",
        "translated_text": "Very satisfied with my purchase! Product quality is excellent and delivery very fast.",
        "sentiment": "positive", "score": 0.79, "confidence": 0.89,
        "aspects": {"quality": "positive", "delivery": "positive"},
        "keywords": ["satisfait", "qualité", "livraison"],
    },
    {
        "raw_text": "Excellent produit! J'utilise cette plateforme depuis 2 ans et elle ne m'a jamais déçu.",
        "lang": "fr",
        "translated_text": "Excellent product! I have been using this platform for 2 years and it has never disappointed me.",
        "sentiment": "positive", "score": 0.87, "confidence": 0.92,
        "aspects": {"quality": "positive", "performance": "positive"},
        "keywords": ["excellent", "produit", "plateforme"],
    },
    {
        "raw_text": "Mauvaise expérience avec le support client. Temps de réponse inacceptable et problème non résolu.",
        "lang": "fr",
        "translated_text": "Bad experience with customer support. Unacceptable response time and unresolved issue.",
        "sentiment": "negative", "score": -0.68, "confidence": 0.87,
        "aspects": {"support": "negative", "service": "negative"},
        "keywords": ["mauvaise", "support", "inacceptable"],
    },
    {
        "raw_text": "Service correct mais les prix ont beaucoup augmenté dernièrement. La qualité reste stable.",
        "lang": "fr",
        "translated_text": "Decent service but prices have increased a lot recently. Quality remains stable.",
        "sentiment": "neutral", "score": 0.08, "confidence": 0.68,
        "aspects": {"service": "neutral", "price": "neutral"},
        "keywords": ["service", "prix", "qualité"],
    },
    # ── GERMAN ───────────────────────────────────────────────
    {
        "raw_text": "Ausgezeichneter Service! Das Produkt hat meine Erwartungen übertroffen. Sehr empfehlenswert!",
        "lang": "de",
        "translated_text": "Excellent service! The product exceeded my expectations. Highly recommended!",
        "sentiment": "positive", "score": 0.84, "confidence": 0.91,
        "aspects": {"service": "positive", "quality": "positive"},
        "keywords": ["ausgezeichnet", "service", "empfehlenswert"],
    },
    {
        "raw_text": "Schlechte Qualität. Das Gerät ist nach zwei Wochen ausgefallen. Kundenservice war wenig hilfreich.",
        "lang": "de",
        "translated_text": "Poor quality. The device failed after two weeks. Customer service was unhelpful.",
        "sentiment": "negative", "score": -0.73, "confidence": 0.89,
        "aspects": {"quality": "negative", "support": "negative"},
        "keywords": ["schlecht", "qualität", "ausgefallen"],
    },
    {
        "raw_text": "Gutes Preis-Leistungs-Verhältnis. Die Software erfüllt die grundlegenden Anforderungen.",
        "lang": "de",
        "translated_text": "Good value for money. The software meets basic requirements.",
        "sentiment": "neutral", "score": 0.15, "confidence": 0.71,
        "aspects": {"price": "neutral", "usability": "neutral"},
        "keywords": ["preis", "leistung", "software"],
    },
    # ── ARABIC ───────────────────────────────────────────────
    {
        "raw_text": "خدمة رائعة وسريعة الاستجابة. المنتج ذو جودة عالية وأنصح به بشدة.",
        "lang": "ar",
        "translated_text": "Wonderful and highly responsive service. The product is of high quality and I strongly recommend it.",
        "sentiment": "positive", "score": 0.81, "confidence": 0.89,
        "aspects": {"service": "positive", "quality": "positive"},
        "keywords": ["خدمة", "جودة", "رائعة"],
    },
    {
        "raw_text": "تجربة مخيبة للآمال. المنتج لا يتطابق مع الوصف المذكور في الموقع.",
        "lang": "ar",
        "translated_text": "Disappointing experience. The product does not match the description on the website.",
        "sentiment": "negative", "score": -0.65, "confidence": 0.86,
        "aspects": {"quality": "negative"},
        "keywords": ["مخيبة", "وصف", "موقع"],
    },
    # ── CHINESE ──────────────────────────────────────────────
    {
        "raw_text": "产品质量非常好，客服响应也很及时，整体体验非常满意，会继续使用并推荐给朋友。",
        "lang": "zh",
        "translated_text": "Product quality is very good, customer service response is timely, overall experience is very satisfying. Will continue using and recommend to friends.",
        "sentiment": "positive", "score": 0.83, "confidence": 0.90,
        "aspects": {"quality": "positive", "support": "positive"},
        "keywords": ["质量", "客服", "满意"],
    },
    {
        "raw_text": "服务质量太差了，等了一周才得到回复，问题依然没有解决，非常失望。",
        "lang": "zh",
        "translated_text": "Service quality is terrible, waited a week for a reply, the problem is still not resolved, very disappointed.",
        "sentiment": "negative", "score": -0.72, "confidence": 0.88,
        "aspects": {"service": "negative", "support": "negative"},
        "keywords": ["服务", "失望", "问题"],
    },
]


def _jitter_score(base_score: float, max_jitter: float = 0.06) -> float:
    """Add small random variation to scores so the data looks natural."""
    jitter = random.uniform(-max_jitter, max_jitter)
    return round(max(-1.0, min(1.0, base_score + jitter)), 3)


def seed():
    engine = create_engine(settings.DATABASE_URL_SYNC)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Find the default tenant (created by seed_admin.py)
        tenant = session.execute(select(Tenant).limit(1)).scalar_one_or_none()
        if not tenant:
            print("No tenant found. Run seed_admin.py first, then re-run this script.")
            return

        # Guard: skip if any reviews already exist for this tenant
        existing_count = session.execute(
            select(func.count(Review.id)).where(Review.tenant_id == tenant.id)
        ).scalar() or 0

        if existing_count > 0:
            print(f"Tenant '{tenant.name}' already has {existing_count} review(s). Skipping demo seed.")
            return

        # ── Generate reviews from templates ───────────────────
        now = datetime.now(timezone.utc)
        reviews_to_insert = []

        for i in range(TOTAL_REVIEWS):
            template = TEMPLATES[i % len(TEMPLATES)]

            # Weight recent days more heavily (simulate active usage)
            # last 7 days = weight 10, days 8–14 = weight 4, days 15–30 = weight 1
            day_weights = [10 if d < 7 else 4 if d < 14 else 1 for d in range(DATE_SPREAD_DAYS)]
            days_ago = random.choices(range(DATE_SPREAD_DAYS), weights=day_weights)[0]
            hours_ago = random.randint(0, 23)
            mins_ago = random.randint(0, 59)
            created_at = now - timedelta(days=days_ago, hours=hours_ago, minutes=mins_ago)

            review = Review(
                id=str(uuid.uuid4()),
                tenant_id=tenant.id,
                raw_text=template["raw_text"],
                translated_text=template.get("translated_text"),
                original_language=template["lang"],
                detected_language=template["lang"],
                source=random.choice(SOURCES),
                product_id=random.choice(PRODUCTS),
                branch_id=random.choice(BRANCHES),
                sentiment=template["sentiment"],
                sentiment_score=_jitter_score(template["score"]),
                confidence=round(min(1.0, template["confidence"] + random.uniform(-0.04, 0.04)), 3),
                sentence_sentiments=[
                    {
                        "sentence": template["raw_text"][:120],
                        "sentiment": template["sentiment"],
                        "score": _jitter_score(template["score"]),
                    }
                ],
                aspects=template.get("aspects", {}),
                keywords=template.get("keywords", []),
                is_pii_masked=False,
                processing_status="completed",
                review_date=created_at,
                created_at=created_at,
                processed_at=created_at,
            )
            reviews_to_insert.append(review)

        session.bulk_save_objects(reviews_to_insert)
        session.commit()

        # Summary
        pos = sum(1 for r in reviews_to_insert if r.sentiment == "positive")
        neg = sum(1 for r in reviews_to_insert if r.sentiment == "negative")
        neu = sum(1 for r in reviews_to_insert if r.sentiment == "neutral")
        langs = set(r.detected_language for r in reviews_to_insert)

        print(f"Demo data seeded successfully for tenant '{tenant.name}'")
        print(f"  Total reviews : {len(reviews_to_insert)}")
        print(f"  Positive      : {pos}  ({round(pos/len(reviews_to_insert)*100)}%)")
        print(f"  Negative      : {neg}  ({round(neg/len(reviews_to_insert)*100)}%)")
        print(f"  Neutral       : {neu}  ({round(neu/len(reviews_to_insert)*100)}%)")
        print(f"  Languages     : {', '.join(sorted(langs))}")
        print(f"  Date range    : last {DATE_SPREAD_DAYS} days")

    except Exception as e:
        session.rollback()
        print(f"Error seeding demo data: {e}")
        raise
    finally:
        session.close()
        engine.dispose()


if __name__ == "__main__":
    seed()
