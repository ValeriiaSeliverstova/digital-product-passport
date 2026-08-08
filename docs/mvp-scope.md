# MVP Scope

## Goal

The first version of the system will demonstrate the core Digital Product Passport workflow:

1. Select a predefined product category.
2. Create a configurable passport template for that category.
3. Add template fields.
4. Register a product model.
5. Register an individual product item.
6. Store configurable passport data.
7. Retrieve and display the product passport.

## Initial User Roles

The MVP will include two main roles:

### System Administrator

The system administrator can:

- manage predefined product categories;
- activate or deactivate categories;
- manage system users;
- view all organizations and products.

### Manufacturer User

A manufacturer user can:

- select an existing product category;
- create passport templates;
- define template fields;
- create product models;
- register individual product items;
- manage passport data.

## Product Categories

Product categories are predefined by the system and managed only by the system administrator.

Manufacturers cannot create arbitrary categories. When creating a passport template or product model, they select a category from the available list.

Example category hierarchy:

```text
Industrial Products
├── Security Equipment
│   ├── Safes
│   ├── Vault Doors
│   └── Deposit Boxes
├── Machinery
├── Electronic Equipment
└── Furniture
```

For the initial case study, the system will include the predefined category:

```text
Industrial Products
└── Security Equipment
    └── Safes
```

## Initial Entities

The MVP will include the following entities:

- Organization
- User
- Role
- ProductCategory
- PassportTemplate
- TemplateField
- ProductModel
- ProductItem
- LifecycleEvent
- DataCarrier

## Initial Entity Responsibilities

### Organization

Represents a manufacturer or another company registered in the system.

### User

Represents an authenticated system user with exactly one role.

Manufacturer users must belong to an organization. A platform-level system administrator may have no organization.

### Role

Defines the user's permissions. The initial roles are `system_admin` and `manufacturer_user`.

### ProductCategory

Represents a predefined system-managed category of industrial products.

Categories may support a hierarchical structure through a parent category.

### PassportTemplate

Defines the configurable structure of a Digital Product Passport for a selected product category.

A manufacturer may create multiple templates for the same category.

Each template may have multiple versions. Every version has a unique `id`, and
all versions in the same family share a stable `template_family_id`. The family
name is editable metadata and is kept consistent across its versions.

New templates start as Draft. Activating a version locks its fields. A new
version copies the latest completed version and its fields into the next Draft
version; only one Draft is allowed per family.

Example:

```text
Category: Safes

Templates:
- Mechanical Safe Passport
- Electronic Safe Passport
- High-Security Safe Passport
```

### TemplateField

Defines an individual configurable field within a passport template.

A template field may include:

- field name;
- field code;
- data type;
- required or optional status;
- validation rules;
- display order;
- access level.

### ProductModel

Represents a product design or commercial model.

Example:

```text
Model: SecureSafe 500
Description: Compact safe designed for homes and small offices
Category: Safes
Template: Electronic Safe Passport
```

The optional description contains general information shared by every physical
item of the product model.

A product model uses one exact Active template version. Its `model_code` is
unique within the manufacturer organization, and its status is either `active`
or `archived`.

### ProductItem

Represents a specific physical product with its own serial number and Digital Product Passport.

Items begin as Draft so incomplete data can be saved. Publishing requires all
required template fields. Published items cannot change their identity or
passport values; they may only move to Retired.

### LifecycleEvent

Represents an event in the lifecycle of a product item, such as manufacturing, installation, maintenance, or repair.

### DataCarrier

Represents a QR code, NFC tag, or another carrier connected to a product item.

## Initial Relationships

- An organization can have multiple users.
- Each user has exactly one role.
- A role can be assigned to multiple users.
- A manufacturer user belongs to one organization.
- A system administrator may have no organization.
- A product category can contain child categories.
- A product category can have multiple passport templates.
- A passport template belongs to one organization.
- Each passport template row is one version and belongs to one template family.
- A template family can contain multiple ordered versions.
- A passport template contains multiple template fields.
- A product model belongs to one product category.
- A product model uses one passport template.
- A product model can have multiple product items.
- A product item can have multiple lifecycle events.
- A product item can have multiple data carriers.

