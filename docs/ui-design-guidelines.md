# UI Design and Development Rules

## 1. Purpose and scope

This document is the shared UI standard for the Digital Product Passport (DPP)
application. Designers use it when preparing screens and components. Developers
use it when implementing and reviewing the React frontend.

It applies to:

- organization-administrator pages;
- service-technician pages with a reduced permission set;
- future system-administrator pages;
- the public Digital Product Passport;
- public support-ticket submission and tracking;
- mobile, tablet, and desktop layouts.

The following words define the strength of a rule:

- **MUST**: mandatory for a design or implementation to be accepted.
- **SHOULD**: the expected choice; deviations require a clear reason.
- **MAY**: optional when it improves the experience without adding complexity.

The MVP uses React, JavaScript, semantic HTML, and plain CSS. A large UI
framework is outside the current scope.

## 2. Product experience principles

Every screen MUST support these principles:

1. **Trust before decoration.** Product identity, ownership, version, status,
   and important actions take priority over illustrations or effects.
2. **Predictable actions.** Labels describe the result: “Create draft”,
   “Activate template”, and “Archive template”. Avoid vague labels such as
   “Continue” when a more precise label is possible.
3. **Visible traceability.** Template version, lifecycle status, organization,
   and relevant dates remain easy to locate.
4. **Safe handling of data.** Public and manufacturer-only data are visually
   distinct. Destructive and irreversible actions explain their consequences.
5. **Mobile-first access.** The complete workflow works on a narrow screen;
   larger screens improve arrangement but do not add essential functionality.
6. **Accessible by default.** Keyboard, touch, screen-reader, zoom, and reduced-
   motion users receive the same information and actions.

The interface SHOULD feel professional, calm, and suitable for manufacturing
and product safety. It SHOULD NOT use decorative “hacker”, lock, machinery, or
industrial imagery as a substitute for meaningful product information.

## 3. Design tokens

Designers MUST use the named tokens in design files. Developers MUST implement
the same names as CSS custom properties. Components MUST NOT introduce new
colours, spacing values, radii, or shadows when an existing token is suitable.

### 3.1 Colour

The MVP uses one tested light theme. Dark mode MAY be added later only when the
full palette and every component state have been reviewed for contrast.

| Token | Value | Required use |
| --- | --- | --- |
| `--color-primary` | `#0F4C5C` | Primary actions, selected navigation, important links |
| `--color-primary-hover` | `#0B3945` | Hover and pressed state for primary actions |
| `--color-secondary` | `#2F6F73` | Supporting emphasis; not a second primary action |
| `--color-page` | `#F5F7F8` | Page background |
| `--color-surface` | `#FFFFFF` | Cards, forms, dialogs, and application header |
| `--color-text` | `#17232A` | Headings and primary body text |
| `--color-text-muted` | `#52616B` | Secondary descriptions and metadata |
| `--color-border` | `#CBD5DB` | Decorative dividers and card boundaries |
| `--color-control-border` | `#64748B` | Input and interactive-control boundaries |
| `--color-success` | `#166534` | Success text and Active status |
| `--color-success-bg` | `#DCFCE7` | Success and Active background |
| `--color-warning` | `#92400E` | Warning text and Draft status |
| `--color-warning-bg` | `#FEF3C7` | Warning and Draft background |
| `--color-error` | `#B42318` | Errors and destructive actions |
| `--color-error-bg` | `#FEE2E2` | Error background |
| `--color-info` | `#1D4ED8` | Informational messages and links |
| `--color-info-bg` | `#DBEAFE` | Informational background |
| `--color-archived` | `#475569` | Archived status and neutral emphasis |
| `--color-archived-bg` | `#E2E8F0` | Archived status background |
| `--color-focus` | `#2563EB` | Keyboard focus indicator |

Colour rules:

- White text MAY be used on `primary`, `primary-hover`, or `secondary`.
- Status foreground and background tokens MUST be used as pairs.
- Colour MUST NOT be the only indication of status, error, selection, or access.
- Normal text MUST meet a 4.5:1 contrast ratio. Large text MUST meet 3:1.
- Meaningful control boundaries and icons MUST meet 3:1 against adjacent colours.
- Disabled content MUST remain readable, even though it is visually subdued.

