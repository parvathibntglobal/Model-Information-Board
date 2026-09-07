import { useParams } from 'react-router-dom'
import { vBlogs, vPost } from '../board/views'
import BoardView from '../board/BoardView'

/**
 * Blogs, ported from the SEO demo: working notes about the models, with our
 * findings used as evidence. Each figure in a post is a bookmark (E1–E5) into
 * the evidence panel at the foot — BoardView wires the scroll-and-highlight.
 *
 *   /blogs         → the index
 *   /blogs/:slug   → one post
 */
export default function Blogs() {
  const rest = useParams()['*'] || ''
  const html = rest ? vPost(rest) : vBlogs()
  return <BoardView html={html} key={rest} />
}
