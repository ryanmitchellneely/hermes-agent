import { describe, expect, it } from 'vitest'

import { formatLocalReasoning, separateGluedReasoningBlocks } from '@/lib/reasoning-blocks'

describe('separateGluedReasoningBlocks', () => {
  it('splits heading-onto-heading parts (the `****` run)', () => {
    const glued =
      '**Investigating likely culprit PRs****Inspecting message schema****Analyzing interrupted tool call impact**'

    expect(separateGluedReasoningBlocks(glued)).toBe(
      [
        '**Investigating likely culprit PRs**',
        '',
        '**Inspecting message schema**',
        '',
        '**Analyzing interrupted tool call impact**'
      ].join('\n')
    )
  })

  it('splits prose-onto-heading parts (vercel/ai#6742 repro)', () => {
    const glued =
      '**Simulating a greeting stream**\n\nIt feels like a streaming interaction!**Simulating a greeting stream**\n\nI want to meet the request.'

    expect(separateGluedReasoningBlocks(glued)).toContain('interaction!\n\n**Simulating')
    expect(separateGluedReasoningBlocks(glued)).not.toContain('interaction!**')
  })

  it('is idempotent on already-separated text', () => {
    const separated = '**One**\n\n**Two**'

    expect(separateGluedReasoningBlocks(separated)).toBe(separated)
  })

  it('leaves emphasis inside prose alone', () => {
    const prose = 'Looking at the logs, the **signature** field is missing — so the replay 400s.'

    expect(separateGluedReasoningBlocks(prose)).toBe(prose)
  })

  it('leaves an unclosed emphasis run alone', () => {
    expect(separateGluedReasoningBlocks('weighing options **')).toBe('weighing options **')
  })

  it('does not split a heading that already opens the text', () => {
    expect(separateGluedReasoningBlocks('**Only one part**')).toBe('**Only one part**')
  })
})

describe('formatLocalReasoning', () => {
  it('strips a local "The user wants…" preamble and breaks discourse turns', () => {
    const wall =
      'The user wants a sentence of exactly 7 words. Let me think of words starting with each letter. Actually, that first try is awkward. So I will try again.'

    expect(formatLocalReasoning(wall)).toBe(
      [
        'Let me think of words starting with each letter.',
        '',
        'Actually, that first try is awkward.',
        '',
        'So I will try again.'
      ].join('\n')
    )
  })

  it('leaves already-paragraphed or fenced thoughts alone', () => {
    const paragraphed = 'First beat.\n\nSecond beat.'
    const fenced = 'Let me look:\n```python\nprint(1)\n```\nDone.'

    expect(formatLocalReasoning(paragraphed)).toBe(paragraphed)
    expect(formatLocalReasoning(fenced)).toBe(fenced)
  })

  it('is a no-op on short Grok-style summaries', () => {
    expect(formatLocalReasoning('Checking the live tunnel next.')).toBe('Checking the live tunnel next.')
  })

  it('keeps a one-sentence "The user is asking…" thought', () => {
    expect(formatLocalReasoning('The user is asking what this file is.')).toBe(
      'The user is asking what this file is.'
    )
  })
})