### 3.2 Typography

Use the following system stack; no font download is required:

```css
font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont,
  "Segoe UI", sans-serif;
```

| Style | Mobile | From 900 px | Weight | Line height |
| --- | --- | --- | --- | --- |
| Page title / `h1` | `1.75rem` | `2.25rem` | 700 | 1.2 |
| Section title / `h2` | `1.375rem` | `1.75rem` | 650 | 1.25 |
| Component title / `h3` | `1.125rem` | `1.25rem` | 650 | 1.3 |
| Body | `1rem` | `1rem` | 400 | 1.5 |
| Label | `0.875rem` | `0.875rem` | 600 | 1.4 |
| Helper or error | `0.875rem` | `0.875rem` | 400 | 1.4 |
| Button | `1rem` | `1rem` | 600 | 1 |
| Table | `0.875rem` | `0.875rem` | 400 | 1.4 |

Text MUST use sentence case. Uppercase MAY be used for established short codes,
not for headings or buttons. UUIDs, serial numbers, and field codes MAY use a
monospace font when it improves scanning.

### 3.3 Spacing, radius, and elevation

```css
--space-1: 0.25rem; /* 4 px */
--space-2: 0.5rem;  /* 8 px */
--space-3: 0.75rem; /* 12 px */
--space-4: 1rem;    /* 16 px */
--space-6: 1.5rem;  /* 24 px */
--space-8: 2rem;    /* 32 px */
--space-12: 3rem;   /* 48 px */

--radius-control: 0.5rem;
--radius-dialog: 0.75rem;
--shadow-floating: 0 8px 24px rgb(23 35 42 / 12%);
```

- Related label, control, and helper text MUST be separated by `space-1` or
  `space-2`.
- Fields in the same form MUST normally be separated by `space-4`.
- Separate sections MUST use `space-6` or `space-8`.
- Cards use `space-4` padding on mobile and `space-6` from 600 px.
- Shadows are reserved for dialogs and floating navigation. Normal cards use a
  border against the page background.

## 4. Responsive layout rules

### 4.1 Breakpoints

All base styles MUST describe the mobile layout. Only `min-width` queries may
enhance the layout:

```css
/* Default: mobile */
@media (min-width: 600px) { /* large phone / tablet */ }
@media (min-width: 900px) { /* wide tablet / desktop */ }
@media (min-width: 1200px) { /* optional large desktop refinement */ }
```

Breakpoints MUST respond to content needs, not specific device brands.

### 4.2 Page frame

- Page padding MUST be `1rem` by default, `1.5rem` from 600 px, and `2rem` from
  900 px.
- Main application content MUST be centred and limited to `75rem` (1200 px).
- Forms and long text SHOULD be limited to `42rem` (672 px).
- Normal pages MUST use one column on mobile.
- A two-column layout MAY start at 900 px when both columns remain readable.
- Horizontal page scrolling is not allowed. A genuine data table MAY scroll
  inside a labelled container.

### 4.3 Mobile interaction

- Interactive targets SHOULD be at least 44 by 44 px.
- Forms and primary actions MUST use the full available width on narrow screens.
- Essential information and actions MUST NOT depend on hover.
- Dialog content MUST fit within the viewport and provide internal scrolling.
- Sticky actions MUST NOT cover content or keyboard focus.
- At 200% browser zoom, the workflow MUST remain operable without lost content.

## 5. Application shell

### 5.1 Authenticated organization application

The authenticated header contains:

- application name or mark;
- organization identity when available;
- role-appropriate navigation;
- access to account information and Logout.

Navigation is a horizontally scrollable labelled row on narrow screens and
uses the additional available width at larger breakpoints. Organization
administrators receive Profile, Templates, Product models, Product items, and
Team members. Service technicians receive Product items and Account only. The
selected destination uses colour and a second indicator such as weight, border,
or background. Permission-restricted destinations MUST be omitted rather than
shown as disabled.

