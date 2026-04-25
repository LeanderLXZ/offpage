# Chinese Work Root And Work ID

- Timestamp: `2026-04-01T21:14:01-0400`

## Summary

Aligned the current Chinese work package with the updated naming rule that
Chinese works may use Chinese `work_id` values and matching Chinese root
folders under both `sources/works/` and `works/`.

## What Changed

- renamed the current source package root from:
  - `sources/works/wo-he-nvdi-de-jiushi-nieyuan/`
  - to:
  - `sources/works/我和女帝的九世孽缘/`
- renamed the current canonical work package root from:
  - `works/wo-he-nvdi-de-jiushi-nieyuan/`
  - to:
  - `works/我和女帝的九世孽缘/`
- updated current manifests, work README, candidate-analysis header, and AI
  handoff docs to use the Chinese `work_id`
- updated schema guidance so `work_id` may also be Chinese for Chinese works

## Why

Previous adjustments had already moved work-scoped identifiers and generated
subfolders toward Chinese naming, but the actual work package root still used a
pinyin directory. That left the most visible package path out of sync with the
project rule.
