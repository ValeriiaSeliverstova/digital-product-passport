# Digital Product Passport frontend

React 19 frontend built with JavaScript, Vite, semantic HTML, CSS Modules, and
shared CSS design tokens.

## Implemented screens

Organization administrators can:

- sign in and change their password;
- manage versioned passport templates and fields;
- search and manage product models and their images;
- register, publish, search, and retire physical product items;
- use AI-assisted extraction from a PDF or supported image while creating an
  item;
- add public or manufacturer-only lifecycle events;
- edit organization contact/support settings and its logo;
- create, activate, and deactivate service-technician accounts;
- generate, download, and print an SVG QR code and write the public URL to a
  supported NFC tag.

Service technicians use a reduced navigation and can register or publish
product items and add lifecycle events. They cannot manage templates, models,
organization settings, team members, or retire products.

Public visitors can:

- open `/passport/{public_id}` without authentication;
- view a published product's public fields and lifecycle events;
- submit an Azure DevOps support request with an optional image attachment;
- open `/support-ticket` or `/support-ticket/{ticket_id}`, enter the emailed
  tracking code, view the current status and customer-visible comments, and
  reply to support.

Draft, retired, and unknown product passports are not exposed publicly.

## Local development

Install dependencies and start Vite:

```bash
npm install
npm run dev
```

The application is available at `http://localhost:5173` by default.

## Environment configuration

Copy `.env.example` to `.env` only when a local override is needed:

```bash
cp .env.example .env
```

`VITE_API_URL` is the public FastAPI base URL. Every `VITE_` value is included
in browser code, so it must never contain a password, PAT, JWT signing key, or
other secret.

The short-lived access token is kept only in React memory and is cleared on
logout or a rejected session. Refreshing the page therefore requires signing
in again by design.

## NFC support

The NFC writer uses the browser Web NFC API. It requires a compatible browser
and device and, outside localhost, an HTTPS page. Unsupported devices can still
use the downloadable QR code or direct passport URL.

## Checks

```bash
npm run lint
npm run build
```

There is currently no automated frontend unit or end-to-end test suite.
