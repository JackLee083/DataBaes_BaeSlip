import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const css = readFileSync(resolve("src/styles/index.css"), "utf8");

function readToken(name) {
  const match = css.match(new RegExp(`--${name}\\s*:\\s*(#[0-9a-fA-F]{6})\\s*;`));
  expect(match, `Missing or unreadable CSS token --${name}`).not.toBeNull();
  return match[1];
}

function luminance(hex) {
  const channels = hex.match(/[0-9a-f]{2}/gi).map((value) => Number.parseInt(value, 16) / 255);
  const [red, green, blue] = channels.map((value) =>
    value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4,
  );
  return 0.2126 * red + 0.7152 * green + 0.0722 * blue;
}

function contrastRatio(foreground, background) {
  const [light, dark] = [luminance(foreground), luminance(background)].sort((a, b) => b - a);
  return (light + 0.05) / (dark + 0.05);
}

describe("tier colour tokens", () => {
  it("all four tier text/background pairs meet 4.5:1 contrast", () => {
    for (const tier of ["a", "b", "c", "d"]) {
      const ratio = contrastRatio(readToken(`tier-${tier}-fg`), readToken(`tier-${tier}-bg`));
      expect(ratio, `Tier ${tier.toUpperCase()} contrast`).toBeGreaterThanOrEqual(4.5);
    }
  });
});

function rule(selector) {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const match = css.match(new RegExp(`(?:^|[},\\s])${escaped}\\s*(?:,[^{]*)?\\{([^}]*)\\}`, "m"));
  expect(match, `Missing CSS rule for ${selector}`).not.toBeNull();
  return match[1];
}

