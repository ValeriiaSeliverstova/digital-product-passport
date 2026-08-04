# Digital Product Passport Platform

A configurable Digital Product Passport system for industrial products.

The platform allows manufacturers to create product passports with customizable fields, documents, components, lifecycle events, and access levels. Each product can be accessed through a QR code, NFC tag, direct link, or serial number.

Safe equipment is used as the primary case study.

## Planned Stack

- Frontend: React + JavaScript
- Backend: FastAPI + Python
- Database: PostgreSQL
- ORM: SQLAlchemy
- Infrastructure: Docker

## Planned Features

- configurable passport templates;
- versioned template families with immutable Active field definitions;
- product models, batches, and individual items;
- QR code and NFC-based access;
- document and certificate management;
- lifecycle and maintenance history;
- role-based access control;
- audit logging.

## Project Status

The MVP backend includes authentication, product categories, configurable and
versioned passport templates, and template-field management. The React frontend
currently supports login and the manufacturer template workflow.

## Security

Only fictional or anonymized data will be used. No confidential company, customer, or security-related information will be stored in this repository.
