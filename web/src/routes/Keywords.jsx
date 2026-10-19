import { useSearchParams } from 'react-router-dom'
import OnOurPages from './KeywordsOnOurPages'
import KeywordPlan from './KeywordPlan'
import '../styles/keywords.css'

/**
 * SEO KEYWORDS: two tabs (2026-10-19).
 *
 *   Keywords on our pages   Parvathi's dashboard, unchanged
 *                           (routes/KeywordsOnOurPages.jsx): which workbook keywords
 *                           sit on each public page today, and where.
 *   Keyword plan            which keywords to USE on which public page, at
 *                           10,000+ searches a month, and the pages and tools
 *                           worth adding (routes/KeywordPlan.jsx).
 *
 * The tab is in the address (`?tab=plan`), so a view can be sent to somebody.
 * Each tab keeps its own query parameters; switching drops the other's.
 */
const TABS = [
  { key: 'onsite', label: 'Keywords on our pages' },
  { key: 'plan', label: 'Keyword plan' },
]

export default function Keywords() {
  const [sp, setSp] = useSearchParams()
  const tab = sp.get('tab') === 'plan' ? 'plan' : 'onsite'
  const open = (key) => setSp(key === 'plan' ? { tab: 'plan' } : {})

  return (
    <>
      <div className="shell kw-tabbar">
        <div className="kw-tabs" role="tablist" aria-label="SEO keyword views">
          {TABS.map((t) => (
            <button key={t.key} type="button" role="tab" aria-selected={tab === t.key}
                    className={`kw-tab ${tab === t.key ? 'kw-tab-on' : ''}`} onClick={() => open(t.key)}>
              {t.label}
            </button>
          ))}
        </div>
      </div>
      {tab === 'plan' ? <KeywordPlan /> : <OnOurPages />}
    </>
  )
}
