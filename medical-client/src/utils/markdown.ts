/**
 * 极简 Markdown 渲染，只处理 AI 回复中实际会出现的语法：
 * 标题、有序/无序列表、分隔线、加粗、换行。先转义 HTML 再替换，避免 XSS。
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
  // 有序与无序列表要用不同标签，需记录当前列表类型
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
    // 三个及以上的 - * _ 视为分隔线
    const isDivider = /^([-*_])\1{2,}$/.test(trimmed)

    if (isDivider) {
      closeList()
      html.push('<hr>')
      continue
    }

    if (headingMatch) {
      closeList()
      // 报告解读里用 ### 分节，统一降级避免标题过大
      const level = Math.min(headingMatch[1].length + 1, 4)
      html.push(`<h${level}>${inline(headingMatch[2])}</h${level}>`)
      continue
    }

    if (bulletMatch || orderedMatch) {
      const wanted: 'ul' | 'ol' = bulletMatch ? 'ul' : 'ol'
      // 列表类型切换时先收尾再开新列表
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
