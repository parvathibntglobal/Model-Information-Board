# For whoever ships the frontend: the bundle is the access boundary

**2026-09-08, from anooj. Sent as
[issue #225](https://github.com/parvathibntglobal/Model-Information-Board/issues/225).
One deployment question, and it is not a pipeline question — which is why it is
in its own document rather than buried in a triage or terms writeup.**

Nothing here is urgent-broken today. Nothing is deployed. The point is that
**one deploy is the thing that changes the answer**, and the person who presses
it should know that before rather than after.

---

## The finding

`web/src/App.jsx` guards every route:

```jsx
<Route path="/articles" element={<Require session={session}><Articles /></Require>} />
```

That is a **client-side** guard. It decides what React renders. It does not
decide what the browser downloaded — and `web/src/auth.js` already says this
about the thing it replaced, in its own words:

> A guard in the client protects the view. It never protected the data.

That sentence was written about a password hash shipped in the bundle. It
applies unchanged to the Articles data, because
`web/src/data/articles.js` does this:

```js
import deepseekX from './deepseek-v4-pro-x.json'
import deepseekReddit from './deepseek-v4-pro-reddit.json'
// …eight more
```

Static imports. They are **compiled into the JavaScript bundle**. Anyone who
can fetch the built asset has the contents, signed in or not — view-source, a
`curl` of the JS chunk, devtools with the login screen still on top.

## What is in there

Not placeholder data. Real quotes, real handles, real permalinks:

| file | records | fields |
|---|---|---|
| `deepseek-v4-pro-x.json` | 149 posts | `handle`, `profile_url`, `status_url`, `quote` |
| `deepseek-v4-pro-reddit.json` | 150 posts | `author`, `url`, `excerpt` |
| `deepseek-v4-pro-hn.json` | 34 posts | `author`, `url`, `quote` |
| `deepseek-v4-pro-devto.json` | 53 posts | `author`, `url`, `excerpt` |
| `deepseek-v4-pro-arxiv.json` | 43 articles | `authors`, `abs_url` |

The one page that *is* placeholder data is Landing's throughput panel, and it
carries an `illustrative` badge. The Articles pages carry none, correctly —
they are real.

## Why it matters beyond the usual

Two of those platforms are governed by terms rulings that turn on exactly this.
`contract/sources.yaml` permits Reddit and X **on an internal-development-only
basis, and only while nothing is published externally**, where published means:

> a quote from a platform, shown with a link, to somebody outside the team.

One reader is enough. Not a launch. So a deployed build with those 149 X quotes
and 150 Reddit quotes in the bundle trips that condition **whether or not
anyone logs in** — the sign-in does not narrow it, because the sign-in is not
where the data is.

And nothing will tell you. The terms checks live on the fetch path
(`assert_terms_reviewed`, called from the harvesters); `judge/app.py`,
`judge/gate.py` and the bundle consult no ruling. The pipeline would go on
passing every assertion.

## What I am asking for

Not a rewrite. A decision made on purpose before the first deploy, from these
three:

1. **Keep it local.** No hosted build. Costs nothing, changes nothing, and is
   the status quo — worth choosing explicitly rather than by default.
2. **Serve the Articles data from the API instead of bundling it.** Move the
   ten JSON files behind a route that `judge/gate.py` already closes, and fetch
   them after sign-in. That makes the existing token the real boundary rather
   than a view filter. Biggest change, and the only one that makes "signed-in
   only" true.
3. **Deploy with the Articles route removed from the build.** Ship Landing,
   Board, Ask and Models; leave Articles out of the bundle entirely until (2)
   exists. Cheapest way to get a hosted demo without the quotes travelling.

**If a hosted build is wanted sooner than (2) can be done, (3) is the one I would
take** — the quotes are the whole exposure, and Articles is the only page that
carries them.

Whichever it is, tell me which, because the terms condition is honoured by
people rather than by code and I would rather we all know the same thing about
it. Happy to be wrong about any of the above if the bundle is served somewhere
I have not looked.

---

*Related, for context only, and not something you need to read:*
*`contract/sources.yaml` — the "WHAT COUNTS AS PUBLICATION" and "ENFORCEMENT"
blocks;* *`docs/three-decisions-ruled-2026-09-08.md` §1 and §4.*
