import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { newsStory } from '../api'
import { modelPagePath, reportsPath } from '../catalog/format'
import { Badge } from '../components/ui'
import { Meta, Picture, SourceLink, StoryLink, full, groupLabel, siteOf, when } from '../news/parts'
import { useHead } from '../seo/head'
import { PRIVATE } from '../seo/pages'
import '../styles/news.css'

/**
 * ONE STORY'S PAGE (/news/<id>, signed in; anooj, 2026-10-28). A story opens
 * here before its source: the picture, the source's own summary, the models it
 * names with what engineers report about each on the board, then the link out.
 *
 * NOTHING HERE IS WRITTEN BY A MODEL. The headline, summary and picture are the
 * source's, labelled as theirs. The one line of our own is assembled from
 * counts (rule 3: a phrase built from counts, never a score). The models are
 * matched by code on exact registry names (judge/news.py `mentioned_models`);
 * a family name like "GPT-6" is never linked to one model.
 *
 * ONLY WHAT THE FEED AND THE PREVIEW TAG GIVE. The article's text is never
 * shown: this page credits and links, it does not republish.
 */

const list = (names) => (names.length < 2 ? names.join('') : `${names.slice(0, -1).join(', ')} and ${names[names.length - 1]}`)

/** Our one line: when the source published it and, when it names models, what
 *  the board holds on the most reported of them. Counts only. A story naming no
 *  model says nothing about models - absence is not news (anooj, 2026-10-28). */
function OurLine({ source, story, models }) {
  const said = when(story.published_at)
  const parts = [said ? `${source.label} published this ${said}.` : `${source.label} gives no date for this story.`]
  if (models.length > 0) {
    parts.push(`It names ${list(models.map((m) => m.name))}.`)
    const top = [...models].sort((a, b) => b.voices - a.voices)[0]
    parts.push(top.voices > 0
      ? `${top.voices} ${top.voices === 1 ? 'engineer has' : 'engineers have'} reported on ${top.name} on this board (${top.reports} ${top.reports === 1 ? 'report' : 'reports'}).`
      : `No engineer has reported on ${top.name} on this board yet.`)
  }
  return <p className="ns-line">{parts.join(' ')}</p>
}

function ModelCard({ m }) {
  return (
    <div className="ns-model">
      <div className="ns-model-name">{m.has_page ? <Link to={modelPagePath(m.id)}>{m.name}</Link> : m.name}</div>
      {m.voices > 0
        ? (
          <>
            <div className="ns-model-counts" title="Distinct engineers, and their reports, on the board's public view">
              <b>{m.voices}</b> {m.voices === 1 ? 'engineer' : 'engineers'} · {m.reports} {m.reports === 1 ? 'report' : 'reports'}
            </div>
            <Link className="ns-model-link" to={reportsPath(m.id)}>What engineers report →</Link>
          </>
        )
        : <div className="ns-model-counts dim">No engineer reports on the board yet</div>}
      {m.has_page && <Link className="ns-model-link" to={modelPagePath(m.id)}>Price and specs →</Link>}
    </div>
  )
}

function MiniCard({ it, sources }) {
  const source = sources[it.source_key]
  return (
    <article className="nw-card">
      <StoryLink it={it}><Picture it={it} source={source} /></StoryLink>
      <Meta it={it} source={source} />
      <h3><StoryLink it={it} className="nw-title">{it.title}</StoryLink></h3>
    </article>
  )
}

