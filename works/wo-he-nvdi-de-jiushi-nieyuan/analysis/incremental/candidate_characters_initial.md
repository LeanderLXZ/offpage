# Candidate Character Identification

## Work

- `work_id`: `wo-he-nvdi-de-jiushi-nieyuan`
- title: `我和女帝的九世孽缘`
- source status: normalized EPUB work package
- chapter count: `537`

## Scope

This is an initial candidate-character identification pass.

It was intentionally limited to:

- work-package metadata
- chapter-title scan
- lightweight surface-form mention counts across normalized chapters
- small targeted reads of high-signal chapters

It did not use:

- a full-novel end-to-end read
- full-log review
- large evidence dumps

## Method Notes

- Mention counts below are first-pass surface-string counts from normalized
  chapter files.
- They are useful for ranking importance, but they are not a final canonical
  identity graph.
- Alias handling is still partial. Some role labels and nickname forms are
  included only when they were directly observed during targeted validation.
- Role descriptions distinguish explicit source support from light inference.

## Work-Package Snapshot

- `manifest.json` reports the work as `normalized`.
- `metadata/book_metadata.json` reports `537` chapters.
- `metadata/chapter_index.json` provides per-chapter title, path, paragraph
  count, and character count.
- `chapters/` contains `537` normalized chapter files.
- `scenes/`, `chunks/`, and `rag/` exist but are currently empty.

## Candidate Characters

### 1. 王枫

- normalized name: `王枫`
- aliases / other forms:
  - `小枫`
  - `师父`
  - early descriptive mockery around `倭瓜男`
- importance: `highest`
- short role:
  - primary male lead
  - current main viewpoint carrier
  - nine-life / system-linked protagonist tied to the central relationship arc
- first-pass mention stats:
  - about `14862` surface-form mentions
  - across `534` chapters
- evidence anchors:
  - early direct interaction with姜寒汐 in `chapters/0006.txt`,
    `chapters/0008.txt`, `chapters/0009.txt`
  - takes 萧浩 as disciple in `chapters/0033.txt`
  - chapter-title signals include chapter `94`, `110`, `304`, `314`, `389`,
    `512`

### 2. 姜寒汐

- normalized name: `姜寒汐`
- aliases / other forms:
  - `寒汐`
  - `汐`
  - `极冰女帝`
  - `冰宫宫主`
  - `冷傻子`
- importance: `highest`
- short role:
  - primary female lead
  - central counterpart to 王枫
  - core time-stage and relationship-logic anchor for the novel
- first-pass mention stats:
  - about `10734` surface-form mentions
  - across `500` chapters
- evidence anchors:
  - title mentions in chapter `4`, `8`, `23`, `27`, `31`, `64`, `101`,
    `124`, `149`, `166`, `289`, `368`
  - early personality and relationship setup in `chapters/0006.txt`,
    `chapters/0008.txt`, `chapters/0009.txt`
  - later alias evidence in `chapters/0413.txt`

### 3. 萧浩

- normalized name: `萧浩`
- aliases / other forms:
  - `徒儿` in relation to 王枫
  - `死耗子` in 楚妍儿's speech
- importance: `high`
- short role:
  - major male supporting character
  - 王枫's disciple
  - own subplot is sustained enough to support independent packaging later
- first-pass mention stats:
  - about `1155` surface-form mentions
  - across `86` chapters
- evidence anchors:
  - disciple setup in `chapters/0033.txt`
  - recurring titled chapters `47`, `48`, `169`, `170`, `172`, `173`, `174`,
    `382`, `413`, `414`, `423`, `429`
  - relation dynamic with 楚妍儿 visible in `chapters/0057.txt`

### 4. 楚妍儿

- normalized name: `楚妍儿`
- aliases / other forms:
  - `妍儿`
- importance: `high`
- short role:
  - major female supporting character
  - daughter of 楚沫兮
  - tightly linked to 萧浩's ongoing subplot
- first-pass mention stats:
  - about `605` surface-form mentions
  - across `74` chapters
- evidence anchors:
  - strong early presence in `chapters/0057.txt` and `chapters/0066.txt`
  - later title signals in chapter `426`, `428`, `430`
  - grouped by 王枫 with 萧浩 and 冷凝月 in `chapters/0413.txt`

### 5. 冷凝月

- normalized name: `冷凝月`
- aliases / other forms:
  - `冷圣女`
- importance: `high`
- short role:
  - important female supporting character from the 冰宫 line
  - often functions as an observer, witness, and relationship-pressure node
  - has enough recurrence and independent perspective to be a packaging
    candidate
