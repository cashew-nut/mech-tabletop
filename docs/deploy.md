# Deploying the game

There is one web app, `apps/web`. The desktop game and the phone version are the same build: the phone layout, touch controls, quality tier and install support are all inside it (PR #86). Nothing else is deployed.

It is published to GitHub Pages by `.github/workflows/pages.yml` ("Publish web app"). Live copy: https://cashew-nut.github.io/mech-tabletop/ (public to anyone with the link).

## Does it need a custom workflow?

Yes, and it already has one, so nothing more is needed. Pages' built-in "deploy from a branch" mode only serves files that are already committed, and `apps/web/dist` is gitignored and built from an npm workspace with Vite. So the build has to run in Actions and upload the result, which is what `pages.yml` does: `npm ci`, `npm run build`, upload `apps/web/dist`, then `actions/deploy-pages`.

Other things that make it work from `https://<user>.github.io/mech-tabletop/` (a sub-path):

- `apps/web/vite.config.ts` sets `base: './'`, so every asset URL is relative.
- The manifest uses `start_url: './'` and `scope: './'`, and the service worker is registered relative, so installing to a phone home screen works from the sub-path.
- The build output includes about 145 MB of walker models from `apps/web/public/parts`, well under the 1 GB Pages limit.

## One-time setup

1. Repo **Settings > Pages > Build and deployment > Source: GitHub Actions**.
2. The workflow file must be on `main`. Manual runs use the workflow as it exists on the branch you pick.

The first run on 2026-11-08 failed at the `deploy-pages` step because step 1 had not been done yet. The build itself passed. After the setting was changed, the re-run succeeded and the site came up.

## Publishing a new copy

The workflow is manual only (`on: workflow_dispatch`), so merging to `main` does not change the live site.

1. Merge what you want live into `main`.
2. Go to **Actions > Publish web app > Run workflow**, branch `main`, then **Run workflow**. It takes about 45 seconds.
3. Open the Pages URL. The run's `deploy` job also prints the URL.

On a phone that already has the app installed, the service worker is network first, so the new copy loads the next time the app opens with signal. If it ever sticks on an old copy, bump `CACHE` in `apps/web/public/sw.js`.

Only `index.html` and `viewer.html` are built. The dev pages (`place.html`, `render*.html`) are not published.

## Check before publishing

```sh
npm run check   # validate data, typecheck, tests
npm run build   # same build the workflow runs; output in apps/web/dist
```

To look at the production build locally: `npm run preview -w apps/web`.

## Optional: publish on every merge

To publish automatically, add this under `on:` in `pages.yml`:

```yaml
  push:
    branches: [main]
```

It was left manual on purpose, so art and tooling merges do not republish a build you have not looked at. The `concurrency` group already cancels an older deploy if a newer one starts.

## Not covered

- Pages is public. If the game should be private, it needs a different host.
- There is no backend, so saved lances live in each browser's `localStorage` only (see `docs/mobile-feasibility.md`).
