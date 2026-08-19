# Implemented MVP Scope

## Purpose

The capstone MVP demonstrates how a Digital Product Passport can connect a
manufacturer's installed product base with lifecycle records and an existing
after-sales support platform. Safe equipment is used as the case study, but the
configurable template model is not limited to safes.

The implementation is a proof of concept for one organization-level workflow,
not a universal DPP interoperability platform or a production service.

## End-to-end workflow

1. Reference product categories and roles are seeded.
2. An organization administrator creates and activates a versioned passport
   template for an active category.
3. The administrator creates an active product model tied to one exact active
   template version.
4. An administrator or service technician registers a physical product item.
   This also supports retrospective registration of an already installed item.
5. Passport values are entered manually or proposed from a PDF/image through
   Gemini and reviewed by the user.
6. The item is published after all required template values pass validation.
7. A customer opens the public passport through its URL, a generated QR code,
   or a supported NFC tag.
8. Organization staff append public or restricted lifecycle events.
9. A customer submits a support ticket from the public passport. The backend
   creates an Azure DevOps work item and sends a private tracking code by email.
10. The public passport provides a generic tracking action but reveals no
    ticket number, count, date, status, or message before verification.
11. The customer enters the ticket number and private code from email to open a
    ticket, read customer-visible support comments, and reply while it remains
    open. When tracking starts from a passport, the backend additionally checks
    that the ticket belongs to that product.

## Implemented roles and permissions

Each user has exactly one role. Permissions are enforced by the backend and
organization ownership is derived from the authenticated user.

### Organization administrator (`manufacturer_user`)

Can:

- manage the organization's profile, contact data, logo, and Azure DevOps Area
  Path/work-item type;
- create, version, activate, and archive passport templates;
- create and update product models and model images;
- create, activate, and deactivate service-technician accounts;
- register, edit, publish, and retire product items;
- generate item QR codes and add lifecycle events.

### Service technician (`service_technician`)

Can:

- view active templates and active models in the same organization;
- register draft product items, including historical installed products;
- use AI-assisted extraction, edit drafts, and publish complete items;
- view product items and add lifecycle events.

Cannot manage templates, models, organization settings, team members, or retire
a published item.

### Platform administrator (`system_admin`)

The role exists in reference data and authorization helpers, but platform-level
administration screens and category-management endpoints are outside the
implemented MVP. Product categories are currently read-only through the public
category API and maintained by the seed script.

## Implemented entities

- `Organization`
- `User`
- `Role`
- `ProductCategory`
- `PassportTemplate`
- `TemplateField`
- `ProductModel`
- `ProductItem`
- `LifecycleEvent`
- `SupportTicket`

QR codes are generated from a product item's existing public identifier and are
not stored as separate database records. NFC writes the same URL. There is no
implemented `DataCarrier` table.

## Entity responsibilities

### Organization

Represents a manufacturer. It stores contact details, Cloudinary logo metadata,
and non-secret Azure DevOps routing settings. The Azure PAT and all other
credentials remain server-side environment settings.

### User and Role

Represent an authenticated account and its single permission set. Organization
administrators and technicians must belong to an organization; a platform
administrator may have none. Active status is checked on every authenticated
request.

### ProductCategory

Represents a seeded hierarchical product classification. Implemented public
endpoints return a flat collection containing `parent_category_id`, allowing a
client to construct the hierarchy.

### PassportTemplate and TemplateField

One template row represents one exact version. All versions in a family share
`template_family_id`. A family may contain at most one Draft. Draft field
definitions are editable; Active and Archived definitions are immutable. A new
version copies the latest completed version and its fields into a new Draft.

Supported field types are text, integer, decimal, boolean, and date. Fields can
be required or optional and public or manufacturer-only, with type-specific
validation rules.

### ProductModel

Represents a commercial product model owned by one organization. It references
one exact active template version and category. Its model code is unique inside
the organization. Name, description, status, and optional Cloudinary image can
be managed after creation, while ownership, code, category, and template remain
fixed.

### ProductItem

Represents one physical product. Its serial number is unique inside the
organization and its random `public_id` is used in the public passport URL.
Configurable values are stored as JSONB and validated against the product
model's exact template version.

Items follow the one-way lifecycle:

```text
Draft -> Published -> Retired
```

Drafts can be incomplete. Publishing requires every required field. Published
identity and passport values are immutable; only an organization administrator
can retire the item.

### LifecycleEvent

Records manufacturing, installation, inspection, maintenance, repair,
certification, retirement, or another event for a published/retired product.
Every new event records its creator and access level. Only public events are
included in the public passport.

### SupportTicket

