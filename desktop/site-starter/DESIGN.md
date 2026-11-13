# Dex design kit

This kit gives every page the same polished look: the system font (San Francisco on Apple devices) for
everything, near-black (or white) with one quiet accent, soft cards. Light and dark both, following the device. It does not decide the layout. Choose the layout that
fits the content best: a report, a dashboard with a sidebar, a landing page, a one-page document, a tool.
`app.js` holds ready parts and one example page; keep what helps, delete the rest.

## The look (always)
- Use the tokens in style.css (colours, --c1 … --c5 for charts, light and dark). Change --accent only for a brand.
- One font: the system sans. Headlines semibold with tight spacing; small grey labels; no decorative fonts.
- Cards: 1 px line, 18 px corners, gentle shadow. Generous space; nothing cramped.
- Lucide line icons, small and consistent. Numbers with tabular figures and thousands separators.
- Pills for counts and tags, compact segmented switches for choices (never rows of plain links).

## Good pages
- Lead with what matters (the answer, the key numbers, the 3 takeaways), then the detail.
- Pick each chart for its question: trend = Area, parts over time = Bars, ranking = Ranked, item × time = Heat,
  exact values = Table. One idea per card, with a one-line note under its title.
- Controls must really change what they say they change.
- Real data and real words from the task, never placeholder text. Plain, short, confident copy.

## Always
- Works on a phone first (375 px): no sideways scrolling, tap targets 44 px.
- Good contrast in both themes, alt text on images, prints cleanly (Download PDF).
- The page's own top buttons are only Download PDF and light/dark. Sharing is done from the Dex app, never on the page.
