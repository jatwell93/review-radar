import os
from datetime import datetime

import stripe
from fastapi import APIRouter, HTTPException, Request
from supabase import create_client

# Validate all required env vars at startup — fail fast rather than cryptic errors at request time
_REQUIRED_ENV_VARS = [
    "STRIPE_SECRET_KEY",
    "STRIPE_WEBHOOK_SECRET",
    "STRIPE_PRICE_ID",
    "SUPABASE_URL",
    "SUPABASE_SERVICE_ROLE_KEY",
    "FRONTEND_URL",
]
for _var in _REQUIRED_ENV_VARS:
    if not os.getenv(_var):
        raise RuntimeError(f"Missing required environment variable: {_var}")

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

router = APIRouter(prefix="/stripe", tags=["stripe"])


def _get_supabase_admin():
    return create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
    )


@router.post("/checkout-session")
def create_checkout_session(request: Request):
    # Extract and validate Bearer token
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = auth_header.removeprefix("Bearer ").strip()

    # Validate token against Supabase — getUser validates JWT server-side
    supabase = _get_supabase_admin()
    user_response = supabase.auth.get_user(token)
    if not user_response or not user_response.user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = user_response.user

    # Gate: return 409 if user already has an active subscription (prevents double-billing)
    # Use limit(1) + list index — maybe_single() returns None (not a response) on no-row in supabase-py v2
    existing_result = (
        supabase.table("subscriptions")
        .select("status, stripe_customer_id")
        .eq("user_id", str(user.id))
        .limit(1)
        .execute()
    )
    existing_data = existing_result.data[0] if existing_result.data else None
    if existing_data and existing_data.get("status") == "active":
        raise HTTPException(status_code=409, detail={"error": "subscription_already_active"})

    # Reuse existing Stripe customer if available (handles re-subscribers)
    stripe_customer_id = existing_data.get("stripe_customer_id") if existing_data else None
    if not stripe_customer_id:
        customer = stripe.Customer.create(
            email=user.email,
            metadata={"user_id": str(user.id)},
        )
        stripe_customer_id = customer.id

    # Create Stripe hosted checkout session
    session = stripe.checkout.Session.create(
        customer=stripe_customer_id,
        mode="subscription",
        line_items=[{"price": os.getenv("STRIPE_PRICE_ID"), "quantity": 1}],
        success_url=f"{os.getenv('FRONTEND_URL')}/dashboard/upgrade/success",
        cancel_url=f"{os.getenv('FRONTEND_URL')}/dashboard/upgrade/cancel",
        metadata={"user_id": str(user.id)},
    )
    return {"url": session.url}


@router.post("/webhook")
async def stripe_webhook(request: Request):
    # Raw body required for signature verification — do NOT use Pydantic model
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    if not sig_header:
        raise HTTPException(status_code=400, detail="Missing Stripe-Signature header")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, os.getenv("STRIPE_WEBHOOK_SECRET")
        )
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    supabase = _get_supabase_admin()
    event_type = event["type"]
    obj = event["data"]["object"]

    if event_type == "checkout.session.completed":
        user_id = obj["metadata"]["user_id"]
        stripe_customer_id = obj["customer"]
        stripe_subscription_id = obj["subscription"]

        # Retrieve subscription — access via attribute, not .get() (StripeObject, not dict)
        sub = stripe.Subscription.retrieve(stripe_subscription_id)
        raw_cpe = getattr(sub, "current_period_end", None)
        current_period_end = (
            datetime.utcfromtimestamp(raw_cpe).isoformat() if raw_cpe else None
        )

        # Upsert with user_id as conflict key — idempotent on Stripe webhook retries
        # If this raises, propagate as 500 so Stripe retries delivery
        supabase.table("subscriptions").upsert(
            {
                "user_id": user_id,
                "stripe_customer_id": stripe_customer_id,
                "stripe_subscription_id": stripe_subscription_id,
                "status": "active",
                "current_period_end": current_period_end,
                "updated_at": datetime.utcnow().isoformat(),
            },
            on_conflict="user_id",
        ).execute()

    elif event_type == "customer.subscription.updated":
        # Handles past_due, unpaid, canceled transitions before hard deletion
        stripe_subscription_id = obj["id"]
        new_status = obj["status"]
        supabase.table("subscriptions").update(
            {
                "status": new_status,
                "updated_at": datetime.utcnow().isoformat(),
            }
        ).eq("stripe_subscription_id", stripe_subscription_id).execute()

    elif event_type == "customer.subscription.deleted":
        stripe_subscription_id = obj["id"]
        supabase.table("subscriptions").update(
            {
                "status": "canceled",
                "updated_at": datetime.utcnow().isoformat(),
            }
        ).eq("stripe_subscription_id", stripe_subscription_id).execute()

    # Silently return 200 for unhandled event types
    return {"received": True}
