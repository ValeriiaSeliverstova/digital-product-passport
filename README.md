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
- printable QR-code access and planned NFC support;
- document and certificate management;
- lifecycle and maintenance history;
- role-based access control;
- audit logging.

## Project Status

The MVP backend includes authentication, product categories, configurable and
versioned passport templates, product models, physical product items, and a
public passport API. The React frontend supports the manufacturer workflows for
templates, product models, and product items, together with the public passport
page and repeatable SVG QR-code generation for printed labels.

## Security

Only fictional or anonymized data will be used. No confidential company, customer, or security-related information will be stored in this repository.