The user's email and organization belong in the account area. Logout MUST have
a visible text label. A “Skip to main content” link MUST be the first keyboard-
focusable item.

### 5.2 Public passport

The public passport MUST use a separate, simplified shell. It MUST NOT display
manufacturer navigation or account controls. Product identity and authenticity
must appear before detailed attributes.

The public support tracker uses the same simplified DPP shell. It MUST keep the
customer inside the DPP application and MUST NOT expose an Azure DevOps link or
internal work-item URL.

## 6. Component standards

Every designed component MUST include default, hover where applicable, focus,
disabled, loading, and error states. Developers MUST implement only documented
variants; new variants must first be added to this standard.

### 6.1 Buttons

| Variant | Use |
| --- | --- |
| Primary | One main action in a page or form section |
| Secondary | Alternative non-destructive action |
| Tertiary/text | Low-emphasis action such as Cancel |
| Destructive | Delete or another destructive action |

Rules:

- Buttons MUST be at least 44 px high.
- Labels MUST describe the result of the action.
- Icon-only buttons require an accessible name and SHOULD be avoided for primary
  or destructive actions.
- A page section MUST NOT present multiple primary buttons of equal emphasis.
- Loading MUST prevent duplicate submission and preserve the button width.
- Disabled state MUST NOT be the only explanation of why an action is blocked.
- Keyboard focus MUST use a visible 2 px `focus-visible` outline with 2 px offset.

### 6.2 Form controls

- Every input, select, and textarea MUST have a persistent visible label.
- Placeholder text MUST NOT replace a label.
- Inputs and selects MUST be at least 44 px high and full width on mobile.
- Optional fields MUST be identified with the word “Optional”.
- Help text MUST describe format or consequence, not repeat the label.
- An error MUST provide an error border, an icon where useful, and explanatory
  text linked with `aria-describedby`.
- The user's input MUST remain after client or API validation failure.
- Error text MUST say how to correct the value when possible.

Checkbox labels MUST be part of the same touch target. Use a checkbox for a
saved form value such as “Required”. Use a switch only when changing it has an
immediate effect without a separate Save action.

### 6.3 Cards

- One card represents one concept: template, product, field, or grouped section.
- A whole card MAY be interactive only when it has one clear destination.
- Nested cards SHOULD be avoided; headings and dividers provide hierarchy.
- Mobile list cards MUST include visible labels for values that would otherwise
  be table-column headings.

### 6.4 Tables and data lists

- Templates and products MUST appear as labelled cards on mobile.
- A semantic table MAY replace the cards from 900 px when comparing rows is
  important.
- Table headers MUST describe every data column.
- Row actions MUST remain keyboard accessible and visible without hover.
- Do not reduce body text below the typography tokens to force a table to fit.

### 6.5 Status and access badges

| Meaning | Text | Colours |
| --- | --- | --- |
| Draft template | `Draft` | warning / warning background |
| Active template | `Active` | success / success background |
| Archived template | `Archived` | archived / archived background |
| Public field | `Public` | info / info background |
| Restricted field | `Manufacturer only` | archived / archived background |

Badges are descriptive and MUST NOT behave like buttons. The complete text is
required even when an icon is present.

### 6.6 Alerts and messages

- Alerts MUST contain a clear title or leading statement and a useful next step.
- Error messages requiring immediate attention use `role="alert"`.
- Non-interrupting success messages use `aria-live="polite"`.
- Colour MUST be supported by text and an icon where appropriate.
- Messages MUST NOT expose database errors, JWT details, or stack traces.

### 6.7 Confirmation dialogs

Confirmation is required for:

- deleting a template field;
- activating a template;
- archiving a template;
- any future destructive operation that cannot be reversed.

The dialog MUST name the affected object and explain the consequence. Focus
must move into the dialog, remain within it, and return to the opening control
after close. Escape closes the dialog as Cancel. The safe action receives
initial focus for destructive confirmations.

On mobile, dialogs use `calc(100% - 2rem)` width, a limited viewport height, a
scrollable body, and stacked full-width actions.

### 6.8 Loading and empty states

