# Project Shutdown Checklist

Use this checklist when the Digital Product Passport project is finished and
its hosted services are no longer needed.

## Services currently used

### Render

Render hosts the deployed application infrastructure:

- React/Vite frontend static site;
- FastAPI backend web service;
- PostgreSQL database.

### Cloudinary

Cloudinary stores uploaded images such as organization logos, product-model
images, and user avatars. It is required only after Cloudinary integration is
enabled.

### GitHub

GitHub stores the source code and may trigger Render deployments. It does not
need to be deleted when the hosted application is shut down. The repository can
instead be archived and kept as the capstone record.

## Recommended shutdown order

### 1. Save anything that must be retained

- Export the production PostgreSQL database if the project data is needed.
- Download original images from Cloudinary if they must be preserved.
- Save important Render configuration separately, without publishing secrets.
- Confirm that the final source code and documentation are committed.

Do not place database passwords, API secrets, JWT secrets, or production data
in the Git repository.

### 2. Stop application traffic on Render

- Disable automatic deployments.
- Suspend or delete the frontend static site.
- Suspend or delete the FastAPI web service.
- Confirm that the public frontend, API, and Swagger URLs are no longer active.

### 3. Remove Cloudinary resources

- Delete uploaded images and generated image variants.
- Remove upload presets and API keys that were created for this project.
- Confirm in the Cloudinary usage dashboard that no assets remain.
- Close the Cloudinary account only if it is not used by another project.

### 4. Remove the Render database

- Confirm that the final database export can be restored, if a backup is
  required.
- Delete the Render PostgreSQL instance.
- Delete any remaining Render environment groups or project resources.
- Check the Render billing page for active resources.

The database is removed last because the backend may need it while final data
or image references are being checked.

### 5. Revoke secrets

- Revoke or rotate the Cloudinary API secret.
- Remove Cloudinary variables from Render.
- Remove the production database URL from Render.
- Remove or rotate `JWT_SECRET_KEY`.
- Remove any local production secrets that are no longer required.

### 6. Preserve or remove the source repository

Choose one option:

- Archive the GitHub repository to preserve the capstone project; or
- Delete it only if the project files must no longer be retained.

Review GitHub deployment settings and remove any Render integration or deploy
hooks that remain connected to the repository.

## Final verification

- [ ] Frontend URL is unavailable.
- [ ] Backend health and Swagger URLs are unavailable.
- [ ] Render web and static services are deleted or suspended.
- [ ] Render PostgreSQL is deleted.
- [ ] Cloudinary assets are deleted or intentionally retained.
- [ ] Cloudinary project credentials are revoked.
- [ ] No paid or active resources remain in Render or Cloudinary.
- [ ] Required database and image backups were tested or documented.
- [ ] GitHub repository is archived, retained, or deleted intentionally.

## Local development cleanup

Local Docker containers and volumes are not cloud services. They can be stopped
without affecting Render or Cloudinary:

```bash
docker compose down
```

Removing Docker volumes also deletes the local PostgreSQL data, so do that only
when a local backup is no longer needed.
