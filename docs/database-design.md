# Database Design

## Entity-Relationship Diagram

![ER Diagram](diagrams/mvp-schema.svg)

The editable schema source is [mvp-schema.dbml](diagrams/mvp-schema.dbml).

## Main Entities

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

## Notes

The database uses a hybrid model:

- relational tables for stable entities and relationships;
- JSONB for configurable passport data;
- external storage for documents and images.

Each user has one role through `users.role_id`. Manufacturer users belong to an organization, while a platform-level system administrator may have no organization.

Each `passport_templates` row represents one exact template version. Its `id`
identifies that version, while `template_family_id` is shared by every version
in the same family. This stable family identifier keeps version history grouped
even when the displayed template family name changes.

Template fields belong to an exact version and are copied into each new Draft
version. Active and Archived versions therefore keep the field definitions that
were valid when they were used.

Each product model references one exact Active passport template version. This
keeps its future product items connected to a stable passport structure even
after another version of the template is created.

Each product item also stores its organization directly. This makes ownership
checks straightforward and allows the database to enforce that serial numbers
are unique within one manufacturer. Configurable passport values are stored in
JSONB and validated against the exact template used by the product model.

The public passport API looks up a product item using its random `public_id`.
It exposes only Published items and filters their JSONB values using the access
level of each field in the exact template version.
