# 🎨 DESIGN: QUERYX UI

The UI is one file, `static/index.html`: plain HTML, CSS variables and vanilla JS, with Chart.js 4 for charts.
Principles: clarity first (always show the SQL), calm neutral surfaces, one accent color, works in light and dark.

## 1. 🧱 Layout
- **Header:** product name, engine badge (`engine: demo (offline)` or `engine: llm`), one-line tagline.
- **Two-column grid:** **280 px sidebar** + flexible main column. Max width 1300 px, 16 px gap, page padding 16 px / 20 px.
- **Responsive:** below **860 px** the grid collapses to one column (sidebar content stacks above main).
- **Sidebar cards:** **🗂️ Data** (schema), **📤 Upload CSV**, **🕘 History**.
- **Main cards, top to bottom:** **💬 Ask** (input, Ask button, example chips) → **⚠️ Error** (hidden unless needed) → **🧾 Generated SQL** → **📈 Result** (metric cards or chart) → **📋 Rows** (table).

## 2. 🎨 Color tokens
Defined on `:root`, overridden in `@media (prefers-color-scheme: dark)`.

| Token | Light | Dark | Use |
|---|---|---|---|
| `--bg` | `#f6f7f9` | `#0f1115` | Page background, input background |
| `--panel` | `#ffffff` | `#171a21` | Cards, header, buttons |
| `--text` | `#1b1f24` | `#e8eaee` | Primary text |
| `--muted` | `#667085` | `#9aa3b2` | Secondary text, labels |
| `--border` | `#e3e6eb` | `#2a2f3a` | Card and table borders |
| `--accent` | `#3b5bdb` | `#748ffc` | Primary button, focus emphasis |
| `--accent-text` | `#ffffff` | `#0f1115` | Text on accent |
| `--code-bg` | `#f1f3f6` | `#1e222b` | SQL block background |
| `--error` | `#c92a2a` | `#ff8787` | Error text |
| `--ok` | `#2b8a3e` | `#69db7c` | Reserved for success states |

**Chart palette (series order):** `#3b5bdb`, `#f08c00`, `#2b8a3e`, `#c2255c`, `#1098ad`.
Bars use 80% opacity fill (`cc` suffix) with a solid border; lines are 2 px with 0.25 tension and visible points.
Color is never the only carrier of meaning: multi-series charts show a legend.

## 3. 🔤 Typography
| Role | Spec |
|---|---|
| Body | `system-ui, -apple-system, Segoe UI, Roboto, sans-serif`, 15 px / 1.5 |
| Product name | 18 px, bold |
| Card titles | 13 px, uppercase, letter-spacing .04em, muted |
| Code (SQL) | `ui-monospace, SFMono-Regular, Menlo, monospace`, 13 px / 1.45, wraps |
| Table | 13 px; numbers right-aligned with tabular figures |
| Metric value | 28 px, bold; label 12 px muted |

## 4. 🧩 Components
- **Card:** panel background, 1 px border, 10 px radius, 14 px padding, 16 px vertical spacing between cards.
- **Primary button (Ask):** accent background, bold, 8 px radius; disabled state shows `Thinking…` and reduced opacity.
- **Secondary button (Copy, Download CSV):** panel background, border, 8 px radius.
- **Example chip:** pill (999 px radius), 12 px text; clicking fills the input and asks immediately.
- **Text input:** 10 px / 12 px padding, 8 px radius, `--bg` background; max length 500.
- **SQL block:** `--code-bg`, 8 px radius, scrolls, preserves wrapping; explanation below in muted 13 px.
- **Metric card:** bordered tile, min width 150 px, one per returned column.
- **Data table:** sticky header, row dividers, max height 360 px with scroll, `null` values shown in the muted color.
- **Chart box:** 320 px tall, responsive, hidden when the suggestion is `metric` or `table`.
- **History item:** one line per question, click to re-ask.
- **Error card:** error color text; shows the server `detail` message verbatim.

## 5. 🔄 Interaction states
| State | Behavior |
|---|---|
| Loading | Ask button disabled with `Thinking…`; previous error hidden |
| Success | SQL, chart/metrics, table and meta line (`N row(s) · X ms`, plus `(truncated)` or `auto-repaired SQL`) |
| Error | Result hidden; error card shows message (unsafe SQL, unsupported question, timeout, LLM failure) |
| Empty history | `No questions yet.` |
| Upload | Message under the file picker: success summary or error; schema refreshes after success |
| No chart library | Chart area stays hidden; table still renders |

## 6. ✍️ Content and tone
- Short, plain-English messages; say what happened and what to try next.
- Demo-mode errors list sample questions and mention the API key (`LLM_API_KEY`).
- Never show stack traces, paths or keys.

## 7. ♿ Accessibility
- Native elements (form, input, button, table) for keyboard and screen-reader support; Enter submits.
- Input is auto-focused on load.
- Contrast: aim for WCAG AA on both themes when changing tokens (not formally audited yet).
- Dynamic text is escaped; no reliance on color alone.

## 8. 🗺️ Planned design improvements
Visible focus rings, aria-live region for results and errors, chart type switcher, saved-query favorites,
column sorting, and a tablet breakpoint review.

## 9. 🔁 Three-Cycle Live Proof (UI checks)
- **Cycle 1:** UI still renders key states (loading/success/error) after changes.
- **Cycle 2:** Live run confirms SQL/table/chart/history/upload behaviors.
- **Cycle 3:** Evaluation/demo prompts exercise representative UI result shapes (metric/line/bar/table).