- A loading region MUST provide visible text or an accessible label.
- Use `aria-busy="true"` on a region that is being updated.
- Loading one component MUST NOT block the whole page unnecessarily.
- Empty states MUST explain the absence of data.
- When the user can resolve the empty state, include exactly one clear action,
  such as “Create your first template”.

## 7. Domain interaction rules

### 7.1 Template lifecycle

The UI MUST represent the backend's one-way lifecycle accurately:

```text
Draft -> Active -> Archived
```

- A new template is always Draft.
- Only Draft template fields are editable. The template family name is
  editable metadata and changes consistently across all versions.
- Activation is unavailable until at least one field exists.
- Activation confirmation MUST show template name, version, field count, and
  “Fields cannot be changed after activation.”
- Active templates MAY only be archived; they cannot return to Draft.
- Archived template structures are visible for traceability and are read-only;
  their shared family name may still be corrected.
- Edit controls MUST be removed from Active and Archived field views. A short
  explanation replaces them; disabled controls alone are insufficient.
- The Template list MUST show one card per `template_family_id`, with the latest
  version and the total version count.
- Template details MUST show the complete version history.
- “Create new version” is available only from the latest Active or Archived
  version when no Draft exists. It copies fields into the next Draft.
- When a Draft already exists, the UI provides “Open draft version” instead of
  creating another Draft.

### 7.2 Template field editor

One field editor contains these controls in this order:

1. Label.
2. Code.
3. Data type.
4. Required checkbox.
5. Access level.
6. Display order.
7. Type-specific validation rules.

Field codes MUST follow `lowercase_with_underscores` and remain within 100
characters. Labels remain within 255 characters.

| Data type | Rules shown by the UI |
| --- | --- |
| Text | Minimum length, maximum length, allowed values |
| Integer | Minimum integer, maximum integer |
| Decimal | Minimum number, maximum number |
| Boolean | No additional rules |
| Date | Earliest date, latest date |

- The UI MUST NOT ask users to write JSON validation rules.
- Allowed values use repeatable text inputs.
- Changing data type requires confirmation before incompatible entered rules
  are removed.
- Mobile shows each field as one vertically stacked card.
- From 900 px, related controls MAY share rows, but reading and keyboard order
  MUST remain unchanged.
- Reordering MUST work without drag-and-drop. Display-order input or labelled
  Move up/Move down actions are required.
- The Save label MUST include the field count, for example “Save 4 fields”.
- The batch is atomic. If any field fails, the UI MUST keep all entered fields,
  show an error summary, and show the error beside the relevant control.

### 7.3 Public and manufacturer-only data

- Every field editor and field summary MUST show its access badge.
- The public passport MUST never render a `manufacturer` field.
- Restricted content MUST NOT be briefly rendered while authorization is loading.
- Hiding restricted content is not authorization; the backend remains the
  source of truth.

## 8. Screen standards

These standards define required content and responsive behaviour. They are not
fixed wireframes; designers MAY choose the exact composition within the shared
tokens and component rules.

| Screen | Required content | Mobile rule | From 900 px |
| --- | --- | --- | --- |
| Login | Product name, email, password, Show/Hide password, Sign in, generic error area | One column, form max width 26rem, full-width submit | Remains a focused form; extra decoration must not dominate |
| Template list | Title, Create action, status/search controls when implemented, family name, category, latest version, version count, latest status, created date, empty state | Template families are cards | A semantic table may be used |
| Create template | Name, active category selection, version, Cancel, Create draft | One readable column | Form remains max 42rem; do not stretch controls |
| Template details | Back navigation, editable family name, category, selected version, version history, status, lifecycle actions, ordered fields | Metadata and actions before stacked field cards | Actions may align horizontally; fields may use denser rows |
| Bulk field editor | Field count, repeated field editors, Add field, Cancel, Save count, error summary | One field card per row; actions stack | Related controls may form a grid |
| Product-model list/form | Search and status filters, pagination, model identity, category, exact template version, description, status, optional image | Cards and stacked form controls | List and form may use wider grids |
| Product-item list/form | Search, status/date filters, pagination, serial number, model, manufacture date, template-driven values, lifecycle events, QR/NFC actions | Stacked item cards and one-column form | Related metadata and actions may share rows |
| Organization profile | Contact fields, logo, Azure Area Path and work-item type; password form | Sections and actions stack | Sections remain readable and bounded |
| Team members | Technician creation form, initial-password guidance, member status and activation action | One member card per row | Form and list may use wider layout |
| Public passport | Manufacturer identity, model, serial number, manufacture date, public attributes, public lifecycle events, support contacts, new-ticket form and generic tracking action | Optimized for QR entry and one-column reading | Content remains centred; sections may use two columns only when meaningful |
| Public support tracker | Ticket number when not present in URL, private tracking code, current state, dates, customer-visible conversation, reply form | One-column card with full-width controls | Card remains narrow enough for readable conversation text |

