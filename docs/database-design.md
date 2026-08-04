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
