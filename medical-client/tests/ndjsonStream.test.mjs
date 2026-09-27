import assert from 'node:assert/strict'
import test from 'node:test'

import { readNdjsonStream } from '../src/utils/ndjsonStream.ts'

function streamOf(...chunks) {
  return new ReadableStream({
    start(controller) {
      for (const chunk of chunks) controller.enqueue(chunk)
      controller.close()
    },
  })
}

test('accepts split UTF-8 events when the stream ends with done', async () => {
  const bytes = new TextEncoder().encode(
    '{"type":"start"}\n{"type":"delta","content":"你好"}\n{"type":"done"}\n',
  )
  const events = []

  await readNdjsonStream(streamOf(bytes.slice(0, 40), bytes.slice(40, 42), bytes.slice(42)),
    (event) => events.push(event))

  assert.deepEqual(events.map((event) => event.type), ['start', 'delta', 'done'])
  assert.equal(events[1].content, '你好')
})

test('rejects a closed stream that only delivered a partial answer', async () => {
  const events = []
  const bytes = new TextEncoder().encode(
    '{"type":"start"}\n{"type":"delta","content":"半截回答"}\n',
  )

  await assert.rejects(readNdjsonStream(streamOf(bytes), (event) => events.push(event)),
    /流式回答中断/)
  assert.deepEqual(events.map((event) => event.type), ['start', 'delta'])
})

test('rejects an error event even when the callback does not throw', async () => {
  const bytes = new TextEncoder().encode('{"type":"error","message":"请求失败"}\n')

  await assert.rejects(readNdjsonStream(streamOf(bytes), () => {}), /请求失败/)
})