export default function NewsStory() {
  const { id } = useParams()
  const [data, setData] = useState(null)
  const [err, setErr] = useState(null)
  useHead({ ...PRIVATE.news, title: data ? `${data.story.title} | AI news` : PRIVATE.news.title })

  useEffect(() => {
    let alive = true
    setData(null)
    setErr(null)
    newsStory(id).then((d) => alive && setData(d)).catch((e) => alive && setErr(e.message))
    return () => { alive = false }
  }, [id])

  if (err) {
    return (
      <div className="shell section-tight stack stack-3">
        <Link className="ns-crumb" to="/news">← All news</Link>
        <p className="dim">This story could not be read: {err}</p>
      </div>
    )
  }
  if (!data) return <div className="shell section-tight"><div className="skel" style={{ height: 520 }} /></div>

  const { story, source, models, related, sources } = data
  const site = siteOf(story.url)
  return (
    <div className="shell section-tight stack stack-4">
      <nav className="ns-crumb" aria-label="Breadcrumb">
        <Link to="/news">News</Link> <span className="dim">/</span> <span>{source.label}</span>
      </nav>

      <header className="stack stack-2">
        <div className="nw-meta">
          <span className="nw-source">{source.label}</span>
          {groupLabel(source.group) && <span>{groupLabel(source.group)}</span>}
          {story.published_at
            ? <time dateTime={story.published_at}>{full(story.published_at)}</time>
            : <span title={`First seen ${full(story.first_seen_at)}`}>date not given by the source</span>}
          {story.llm_keywords.length > 0 && <Badge tone="pass" title={`Matched: ${story.llm_keywords.join(', ')}`}>LLM</Badge>}
        </div>
        <h1 className="ns-title">{story.title}</h1>
        {story.author && <p className="nw-byline">By {story.author}</p>}
      </header>

      <div className={models.length ? 'ns-body' : 'ns-body ns-body-one'}>
        <div className="stack stack-3">
          <SourceLink it={story}><Picture it={story} source={source} lead /></SourceLink>
          {story.image_url && (
            <p className="ns-caption">
              Picture: {story.image_source === 'link_preview' ? `the article's own preview image, from ${site}` : `${source.label}'s feed`}
            </p>
          )}
          {story.image_generic && (
            <p className="ns-caption">{source.label} uses one picture for every story, so a card is drawn instead.</p>
          )}

          <OurLine source={source} story={story} models={models} />

          <section className="ns-brief">
            <h2>
              In brief <span className="dim">· in {source.label}&apos;s words
                {story.summary_source === 'page_description' ? ", from the article's own description" : ''}</span>
            </h2>
            {story.summary
              ? <blockquote>{story.summary}</blockquote>
              : <p className="dim">{source.label}&apos;s feed gives no summary for this story.</p>}
            <SourceLink it={story} className="ns-read">Read the full story on {site} ↗</SourceLink>
          </section>

          {story.categories.length > 0 && (
            <div className="nw-tags">{story.categories.slice(0, 8).map((c) => <span key={c}>{c}</span>)}</div>
          )}
        </div>

        {models.length > 0 && (
          <aside className="stack stack-3 ns-side" aria-label="Models in this story">
            <h2 className="nw-latest-head">Models in this story</h2>
            {models.map((m) => <ModelCard key={m.id} m={m} />)}
            <p className="dim ns-note">
              Matched by code on exact model names; a family name such as &quot;GPT-6&quot; is never linked to one model.
            </p>
          </aside>
        )}
      </div>

      {related.same_model.length > 0 && (
        <section className="stack stack-2">
          <h2 className="nw-section-head">More on {list([...new Set(related.same_model.flatMap((r) => r.shares))].slice(0, 3))}</h2>
          <div className="nw-grid">{related.same_model.map((it) => <MiniCard key={it.id} it={it} sources={sources} />)}</div>
        </section>
      )}
      {related.same_source.length > 0 && (
        <section className="stack stack-2">
          <h2 className="nw-section-head">More from {source.label}</h2>
          <div className="nw-grid">{related.same_source.map((it) => <MiniCard key={it.id} it={it} sources={sources} />)}</div>
        </section>
      )}

      <p className="dim ns-credit">
        The headline{story.summary ? ', summary' : ''}{story.image_url ? ' and picture' : ''} {story.summary || story.image_url ? 'are' : 'is'}{' '}
        {source.label}&apos;s; this page links to the original and shows nothing more of it. Nothing on this
        page is written by a model.
      </p>
    </div>
  )
}