## First Implementation Flow

```text
System Administrator
        ↓
Manage Predefined Product Categories

Manufacturer
        ↓
Select Product Category
        ↓
Create Passport Template
        ↓
Add Template Fields
        ↓
Create Product Model
        ↓
Create Product Item
        ↓
Store Passport Data
        ↓
Retrieve Product Passport
```

## MVP Business Rules

1. Only system administrators can create, update, deactivate, or reorder product categories.

2. Manufacturers must select an existing active category.

3. Each passport template belongs to one organization and one product category.

4. A manufacturer may create multiple passport templates for the same category.

4a. Versions of one template share a stable `template_family_id`; only Draft
versions may change fields.

5. A product model must use a template assigned to the same category.

6. Each product item must belong to one product model.

7. Each product item must have a unique serial number within its manufacturer.

8. Each product item receives a unique public identifier.

9. QR codes and NFC tags contain only a URL

10. Product-specific passport data must comply with the selected template.

## Planned Backend Setup

- Python
- FastAPI
- SQLAlchemy
- Alembic
- PostgreSQL
- Pydantic
- Environment-based configuration

## Planned First API Endpoints

### Authentication and users

```text
POST /api/auth/login
GET  /api/users/me
```

### Product categories

```text
GET  /api/categories
GET  /api/categories/{id}
```

Category creation and modification endpoints will be restricted to system administrators:

```text
POST   /api/admin/categories
PUT    /api/admin/categories/{id}
DELETE /api/admin/categories/{id}
```

Deletion may be implemented as deactivation rather than permanent removal.

### Passport templates

```text
POST /api/templates
GET  /api/templates
GET  /api/templates/{id}
PUT  /api/templates/{id}
POST /api/templates/{id}/versions
```

The version endpoint copies the latest Active or Archived version and its
fields into the next Draft version. It rejects older source versions and
families that already contain a Draft.

### Template fields

```text
POST   /api/templates/{id}/fields
PUT    /api/templates/{template_id}/fields/{field_id}
DELETE /api/templates/{template_id}/fields/{field_id}
```

### Product models

```text
POST /api/product-models
GET  /api/product-models
GET  /api/product-models/{id}
PUT  /api/product-models/{id}
```

Only the name, optional description, and status can be updated. Organization,
category, template version, and model code remain fixed after creation.

### Product items

```text
POST /api/product-items
GET  /api/product-items
GET  /api/product-items/{id}
PUT  /api/product-items/{id}
GET  /api/product-items/{id}/qr-code
GET  /api/passports/{public_id}
```

The manufacturer endpoints require authentication and return only items owned
by the user's organization. The public passport endpoint requires no login and
returns only Published products and fields marked for public access. Draft,
Retired, and unknown passports return the same Not Found response.

The protected QR endpoint generates a fresh printable SVG for an owned
Published item whenever requested. The image is not stored in the database and
contains only the frontend public-passport URL.

## Initial Seed Data

The database should contain initial system-managed seed data.

Example:

```text
Industrial Products
└── Security Equipment
    ├── Safes
    ├── Vault Doors
    └── Deposit Boxes
```

Additional seed data may include:

- one system administrator;
- one manufacturer organization;
- one manufacturer user;
- one safe passport template;
- several template fields;
- one safe product model;
- one product item.

## MVP Success Criteria

The MVP is considered successful when:

1. A system administrator can manage predefined categories.
2. A manufacturer can select an active category.
3. A manufacturer can create a configurable passport template.
4. Template fields can be added without changing the database schema.
5. A product model can be linked to the selected category and template.
6. A physical product item can be registered with a serial number.
7. Product-specific passport data can be stored and validated.
8. A passport can be retrieved through its public identifier.
9. The same core system can support another product category by creating a different template.