- first-pass mention stats:
  - about `587` surface-form mentions
  - across `61` chapters
- evidence anchors:
  - appears by `chapters/0117.txt`
  - strong characterization in `chapters/0154.txt` and `chapters/0210.txt`
  - later involved with 苏婉 and仙界 transition in `chapters/0453.txt`,
    `chapters/0459.txt`

### 6. 苏婉

- normalized name: `苏婉`
- aliases / other forms:
  - no stable alternate form validated yet beyond direct name use
- importance: `medium-high`
- short role:
  - important later-stage female supporting character
  - high-power仙界 figure with direct influence on 姜寒汐, 王枫, and 冷凝月
- first-pass mention stats:
  - about `276` surface-form mentions
  - across `29` chapters
- evidence anchors:
  - titled chapter signals at `398`, `408`, `439`, `457`, `459`, `460`
  - direct role validation in `chapters/0398.txt`, `chapters/0453.txt`,
    `chapters/0459.txt`

### 7. 许青枫

- normalized name: `许青枫`
- aliases / other forms:
  - no stable alternate form validated yet
- importance: `medium`
- short role:
  - later-stage male supporting character
  - not central like 王枫 or 姜寒汐, but receives enough dedicated focus to
    remain a strong candidate
- first-pass mention stats:
  - about `136` surface-form mentions
  - across `19` chapters
- evidence anchors:
  - introduction and interaction check in `chapters/0273.txt`
  - explicit title signals in chapter `279` and `280`

### 8. 柳青瑶

- normalized name: `柳青瑶`
- aliases / other forms:
  - no stable alternate form validated yet
- importance: `medium`
- short role:
  - later conflict-heavy female character
  - appears tied to a multi-soul / confrontation line involving 王枫 and
    姜寒汐
- first-pass mention stats:
  - about `152` surface-form mentions
  - across `19` chapters
- evidence anchors:
  - referenced in `chapters/0260.txt`
  - strong conflict evidence in `chapters/0363.txt`
  - also appears in later reflective grouping in `chapters/0413.txt`

### 9. 楚沫兮

- normalized name: `楚沫兮`
- aliases / other forms:
  - validated descriptive roles:
    - `东阳皇朝女帝`
    - `仙庭前代圣女`
- importance: `medium`
- short role:
  - important parental / royal-line character
  - mother of 楚妍儿
  - not as chapter-pervasive as the top tier, but clearly canon-significant
- first-pass mention stats:
  - about `100` surface-form mentions
  - across `9` chapters
- evidence anchors:
  - authority and family-role setup in `chapters/0066.txt`
  - explicit identity line in `chapters/0310.txt`

### 10. 秦羽溪

- normalized name: `秦羽溪`
- aliases / other forms:
  - no stable alternate form validated yet
- importance: `medium-`
- short role:
  - later female supporting character
  - strong enough to track, but not yet strong enough to prioritize over the
    groups above
- first-pass mention stats:
  - about `81` surface-form mentions
  - across `9` chapters
- evidence anchors:
  - introduction signal in `chapters/0213.txt`
  - title mentions in chapter `168`, `483`, `486`

## Important Non-Human Or Special Companion Candidate

### 哈弟

- not ranked together with the human candidate list above
- clearly recurring enough to track separately
- evidence anchors:
  - title mention in chapter `413`
  - later appears around 冷凝月 and 苏婉 in `chapters/0453.txt`,
    `chapters/0459.txt`

## Provisional Ranking Summary

Recommended current packaging priority if the user wants to start with the most
important roles:

1. `姜寒汐`
2. `王枫`
3. `萧浩`
4. `楚妍儿`
5. `冷凝月`

## Recommended Next Step

Do not jump into whole-book character construction.

Instead:

1. let the user choose one or two target characters from the list above
2. start batch extraction on about `8-20` chapters at a time
3. keep evidence chains and incremental revisions
4. update character data incrementally instead of rewriting it from scratch

## Targeted Validation Chapters Used In This Pass

- `chapters/0006.txt`
- `chapters/0008.txt`
- `chapters/0009.txt`
- `chapters/0033.txt`
- `chapters/0057.txt`
- `chapters/0066.txt`
- `chapters/0117.txt`
- `chapters/0154.txt`
- `chapters/0210.txt`
- `chapters/0213.txt`
- `chapters/0260.txt`
- `chapters/0273.txt`
- `chapters/0310.txt`
- `chapters/0363.txt`
- `chapters/0398.txt`
- `chapters/0413.txt`
- `chapters/0453.txt`
- `chapters/0459.txt`
