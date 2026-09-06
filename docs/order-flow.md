ShopOnBot Order Service API --- Architecture & End-to-End Flow

Purpose: This document defines the production-oriented
architecture, responsibilities, APIs, database design, order
lifecycle, payment lifecycle, Kafka events, and end-to-end flows of
shoponbot-order-service-api.

1. System Position

The Order Service is responsible for everything that happens after a
customer decides to place an order.

It owns:

Checkout

Orders

Order items

Payment orchestration

Payment webhooks

Order/payment state transitions

Order-related domain events

It does not own the shopping cart, authentication, users, or
products.

High-level architecture

flowchart TB
    FE[Next.js Frontend]

    NG[Nginx API Gateway]

    BE[Backend API]
    OS[Order Service]
    AI[AI Service]
    NS[Notification Service]

    DB[(PostgreSQL)]
    K[(Kafka)]

    PG[Payment Gateway]

    FE --> NG

    NG -->|/api/v1/auth/*| BE
    NG -->|/api/v1/products/*| BE
    NG -->|/api/v1/cart/*| BE
    NG -->|/api/v1/orders/*| OS

    BE --> DB
    OS --> DB

    OS -->|Payment API| PG
    PG -->|Webhook| NG
    NG -->|/api/v1/orders/payments/webhook| OS

    OS -->|Domain Events| K

    K --> NS
    K --> AI

2. Service Responsibilities

Backend API

Owns:

Authentication
Users
Products
Cart
Cart Items

Order Service

Owns:

Checkout
Orders
Order Items
Payments
Payment Attempts
Payment Webhooks
Order State Transitions
Order Events

Notification Service

Consumes events and handles:

Email
SMS
WhatsApp
Push Notifications

AI Service

Can consume order events for:

Recommendations
Customer insights
Sales analysis
AI-powered business intelligence

3. Public API Boundary

All Order Service APIs are exposed through:

/api/v1/orders

Nginx routes:

location /api/v1/orders/ {
    proxy_pass http://order_service:8002/;
}

Therefore:

Browser
  /api/v1/orders/checkout
          |
          v
Nginx
          |
          v
order_service:8002/checkout

The Order Service itself does not need to know that Nginx exists for its
internal route definitions.

4. API Design

Orders

Method   Endpoint                             Responsibility

GET      /api/v1/orders                     Get user's orders
GET      /api/v1/orders/{order_id}          Get one order
POST     /api/v1/orders/checkout            Convert cart into an order
POST     /api/v1/orders/{order_id}/cancel   Cancel an order
GET      /api/v1/orders/{order_id}/status   Get order status

Payments

Method                  Endpoint                                 Responsibility

POST                    /api/v1/orders/payments/create         Create payment attempt

GET                     /api/v1/orders/payments/{payment_id}   Get payment information

Additional payment endpoints can be added later for refunds, retries,
or payment-method specific operations.

5. Internal Application Architecture

Every request follows this structure:

flowchart LR
    R[HTTP Request]
    API[API / Router]
    S[Service Layer]
    REP[Repository Layer]
    DB[(PostgreSQL)]

    R --> API
    API --> S
    S --> REP
    REP --> DB

External integrations are called from the service layer:

flowchart TB
    API[API Layer]
    S[Service Layer]

    DB[(PostgreSQL)]
    CART[Cart Client]
    PAY[Payment Gateway]
    K[Kafka Producer]

    API --> S

    S --> DB
    S --> CART
    S --> PAY
    S --> K

Rule

Routers should remain thin.

Bad:

@router.post("/checkout")
async def checkout():
    # validation
    # database queries
    # payment logic
    # Kafka logic
    # 100+ lines

Preferred:

@router.post("/checkout")
async def checkout(...):
    return await checkout_service.checkout(...)

6. Checkout --- Complete Flow

Checkout is the most important business flow.

sequenceDiagram
    participant U as User
    participant FE as Frontend
    participant N as Nginx
    participant O as Order Service
    participant C as Cart
    participant DB as PostgreSQL
    participant P as Payment Gateway
    participant K as Kafka

    U->>FE: Click "Place Order"
    FE->>N: POST /api/v1/orders/checkout
    N->>O: POST /checkout

    O->>C: Get user's cart
    C-->>O: Cart + Cart Items

    O->>O: Validate cart
    O->>O: Calculate subtotal/tax/shipping/discount
    O->>DB: Create Order
    O->>DB: Create Order Items
    O->>DB: Create Payment Attempt

    O->>DB: COMMIT

    O->>K: Publish order.created

    O-->>N: Checkout Response
    N-->>FE: Order + Payment Information
    FE-->>U: Show payment screen

    FE->>P: Start payment

Important transaction rule

The database transaction should finish before the event is considered
successfully published.

Conceptually:

Validate
   ↓
Create Order
   ↓
Create Order Items
   ↓
Create Payment
   ↓
COMMIT
   ↓
Publish order.created

For stronger production reliability, an Outbox Pattern can later be
introduced so DB commit and event publication are reliably coordinated.

7. Checkout Idempotency

Checkout must protect against duplicate requests.

Example:

User clicks "Place Order"
        |
        v
Request A
        |
        X Network timeout
        |
        v
Frontend retries
        |
        v
Request B

Without idempotency:

Order #1001
Order #1002

could accidentally be created.

Therefore:

POST /api/v1/orders/checkout
Idempotency-Key: checkout-abc-123

The service stores the key and associates it with the created
operation/order.

If the same key is received again:

Existing operation
       ↓
Return previous result

instead of creating another order.

8. Database Model

Entity relationship

erDiagram
    ORDERS ||--|{ ORDER_ITEMS : contains
    ORDERS ||--o{ PAYMENTS : has
    ORDERS {
        bigint id PK
        bigint user_id
        string order_number UK
        string status
        string payment_status
        decimal subtotal
        decimal tax
        decimal shipping_fee
        decimal discount
        decimal total_amount
        string currency
        json shipping_address
        datetime created_at
        datetime updated_at
    }

    ORDER_ITEMS {
        bigint id PK
        bigint order_id FK
        bigint product_id
        string product_name
        decimal product_price
        int quantity
        decimal subtotal
        datetime created_at
    }

    PAYMENTS {
        bigint id PK
        bigint order_id FK
        string provider
        string provider_payment_id
        decimal amount
        string currency
        string status
        string payment_method
        string failure_reason
        datetime created_at
        datetime updated_at
    }

9. Why Order Items Store Product Snapshots

Suppose the customer purchases:

Product: Wireless Headphones
Price: ₹999
Quantity: 2

The order stores:

product_name  = Wireless Headphones
product_price = 999
quantity      = 2

Later the product price changes:

₹999 → ₹1299

The old order must still display:

Wireless Headphones
₹999
2 ×

Therefore, historical order data should not depend on the current
product price.

10. Payment Model

One order may have multiple payment attempts:

flowchart TB
    O[Order #1001]

    O --> P1[Payment Attempt 1]
    O --> P2[Payment Attempt 2]
    O --> P3[Payment Attempt 3]

    P1 --> F1[FAILED]
    P2 --> F2[FAILED]
    P3 --> S3[SUCCESS]

Example:

Order #1001

Attempt 1 → Failed
Attempt 2 → Failed
Attempt 3 → Successful

This preserves payment history instead of overwriting the previous
attempt.

11. Order State Machine

Recommended order lifecycle:

stateDiagram-v2
    [*] --> PENDING

    PENDING --> PAYMENT_PENDING
    PENDING --> CANCELLED

    PAYMENT_PENDING --> CONFIRMED
    PAYMENT_PENDING --> PAYMENT_FAILED
    PAYMENT_PENDING --> CANCELLED

    CONFIRMED --> PROCESSING
    CONFIRMED --> CANCELLED

    PROCESSING --> SHIPPED

    SHIPPED --> DELIVERED

    DELIVERED --> [*]
    CANCELLED --> [*]
    PAYMENT_FAILED --> [*]

States

PENDING
PAYMENT_PENDING
PAYMENT_FAILED
CONFIRMED
PROCESSING
SHIPPED
DELIVERED
CANCELLED

Future states can include:

RETURN_REQUESTED
RETURNED
REFUNDED

12. Payment State Machine

stateDiagram-v2
    [*] --> PENDING

    PENDING --> SUCCESS
    PENDING --> FAILED

    SUCCESS --> REFUNDED

    FAILED --> [*]
    REFUNDED --> [*]

Future:

PARTIALLY_REFUNDED

can be added when partial refunds are implemented.

13. Payment Flow

sequenceDiagram
    participant FE as Frontend
    participant O as Order Service
    participant P as Payment Gateway
    participant N as Nginx
    participant DB as PostgreSQL
    participant K as Kafka

    FE->>O: Create/Start Payment
    O->>P: Create payment
    P-->>O: Payment details

    O->>DB: Save payment attempt
    O->>DB: COMMIT

    O-->>FE: Payment information

    FE->>P: Complete payment

    P->>N: POST payment webhook
    N->>O: Forward webhook

    O->>P: Verify webhook/signature
    P-->>O: Valid

    O->>DB: Payment = SUCCESS
    O->>DB: Order = CONFIRMED
    O->>DB: COMMIT

    O->>K: payment.succeeded
    O->>K: order.confirmed

14. Payment Failure Flow

sequenceDiagram
    participant P as Payment Gateway
    participant N as Nginx
    participant O as Order Service
    participant DB as PostgreSQL
    participant K as Kafka

    P->>N: Payment failed webhook
    N->>O: Forward webhook

    O->>O: Verify webhook

    O->>DB: Payment = FAILED
    O->>DB: Order = PAYMENT_FAILED
    O->>DB: COMMIT

    O->>K: Publish payment.failed

15. Kafka Event Architecture

The Order Service is primarily an event producer.

flowchart LR
    O[Order Service]

    K[Kafka]

    NS[Notification Service]
    AI[AI Service]
    AN[Analytics / Future Service]

    O --> K

    K --> NS
    K --> AI
    K --> AN

16. Domain Events

Order events

order.created
order.confirmed
order.cancelled
order.shipped
order.delivered

Payment events

payment.succeeded
payment.failed
payment.refunded

17. Kafka Topics

Initial topic design:

orders.events
payments.events

orders.events

order.created
order.confirmed
order.cancelled
order.shipped
order.delivered

payments.events

payment.succeeded
payment.failed
payment.refunded

Avoid creating a separate Kafka topic for every event unless a future
scaling or ownership requirement justifies it.

18. Event Envelope

All events should use a consistent envelope.

Example:

{
  "event_id": "uuid",
  "event_type": "order.created",
  "event_version": 1,
  "occurred_at": "2026-09-04T12:00:00Z",
  "source": "order-service",
  "data": {
    "order_id": 123,
    "user_id": 45,
    "order_number": "ORD-20260904-001",
    "total_amount": 2499,
    "currency": "INR"
  }
}

Why these fields exist

Field             Purpose

event_id        Unique event identity
event_type      Identifies the business event
event_version   Allows event schema evolution
occurred_at     Event timestamp
source          Identifies producer
data            Actual event payload

19. What Happens After order.created?

flowchart TB
    O[Order Service]
    K[Kafka]
    N[Notification Service]
    AI[AI Service]

    O -->|order.created| K

    K --> N
    K --> AI

    N --> E[Send Order Confirmation]
    N --> W[WhatsApp / Email / SMS]

    AI --> R[Recommendations / Analytics]

The Order Service does not directly call Notification Service for every
notification.

Instead:

Order Service
      ↓
Kafka
      ↓
Notification Service

This keeps services loosely coupled.

20. Order Cancellation

sequenceDiagram
    participant FE as Frontend
    participant O as Order Service
    participant DB as PostgreSQL
    participant K as Kafka

    FE->>O: POST /orders/{id}/cancel

    O->>DB: Load Order
    O->>O: Validate cancellation rules

    O->>DB: Order = CANCELLED
    O->>DB: COMMIT

    O->>K: order.cancelled

    O-->>FE: Updated Order

Cancellation rules should be enforced inside the Order Service, not
trusted from the frontend.

21. Order Shipping

A future admin/warehouse operation can trigger:

POST /api/v1/orders/{order_id}/ship

Flow:

Admin/Warehouse
       ↓
Order Service
       ↓
Validate order
       ↓
Order = SHIPPED
       ↓
COMMIT
       ↓
order.shipped
       ↓
Kafka
       ↓
Notification Service
       ↓
Customer notification

22. Complete End-to-End Order Journey

flowchart TD
    A[Customer adds products to Cart]
    B[Cart owned by Backend API]
    C[Customer clicks Checkout]
    D[POST /api/v1/orders/checkout]

    E[Order Service validates Cart]
    F[Calculate totals]
    G[Create Order]
    H[Create Order Items]
    I[Create Payment Attempt]
    J[DB Commit]

    K[order.created]
    L[Kafka]

    M[Customer completes payment]
    N[Payment Gateway]
    O[Webhook]
    P[Verify webhook]

    Q[Payment SUCCESS]
    R[Order CONFIRMED]
    S[DB Commit]

    T[payment.succeeded]
    U[order.confirmed]

    V[Order Processing]
    W[Order Shipped]
    X[Order Delivered]

    A --> B --> C --> D
    D --> E --> F --> G --> H --> I --> J
    J --> K --> L

    D --> M --> N --> O --> P
    P --> Q --> R --> S
    S --> T
    S --> U

    R --> V --> W --> X

23. Failure Scenarios

Payment Failure

Payment Gateway
      ↓
Webhook
      ↓
Order Service
      ↓
Payment = FAILED
      ↓
Order = PAYMENT_FAILED
      ↓
payment.failed

Duplicate Checkout

Request A
   ↓
Idempotency Key
   ↓
Order created

Request B
   ↓
Same Idempotency Key
   ↓
Return existing result

Network Timeout

The frontend should be able to safely retry an idempotent operation.

Kafka Failure

A production implementation should not lose an important domain event
merely because Kafka is temporarily unavailable.

Recommended evolution:

DB Transaction
      ↓
Outbox Table
      ↓
Outbox Publisher
      ↓
Kafka

This is the Transactional Outbox Pattern and can be introduced when
event reliability becomes a requirement.

24. Transaction Boundary

For important state changes:

BEGIN
   ↓
Validate
   ↓
Write DB changes
   ↓
COMMIT

If something fails:

ROLLBACK

Example:

Create Order
Create Order Items
Create Payment
      |
      X error
      |
   ROLLBACK

No partially-created order should remain.

25. Pydantic Schema Design

Recommended structure:

schemas/
├── checkout.py
├── order.py
├── payment.py
└── event.py

checkout.py

CheckoutRequest
CheckoutResponse

order.py

OrderResponse
OrderItemResponse
OrderStatusResponse
CancelOrderRequest

payment.py

PaymentCreateRequest
PaymentResponse
PaymentWebhookRequest

event.py

OrderCreatedEvent
OrderConfirmedEvent
OrderCancelledEvent
PaymentSucceededEvent
PaymentFailedEvent

26. SQLAlchemy Model Structure

Recommended:

models/
├── order.py
├── order_item.py
├── payment.py
└── __init__.py

Relationships:

Order
 ├── order_items
 └── payments

OrderItem
 └── belongs to Order

Payment
 └── belongs to Order

27. Final Project Structure

shoponbot-order-service-api/
│
├── app/
│   ├── main.py
│   │
│   ├── core/
│   │   ├── config.py
│   │   ├── security.py
│   │   └── logging.py
│   │
│   ├── db/
│   │   ├── session.py
│   │   └── base.py
│   │
│   ├── models/
│   │   ├── order.py
│   │   ├── order_item.py
│   │   ├── payment.py
│   │   └── __init__.py
│   │
│   ├── schemas/
│   │   ├── checkout.py
│   │   ├── order.py
│   │   ├── payment.py
│   │   ├── event.py
│   │   └── __init__.py
│   │
│   ├── api/
│   │   └── v1/
│   │       ├── router.py
│   │       └── endpoints/
│   │           ├── orders.py
│   │           ├── checkout.py
│   │           └── payments.py
│   │
│   ├── services/
│   │   ├── order_service.py
│   │   ├── checkout_service.py
│   │   ├── payment_service.py
│   │   └── order_status_service.py
│   │
│   ├── repositories/
│   │   ├── order_repository.py
│   │   ├── order_item_repository.py
│   │   └── payment_repository.py
│   │
│   ├── integrations/
│   │   ├── cart_client.py
│   │   └── payment/
│   │       ├── base.py
│   │       └── razorpay.py
│   │
│   ├── messaging/
│   │   ├── producer.py
│   │   ├── topics.py
│   │   └── events.py
│   │
│   └── utils/
│       └── idempotency.py
│
├── migrations/
│
├── tests/
│   ├── unit/
│   └── integration/
│
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── uv.lock
└── .env

28. Responsibility Matrix

Responsibility        Backend API  Order Service        Kafka   Notification           AI

Auth                           ✅

Users                          ✅

Products                       ✅

Cart                           ✅   Read/consume

Checkout                                      ✅

Orders                                        ✅

Payments                                      ✅

Payment Webhook                               ✅

Order State                                   ✅

Order Events                             Produce           ✅        Consume      Consume

Email/SMS/WhatsApp                                                        ✅

AI Analytics                                                                           ✅

29. Architecture Principles

The Order Service should follow these principles:

1. Single Responsibility

Order Service owns order-related business logic.

2. Thin API Layer

Routers should delegate to services.

3. Transactional Database Operations

Related writes should happen inside one transaction.

4. Idempotency

Checkout/payment operations must safely handle retries.

5. Event-Driven Communication

Use Kafka for asynchronous cross-service communication.

6. Loose Coupling

Order Service should not directly depend on Notification Service
implementation.

7. Historical Accuracy

Order items store historical product information.

8. Provider Abstraction

Payment gateway-specific code should stay behind a payment interface.

9. Event Versioning

Kafka events should be versioned from the beginning.

10. Reliability Evolution

When needed, introduce the Transactional Outbox Pattern for guaranteed
event publication.

30. Final Mental Model

Remember the entire architecture as:

                    CUSTOMER
                       |
                       v
                  NEXT.JS APP
                       |
                       v
                     NGINX
                       |
          +------------+-------------+
          |                          |
          v                          v
     BACKEND API              ORDER SERVICE
          |                          |
          |                    +-----+-----+
          |                    |     |     |
          v                    v     v     v
        CART                ORDER PAYMENT KAFKA
          |                    |     |
          +--------+-----------+     |
                   |                 |
                   v                 v
              POSTGRESQL      PAYMENT GATEWAY
                                     |
                                     v
                                  WEBHOOK
                                     |
                                     v
                              ORDER SERVICE
                                     |
                                     v
                                   KAFKA
                                     |
                    +----------------+----------------+
                    |                                 |
                    v                                 v
             NOTIFICATION                         AI SERVICE
                SERVICE

One-line summary

Frontend requests → Nginx routes → Order Service executes business
logic → PostgreSQL stores transactional state → Kafka broadcasts
domain events → other services react asynchronously.

31. Implementation Order

Once this architecture is frozen, implementation should proceed in this
order:

1. Database models
       ↓
2. Alembic migrations
       ↓
3. Pydantic schemas
       ↓
4. Repository layer
       ↓
5. Order service
       ↓
6. Checkout service
       ↓
7. Payment abstraction
       ↓
8. APIs
       ↓
9. Kafka producer
       ↓
10. Idempotency
       ↓
11. Payment webhook
       ↓
12. Tests

This document is the architecture baseline. Any future change to
order states, payment states, database relationships, APIs, or Kafka
events should be intentionally reviewed against this design before
implementation.