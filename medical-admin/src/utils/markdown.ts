/**
 * Render the small Markdown subset used by AI report interpretations.
 * Escape HTML first so v-html cannot execute model-provided markup.
 */
function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

export function renderMarkdown(text: string): string {
  const lines = escapeHtml(text).split('\n')
  const html: string[] = []
  let listTag: 'ul' | 'ol' | null = null

  const closeList = () => {
    if (listTag) {
      html.push(`</${listTag}>`)
      listTag = null
    }
  }

  for (const line of lines) {
    const trimmed = line.trim()
    const headingMatch = trimmed.match(/^(#{1,4})\s+(.*)$/)
    const bulletMatch = trimmed.match(/^[*-]\s+(.*)$/)
    const orderedMatch = trimmed.match(/^\d+[.)]\s+(.*)$/)
    const isDivider = /^([-*_])\1{2,}$/.test(trimmed)

    if (isDivider) {
      closeList()
      html.push('<hr>')
      continue
    }

    if (headingMatch) {
      closeList()
      const level = Math.min(headingMatch[1].length + 1, 4)
      html.push(`<h${level}>${inline(headingMatch[2])}</h${level}>`)
      continue
    }

    if (bulletMatch || orderedMatch) {
      const wanted: 'ul' | 'ol' = bulletMatch ? 'ul' : 'ol'
      if (listTag !== wanted) {
        closeList()
        html.push(`<${wanted}>`)
        listTag = wanted
      }
      html.push(`<li>${inline((bulletMatch || orderedMatch)![1])}</li>`)
      continue
    }

    closeList()
    if (trimmed) {
      html.push(`<p>${inline(trimmed)}</p>`)
    }
  }

  closeList()
  return html.join('')
}

function inline(text: string): string {
  return text.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
}
