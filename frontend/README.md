# Digital Product Passport frontend

React frontend built with JavaScript and Vite.

## Local development

Install dependencies and start the development server:

```bash
npm install
npm run dev
```

The application is available at `http://localhost:5173` by default.

After signing in, a manufacturer can manage templates, product models, and
physical product items. Product Item forms are generated from the exact
template selected by their Product Model.

Published Product Items provide controls to generate, download, and print a
scalable QR code. A new copy can be generated whenever another label is needed.

A published passport can be opened without signing in:

```text
http://localhost:5173/passport/{public_id}
```

The `public_id` is returned by the Product Item API. Draft and Retired items do
not appear on the public page.

## Environment configuration

Copy `.env.example` to `.env` when a local override is needed. Variables with
the `VITE_` prefix are included in browser code, so they must never contain
passwords, JWT signing keys, or other secrets.

`VITE_API_URL` specifies the public URL of the FastAPI backend.

## Checks

```bash
npm run lint
npm run build
```
