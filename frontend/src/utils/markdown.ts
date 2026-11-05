import { marked } from 'marked'

// 极简 XSS 防护：去除 script 标签与内联事件处理器后渲染 Markdown
export function renderMarkdown(text: string): string {
  if (!text) return ''
  const safe = text
    .replace(/<script[\s\S]*?<\/script>/gi, '')
    .replace(/<script[\s\S]*?>/gi, '')
    .replace(/\son\w+\s*=\s*("[^"]*"|'[^']*'|[^\s>]+)/gi, '')
    .replace(/javascript:/gi, '')
  return marked.parse(safe, { async: false }) as string
}

export function plainTextFromMarkdown(text: string): string {
  if (!text) return ''
  return text
    .replace(/[#*`>\-\[\]()]/g, '')
    .replace(/\s+/g, ' ')
    .trim()
}