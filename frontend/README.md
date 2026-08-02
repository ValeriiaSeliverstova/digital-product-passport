# Digital Product Passport frontend

React frontend built with JavaScript and Vite.

## Local development

Install dependencies and start the development server:

```bash
npm install
npm run dev
```

The application is available at `http://localhost:5173` by default.

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