describe("responsive and accessible styling", () => {
  it("wraps long text globally and lets flex/grid children shrink", () => {
    expect(rule("html")).toMatch(/overflow-wrap:\s*anywhere/);
    expect(css).toMatch(/min-width:\s*0/);
  });

  it("has a visible focus outline for links, buttons and inputs", () => {
    expect(css).toMatch(/:focus-visible[^{]*\{[^}]*outline:\s*3px solid/);
    expect(readToken("focus")).toBeTruthy();
    expect(contrastRatio(readToken("focus"), "#ffffff")).toBeGreaterThanOrEqual(3);
  });

  it("makes buttons and controls at least 44px tall", () => {
    expect(css).toMatch(/button[^{]*\{[^}]*min-height:\s*(44px|2\.75rem)/);
    expect(css).toMatch(/input[^{]*\{[^}]*min-height:\s*(44px|2\.75rem)/);
  });

  it("defines tablet, desktop and small-phone breakpoints with a max content width", () => {
    expect(css).toMatch(/@media\s*\(min-width:\s*(48rem|768px)\)/);
    expect(css).toMatch(/@media\s*\(min-width:\s*(64rem|1024px|75rem|1200px)\)/);
    expect(css).toMatch(/@media\s*\(max-width:\s*(22\.5rem|360px|24rem|390px)\)/);
    expect(css).toMatch(/--content-width:\s*\d+rem/);
    expect(rule(".app-page")).toMatch(/width:\s*min\(100%,\s*var\(--content-width\)\)/);
  });

  it("makes the verify status badge prominent and distinguishable beyond colour", () => {
    const badge = rule(".status-badge");
    expect(badge).toMatch(/font-size:\s*clamp\(/);
    expect(badge).toMatch(/padding:/);
    expect(badge).toMatch(/border:/);
    for (const state of ["valid", "expired", "revoked", "not_found", "invalid"]) {
      expect(css, `status-badge--${state}`).toMatch(new RegExp(`\\.status-badge--${state}`));
    }
    // StatusBadge renders its own symbol and text, so CSS must not add a second symbol.
    expect(css).not.toMatch(/\.status-badge[^{]*::(before|after)[^{]*\{[^}]*content:/);
  });

  it("styles the private checks notice distinctly", () => {
    const notice = rule(".private-checks-notice");
    expect(notice).toMatch(/border(-left)?:/);
    expect(notice).toMatch(/background:/);
    expect(notice).toMatch(/font-weight:/);
  });

  it("makes self-reported timeline items visibly different from attested ones", () => {
    const self = rule(".timeline-self-reported");
    expect(self).toMatch(/dashed/);
    expect(self).toMatch(/color:/);
  });

  it("keeps every content panel a normal padded surface, never an error colour", () => {
    // Regression: a rule inserted inside the shared selector list once turned every panel red.
    for (const selector of [
      ".income-timeline", ".check-card", ".verify-summary", ".verify-sources",
      ".verify-issuer", ".share-flow", ".spec-tiers", ".spec-forbidden", ".spec-schema",
    ]) {
      const panel = rule(selector);
      expect(panel, selector).toMatch(/padding:/);
      expect(panel, selector).toMatch(/border:/);
      expect(panel, selector).toMatch(/background:\s*var\(--surface\)/);
      expect(panel, selector).not.toMatch(/#fee2e2|#991b1b/i);
    }
    expect(rule(".status-badge--invalid")).toMatch(/#fee2e2/);
  });
});

function mediaBlock(query) {
  const start = css.indexOf(`@media ${query}`);
  expect(start, `Missing @media ${query}`).toBeGreaterThanOrEqual(0);
  const open = css.indexOf("{", start);
  let depth = 0;
  for (let i = open; i < css.length; i += 1) {
    if (css[i] === "{") depth += 1;
    if (css[i] === "}") depth -= 1;
    if (depth === 0) return css.slice(open + 1, i);
  }
  throw new Error(`Unclosed @media ${query}`);
}

function ruleIn(block, selector) {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const match = block.match(new RegExp(`(?:^|[},\\s])${escaped}\\s*\\{([^}]*)\\}`, "m"));
  expect(match, `Missing rule for ${selector}`).not.toBeNull();
  return match[1];
}

describe("page layout and component styles", () => {
  it("lays out /app in two columns from 64rem with the timeline full width", () => {
    const wide = mediaBlock("(min-width: 64rem)");
    expect(ruleIn(wide, ".app-layout")).toMatch(
      /grid-template-columns:\s*minmax\(0,\s*1fr\)\s+minmax\(0,\s*1fr\)/,
    );
    expect(ruleIn(wide, ".app-timeline")).toMatch(/grid-column:\s*1\s*\/\s*-1/);
    expect(rule(".app-layout")).toMatch(/display:\s*grid/);
  });

  it("styles the income summary as a normal panel with large figures", () => {
    const panel = rule(".income-summary");
    expect(panel).toMatch(/padding:/);
    expect(panel).toMatch(/border:/);
    expect(panel).toMatch(/background:\s*var\(--surface\)/);
    expect(rule(".income-summary [data-money]")).toMatch(/font-size:\s*clamp\(/);
  });

  it("makes the primary action prominent and at least 44px tall", () => {
    const action = rule(".primary-action");
    expect(action).toMatch(/min-height:\s*(44px|2\.75rem)/);
    expect(action).toMatch(/background:/);
    expect(action).toMatch(/font-weight:/);
  });

  it("site nav links are 44px tall and the current page is marked beyond colour", () => {
    expect(rule(".site-nav a")).toMatch(/min-height:\s*(44px|2\.75rem)/);
    expect(rule('.site-nav [aria-current="page"]')).toMatch(/font-weight:|text-decoration:/);
  });

  it("aligns the site nav with the page content column", () => {
    const nav = rule(".site-nav");
    expect(nav).toMatch(/width:\s*min\(100%,\s*var\(--content-width\)\)/);
    expect(nav).toMatch(/margin:\s*0 auto/);
    expect(ruleIn(mediaBlock("(min-width: 48rem)"), ".site-nav")).toMatch(/padding-inline:\s*2rem/);
    expect(ruleIn(mediaBlock("(min-width: 64rem)"), ".site-nav")).toMatch(/padding-inline:\s*2\.5rem/);
  });

  it("gives the income range a full row so it never breaks inside a narrow column", () => {
    expect(rule(".income-summary-figures > div:first-child")).toMatch(/grid-column:\s*1\s*\/\s*-1/);
    expect(ruleIn(mediaBlock("(min-width: 48rem)"), ".income-summary-figures")).toMatch(
      /grid-template-columns:\s*repeat\(2,\s*minmax\(0,\s*1fr\)\)/,
    );
    expect(rule(".income-summary-range")).toMatch(/white-space:\s*nowrap/);
    expect(rule(".income-summary [data-money]")).not.toMatch(/white-space:\s*nowrap/);
  });

  it("month rows are clickable summaries at least 44px tall", () => {
    const summary = rule(".timeline-month-summary");
    expect(summary).toMatch(/cursor:\s*pointer/);
    expect(summary).toMatch(/min-height:\s*(44px|2\.75rem)/);
    // display: flex hides the native disclosure triangle, so the row draws its own open/closed marker.
    expect(css).toMatch(/\.timeline-month-summary::before\s*\{[^}]*content:\s*"\\25B8"/);
    expect(css).toMatch(/\.timeline-month\[open\]\s*>\s*\.timeline-month-summary::before\s*\{[^}]*content:\s*"\\25BE"/);
  });

  it("defines compact tier badges and the tier legend", () => {
    expect(rule(".tier-badge--compact")).toMatch(/font-size:/);
    // .tier-badge is inline-flex, which drops the space between the letter and the short label.
    expect(rule(".tier-badge--compact")).toMatch(/gap:/);
    expect(rule(".tier-legend")).toMatch(/display:\s*grid/);
  });
});