Stores the link between a product item and its Azure DevOps work-item number,
idempotency metadata, a one-way hash of the private tracking code, and delivery
state. The complete work-item status and conversation remain in Azure DevOps
and are loaded on demand.

## Main business rules

1. All organization-owned queries enforce the current user's organization.
2. A product model must use an active category and an active template belonging
   to the same organization and category.
3. Only Draft template fields can be changed.
4. One template family can contain no more than one Draft version.
5. Product serial numbers and model codes are unique per organization.
6. Only Published product items are returned by the public passport API.
7. Public responses contain only public template fields and public lifecycle
   events; restricted values are filtered on the server.
8. QR and NFC payloads contain only the public passport URL.
9. AI extraction returns reviewable suggestions and never modifies a product
   item automatically.
10. Public support submission requires an idempotency key and is protected by a
    short in-process rate limit.
11. One optional support attachment must be PNG, JPEG, or WebP and no larger
    than 5 MB; its byte signature is checked before upload to Azure DevOps.
12. Ticket tracking requires both the Azure ticket number and the emailed
    private code. Only Azure comments beginning with `@customer` are shown.
13. A Closed Azure ticket remains available for tracking but cannot receive new
    customer messages through either the UI or API.
14. The public passport does not provide a ticket-list endpoint. Failed ticket,
    code, and product-context checks return the same generic response.

## API surface

FastAPI also provides `GET /health` and interactive OpenAPI documentation at
`/docs`.

### Authentication and current user

```text
POST /api/auth/login
GET  /api/users/me
PUT  /api/users/me/password
```

### Categories and organization

```text
GET    /api/categories
GET    /api/categories/{category_id}
PUT    /api/organizations/me
PUT    /api/organizations/me/logo
DELETE /api/organizations/me/logo
GET    /api/organizations/{organization_id}/logo
```

### Organization technicians

```text
GET  /api/organizations/me/team-members
POST /api/organizations/me/team-members
PUT  /api/organizations/me/team-members/{member_id}
```

### Passport templates and fields

```text
POST   /api/templates
GET    /api/templates
GET    /api/templates/families
GET    /api/templates/{template_id}
PUT    /api/templates/{template_id}
POST   /api/templates/{template_id}/versions
POST   /api/templates/{template_id}/fields
PUT    /api/templates/{template_id}/fields/{field_id}
DELETE /api/templates/{template_id}/fields/{field_id}
```

### Product models

```text
POST   /api/product-models
GET    /api/product-models
GET    /api/product-models/page
GET    /api/product-models/{model_id}
PUT    /api/product-models/{model_id}
PUT    /api/product-models/{model_id}/image
DELETE /api/product-models/{model_id}/image
GET    /api/product-models/{model_id}/image
POST   /api/product-models/{model_id}/ai-extraction
```

The AI endpoint accepts one PDF, JPEG, PNG, WebP, HEIC, or HEIF source of at
most 10 MB and returns locally validated suggestions.

### Product items and lifecycle events

```text
POST /api/product-items
GET  /api/product-items
GET  /api/product-items/{item_id}
PUT  /api/product-items/{item_id}
GET  /api/product-items/{item_id}/qr-code
POST /api/product-items/{item_id}/lifecycle-events
GET  /api/product-items/{item_id}/lifecycle-events
```

### Public passport and support

```text
GET  /api/passports/{public_id}
POST /api/passports/{public_id}/support-tickets
POST /api/support-tickets/{ticket_id}/track
POST /api/support-tickets/{ticket_id}/comments
```

Support-ticket creation is enabled only when Azure DevOps routing, server-side
PAT, and SMTP settings are configured.

## External services

- **Azure DevOps** stores and processes customer support work items,
  attachments, states, and comments.
- **SMTP** sends the private ticket tracking code and DPP tracking link.
- **Cloudinary** stores organization logos and product-model images.
- **Gemini** proposes structured passport values from uploaded documents.

Failures from external services are converted into controlled API errors. The
prototype uses request timeouts and idempotent ticket retries, but does not have
a background queue, distributed retries, webhooks, or a local ticket-status
cache.

## Verification status

The tracked backend suite currently has 121 pytest tests covering unit-level rules and
API-level workflows with an isolated in-memory SQLite database. External
services are replaced with test doubles. Frontend lint and production build
checks are implemented; automated frontend component and end-to-end tests are
not.

## Explicitly outside the current MVP

- platform-administrator and category-management UI/API;
- a universal CRM, ERP, or PLM connector;
- a persisted registry of QR/NFC carriers;
- customer accounts and a customer ticket list;
- antivirus scanning and document sandboxing;
- distributed rate limiting, background jobs, and automatic retry workers;
- production monitoring, formal accessibility certification, load testing, and
  penetration testing.
