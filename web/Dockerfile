# Frontend: Vite build, served as static files by nginx.
#
# VITE_API_URL IS A BUILD ARGUMENT, NOT A RUNTIME VARIABLE, AND THIS IS THE
# EASIEST THING ON THIS PAGE TO GET WRONG.
#
# Vite INLINES `import.meta.env.*` into the bundle at build time. Setting
# VITE_API_URL in Railway's runtime variables for this service changes nothing
# at all - the string is already compiled into the JavaScript, and the app goes
# on calling the dev-proxy default `/api`, which on a static host is a 404 from
# nginx rather than an error anybody can read. Set it as a BUILD variable.
#
# API_TOKEN IS DELIBERATELY NOT PASSED, and `web/vite.config.js` already ruled
# on this: "a deployed build must get its credential from a session the server
# issues, never from a value compiled into the client." `judge/gate.py` accepts
# two kinds of bearer - the static API_TOKEN and a signed session from
# /auth/login - so the deployed bundle needs no token: the person signs in and
# the session token satisfies the gate. Passing API_TOKEN here would publish
# the backend's shared secret to every visitor, and would also be unnecessary.

FROM node:22-alpine AS build

# THE BROWSER FOR PRE-RENDERING (web/prerender.js, 2026-10-20). `npm run build`
# saves each public page's finished HTML when the site is open (SITE_URL +
# PUBLIC_SITE=1) or PRERENDER=1, reading the API named by VITE_API_URL - so
# that API must be reachable from the build. A closed build skips it.
RUN apk add --no-cache chromium
ENV CHROME_PATH=/usr/bin/chromium

WORKDIR /web

# `npm ci` NOT `npm install`, because `package-lock.json` is committed and a
# deployment that resolves its own versions is a deployment that differs from
# the one that was tested.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# The default is the dev proxy path, which is correct for `npm run dev` and
# wrong for every deployed build. Left as the default rather than made
# mandatory so a local `docker build` still produces something that runs; the
# variables block in the deployment notes says to set it.
ARG VITE_API_URL=/api
ENV VITE_API_URL=$VITE_API_URL

# THE SWITCH THAT OPENS THE SITE, and pre-rendering with it (2026-10-20).
# Railway hands a service variable to the build only when it is declared here,
# so until now SITE_URL and PUBLIC_SITE never reached `vite build` and the
# deployed site stayed closed whatever the variables said. Empty = closed.
# PRERENDER_API is where pre-rendering reads data when VITE_API_URL is the
# relative `/api`.
#
# THE PAGE LIST FOR AN OPEN BUILD (2026-10-21). vite.config.js refuses an open
# build without SEO_PATHS_FILE (the sitemap would list only the structural
# pages). Writing it takes the database, which this image cannot reach - but
# pre-rendering already needs PRERENDER_API, and that API serves the same file:
# `/seo/indexable?export=1` is scripts/export_indexable_paths.py's output, field
# for field. So an open build fetches it there, unless SEO_PATHS_FILE was
# given. No PRERENDER_API on an open build FAILS here, by name, rather than at
# the sitemap step with a message about a file. Same "open" test as
# web/seo-build.js `siteOf`: SITE_URL set and PUBLIC_SITE exactly 1.
ARG SITE_URL=
ARG PUBLIC_SITE=
ARG PRERENDER=
ARG PRERENDER_API=
ARG SEO_PATHS_FILE=
ENV SITE_URL=$SITE_URL PUBLIC_SITE=$PUBLIC_SITE PRERENDER=$PRERENDER PRERENDER_API=$PRERENDER_API

# `vite.config.js` reads the repo-root `.env` via `loadEnv(mode, REPO_ROOT, '')`
# to find API_TOKEN. That file is not in this build context and must not be -
# `loadEnv` returns an empty value, `define` injects an empty token, and the
# session path above is what carries the credential.
#
# SEO_PATHS_FILE is resolved from the repo root (vite.config.js), which is `/`
# in this image, so the fetched file is named `web/seo-paths.json`.
RUN set -e; \
    if [ -n "$SITE_URL" ] && [ "$(echo "$PUBLIC_SITE" | tr -d ' ')" = "1" ] && [ -z "$SEO_PATHS_FILE" ]; then \
      if [ -z "$PRERENDER_API" ]; then \
        echo "open build refused: PRERENDER_API is not set, so the indexable page list cannot be fetched" >&2; \
        exit 1; \
      fi; \
      wget -q -T 120 -O /web/seo-paths.json "${PRERENDER_API%/}/seo/indexable?export=1"; \
      SEO_PATHS_FILE=web/seo-paths.json npm run build; \
    else \
      SEO_PATHS_FILE="$SEO_PATHS_FILE" npm run build; \
    fi


FROM nginx:alpine

# nginx:alpine runs `envsubst` over /etc/nginx/templates/*.template at startup
# and writes the result into /etc/nginx/conf.d/. That is how $PORT - which the
# platform assigns and which nginx cannot read from the environment by itself -
# reaches the `listen` directive.
COPY nginx.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /web/dist /usr/share/nginx/html

ENV PORT=8080
EXPOSE 8080
