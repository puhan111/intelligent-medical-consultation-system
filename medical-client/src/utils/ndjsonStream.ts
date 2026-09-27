type StreamEvent = { type: string; message?: string }

export async function readNdjsonStream<T extends StreamEvent>(
  body: ReadableStream<Uint8Array> | null,
  onEvent: (event: T) => void,
): Promise<void> {
  if (!body) throw new Error('浏览器不支持流式响应')

  const reader = body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let completed = false

  function handleLine(line: string) {
    if (!line.trim()) return
    const event = JSON.parse(line) as T
    onEvent(event)
    if (event.type === 'error') throw new Error(event.message || '流式回答失败')
    if (event.type === 'done') completed = true
  }

  try {
    while (true) {
      const { value, done } = await reader.read()
      buffer += decoder.decode(value, { stream: !done })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''
      for (const line of lines) handleLine(line)
      if (done) break
    }

    handleLine(buffer)
    if (!completed) throw new Error('流式回答中断，请重试')
  } finally {
    reader.releaseLock()
  }
}
