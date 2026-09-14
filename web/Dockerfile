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

# `vite.config.js` reads the repo-root `.env` via `loadEnv(mode, REPO_ROOT, '')`
# to find API_TOKEN. That file is not in this build context and must not be -
# `loadEnv` returns an empty value, `define` injects an empty token, and the
# session path above is what carries the credential.
RUN npm run build


FROM nginx:alpine

# nginx:alpine runs `envsubst` over /etc/nginx/templates/*.template at startup
# and writes the result into /etc/nginx/conf.d/. That is how $PORT - which the
# platform assigns and which nginx cannot read from the environment by itself -
# reaches the `listen` directive.
COPY nginx.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /web/dist /usr/share/nginx/html

ENV PORT=8080
EXPOSE 8080