Additional screen rules:

- Login MUST use `type="email"`, appropriate autocomplete values, and a password
  control hidden by default. It MUST NOT show OAuth client ID, client secret,
  scopes, or the JWT.
- Create template MUST load categories from the API; free category text is not
  allowed. Successful creation opens the Draft template detail view.
- Public passport labels MUST be human-readable. Raw JSON keys and raw URLs are
  not acceptable presentation; links use labels such as “View certification”.
- AI-extracted values MUST be presented as suggestions with confidence and
  source information. The user reviews them before applying them to the form.
- Support comments are public only when the backend accepts their `@customer`
  marker. The public UI MUST NOT render Azure user identity or untagged internal
  discussion.
- The public passport MUST NOT reveal existing ticket numbers, counts, dates,
  statuses, subjects, or messages. Tracking requires a ticket number and its
  private code. A Closed ticket keeps its verified history visible but MUST NOT
  render a reply form.

## 9. Content and language rules

- Use short, concrete labels in sentence case.
- Use the same word for the same entity everywhere: Template, Field, Product
  model, Product item, Organization.
- Buttons begin with a verb: Create, Save, Add, Remove, Activate, Archive.
- Confirmation titles name the action: “Activate template?”
- Destructive descriptions state what cannot be undone.
- Avoid technical backend language such as “422”, “constraint”, “payload”, or
  “JSONB” in user-facing messages.
- Dates MUST use one consistent, locale-aware format. Machine codes and ISO dates
  MAY be shown in technical detail sections.
- Empty-state and error copy MUST help the user take the next valid action.

## 10. Security and privacy rules

- JWTs, signing secrets, password hashes, and raw authentication responses MUST
  never be displayed or written to browser logs.
- The MVP access token MUST remain in React memory. It MUST NOT appear in a URL.
- Password characters are hidden by default. Show/Hide does not alter the value.
- Login uses one generic failure message: “Email or password is incorrect.”
- An expired or rejected session clears authentication state and returns the user
  to Login with a neutral message.
- The UI MUST NOT request an organization ID when ownership is derived from the
  authenticated user.
- User-provided text MUST be rendered as text. `dangerouslySetInnerHTML` is not
  permitted for product or template data.
- Public pages MUST NOT expose biometric templates, access codes, pairing tokens,
  customer locations, private activity logs, internal attack details, or reset
  procedures.
- Azure PATs, SMTP passwords, Gemini keys, and Cloudinary secrets MUST remain
  server-side and MUST NOT be represented by `VITE_` variables.
- The support tracking code MUST be submitted only in the request body and MUST
  NOT appear in a URL, browser storage, or client log.
- Support attachments MUST be restricted to the formats and size accepted by
  the API. Client validation improves feedback but does not replace backend
  byte-signature validation.
- CORS is not authorization. JWT, role, ownership, and access-level enforcement
  remain backend responsibilities.

## 11. Accessibility rules

The MVP design targets WCAG 2.2 Level AA. This is a design target, not a claim
of formal accessibility certification.

- Pages MUST use semantic `header`, `nav`, `main`, and `footer` landmarks where
  applicable.
- Each page MUST have one `h1` and a logical heading hierarchy.
- Every function MUST work with keyboard alone in a predictable focus order.
- Focus MUST remain visible and not be hidden by sticky UI.
- Forms MUST use real labels and link instructions/errors with
  `aria-describedby`.
- Required, selected, restricted, warning, and error states MUST NOT rely on
  colour alone.
- Asynchronous errors and important success states MUST be announced.
- At 200% zoom, content MUST reflow without losing information or actions.
- Motion MUST respect `prefers-reduced-motion` and MUST NOT communicate required
  information by itself.
- Decorative images use empty alternative text. Meaningful images require a
  concise text alternative.
- Designers MUST annotate focus order, dialog behaviour, and non-obvious
  accessible names in handoff.
- Developers MUST test keyboard navigation, zoom, a narrow viewport, and at
  least one screen reader for every completed workflow.

References:

- [WCAG 2.2 contrast minimum](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html)
- [WCAG 2.2 non-text contrast](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html)
- [WCAG 2.2 focus visible](https://www.w3.org/WAI/WCAG22/Understanding/focus-visible)
- [WCAG 2.2 target size minimum](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html)

## 12. Frontend implementation structure

The frontend SHOULD use this small structure as features are added:

```text
frontend/src/
├── components/  # Component.jsx and Component.module.css pairs
├── pages/       # Page.jsx and Page.module.css pairs
├── services/    # API and authentication requests; no UI markup
├── styles/
│   ├── tokens.css
│   └── global.css
├── App.jsx      # Top-level authentication and page flow
├── App.module.css
└── main.jsx     # React entry point and global style import
```

- `tokens.css` MUST contain the shared colour, type, spacing, radius, and shadow
  values.
- `global.css` MUST contain body defaults, focus treatment, basic form defaults,
  and accessibility utilities. It MUST NOT contain page-specific layout.
- Page and component styles MUST use CSS Modules named after their owner, such
  as `LoginPage.module.css` or `Button.module.css`.
- CSS Modules MUST be imported as `styles` and applied through properties such
  as `className={styles.form}`. Global class-name strings are reserved for the
  small documented utilities in `global.css`.
- Reusable components MUST live in `components/`; one-off page composition stays
  in `pages/`.
- API base URL, authorization header, response parsing, and safe error conversion
  SHOULD be centralized in `services/api.js`.
- Redux, a large component library, or deep abstraction MUST NOT be added unless
  a demonstrated requirement justifies it.

## 13. Designer and developer handoff

### Designer responsibilities

For every new screen or changed workflow, the designer MUST provide:

- the mobile layout first;
- changes at 600 px and 900 px where needed;
- component names and documented variants;
- default, focus, error, disabled, loading, and empty states;
- exact content, not placeholder text;
- behaviour notes for dialogs, validation, and responsive transformations;
- annotations for access level and lifecycle restrictions.

Design files MUST use the tokens in this document. Any proposed new token or
component variant must be reviewed before handoff.

### Developer responsibilities

For every implemented screen or changed workflow, the developer MUST:

- reuse tokens and existing components;
- preserve the documented hierarchy and responsive behaviour;
- implement semantic elements and keyboard behaviour;
- handle loading, empty, success, validation, API-error, and unauthorized states;
- verify that public and manufacturer-only data are separated;
- avoid hard-coded colours or arbitrary spacing values;
- run frontend lint and production build checks.

If technical constraints require a design change, designer and developer SHOULD
update the rule or design together rather than silently diverging.

## 14. UI definition of done

A screen or component is complete only when all applicable statements are true:

- [ ] It uses documented tokens and component variants.
- [ ] It works at narrow mobile, 600 px, 900 px, and wide desktop sizes.
- [ ] No horizontal page scrolling occurs.
- [ ] Touch targets, contrast, and focus treatment meet this standard.
- [ ] Keyboard order is logical and every action is operable.
- [ ] Labels, validation, loading, empty, error, and success states are present.
- [ ] Draft, Active, Archived, Public, and Manufacturer-only meanings are correct.
- [ ] Sensitive data is not rendered, stored in URLs, or logged.
- [ ] User input remains available after a recoverable error.
- [ ] The design and implementation use the same content and behaviour.
- [ ] Frontend lint and production build checks pass.
