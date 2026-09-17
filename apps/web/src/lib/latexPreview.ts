/**
 * LaTeX → HTML resume preview (Overleaf-like paper layout, not a full TeX engine).
 */

export function latexToPreviewHtml(latex: string): string {
  if (!latex?.trim()) {
    return `<p class="preview-empty">No aligned LaTeX yet. Run Align, then Finalize.</p>`;
  }

  let text = latex
    .replace(/^[\s\S]*?\\begin\{document\}/i, "")
    .replace(/\\end\{document\}[\s\S]*$/i, "")
    .replace(/%.*$/gm, "");

  // Spacing / punctuation helpers used by academic CV templates
  text = text
    .replace(/\\\\\[.*?\]/g, "\n")
    .replace(/\\vspace\*?\s*\{[^}]*\}/gi, "\n")
    .replace(/\\hspace\*?\s*\{[^}]*\}/gi, " ")
    .replace(/\\;|\\,|\\!|\\quad|\\qquad/g, " ")
    .replace(/\\bullet/g, "•")
    .replace(/\\&/g, "&")
    .replace(/\\_/g, "_")
    .replace(/\\%/g, "%")
    .replace(/\\#/g, "#")
    .replace(/---/g, "—")
    .replace(/--/g, "–")
    .replace(/``/g, '"')
    .replace(/''/g, '"')
    .replace(/\\newline|\\\\/g, "\n")
    .replace(/\\headerfont[a-z0-9]*/gi, "");

  // Centered header block
  text = text.replace(
    /\\begin\{center\}([\s\S]*?)\\end\{center\}/gi,
    (_m, inner) => {
      const cleaned = stripNested(inner);
      return `\n<div class="pv-header">${cleaned}</div>\n`;
    }
  );

  // Links before stripping commands
  text = text.replace(/\\href\{([^}]+)\}\{([^}]*)\}/gi, (_m, url, label) => {
    return `<a href="${escapeAttr(url)}" target="_blank" rel="noreferrer">${escapeHtml(
      stripNested(label)
    )}</a>`;
  });

  // resumeSubheading {role}{loc}{company}{dates}
  text = text.replace(
    /\\resumeSubheading\s*\{([^{}]*)\}\s*\{([^{}]*)\}\s*\{([^{}]*)\}\s*\{([^{}]*)\}/gi,
    (_m, a, b, c, d) =>
      `\n<div class="pv-job"><div class="pv-job-row"><strong>${escapeHtml(a)}</strong><span>${escapeHtml(
        d
      )}</span></div><div class="pv-job-row"><em>${escapeHtml(c)}</em><span>${escapeHtml(
        b
      )}</span></div></div>\n`
  );

  // resumeProject {name}{stack}{date}{...nested links...}
  text = text.replace(
    /\\resumeProject\s*\{([^{}]*)\}\s*\{([^{}]*)\}\s*\{([^{}]*)\}\s*\{[\s\S]*?\n\}/gi,
    (_m, name, stack, date) =>
      `\n<div class="pv-job"><div class="pv-job-row"><strong>${escapeHtml(
        name
      )}</strong><span>${escapeHtml(date)}</span></div><div class="pv-stack">${escapeHtml(
        stack
      )}</div></div>\n`
  );

  // \section{\textbf{Projects}} — nested braces
  text = replaceSections(text);

  text = text.replace(/\\textbf\{([^{}]*)\}/gi, (_m, inner) => `<strong>${escapeHtml(inner)}</strong>`);
  text = text.replace(/\\textit\{([^{}]*)\}/gi, (_m, inner) => `<em>${escapeHtml(inner)}</em>`);
  text = text.replace(/\\textcolor\{[^}]+\}\{([^{}]*)\}/gi, (_m, inner) => escapeHtml(inner));
  text = text.replace(/\{\\LARGE\s*\\textbf\{([^{}]*)\}\}/gi, (_m, inner) => `<h1 class="pv-name">${escapeHtml(inner)}</h1>`);
  text = text.replace(/\\LARGE|\\Large|\\large|\\small|\\footnotesize/gi, "");

  text = text.replace(/\\item\b/gi, "\n• ");

  text = text.replace(
    /\\(?:resumeSubHeadingListStart|resumeSubHeadingListEnd|resumeItemListStart|resumeItemListEnd|resumeHeadingSkillStart|resumeHeadingSkillEnd)\b/gi,
    "\n"
  );
  text = text.replace(/\\begin\{[^}]+\}|\\end\{[^}]+\}/gi, "\n");
  text = text.replace(/\\[a-zA-Z]+@?[a-zA-Z]*\*?/g, " ");
  text = text.replace(/[{}]/g, "");
  text = text.replace(/[ \t]+\n/g, "\n");
  text = text.replace(/\n{3,}/g, "\n\n");

  const lines = text
    .split(/\n+/)
    .map((l) => l.trim())
    .filter(Boolean);

  const htmlParts: string[] = [];
  let listBuf: string[] = [];

  const flushList = () => {
    if (listBuf.length) {
      htmlParts.push(`<ul class="pv-list">${listBuf.join("")}</ul>`);
      listBuf = [];
    }
  };

  for (const line of lines) {
    if (line.startsWith("<div") || line.startsWith("<h1") || line.startsWith("<h2")) {
      flushList();
      htmlParts.push(line);
      continue;
    }
    if (line.startsWith("• ")) {
      listBuf.push(`<li>${line.slice(2)}</li>`);
      continue;
    }
    flushList();
    htmlParts.push(`<p>${line}</p>`);
  }
  flushList();

  return `<div class="pv-paper">${htmlParts.join("\n")}</div>`;
}

function replaceSections(text: string): string {
  const re = /\\section\*?\{/gi;
  let out = "";
  let last = 0;
  let m: RegExpExecArray | null;
  while ((m = re.exec(text)) !== null) {
    out += text.slice(last, m.index);
    const open = m.index + m[0].length - 1;
    const close = closingBraceIndex(text, open);
    if (close < 0) {
      out += m[0];
      last = m.index + m[0].length;
      continue;
    }
    const rawName = text.slice(open + 1, close);
    out += `\n<h2 class="pv-section">${escapeHtml(stripNested(rawName))}</h2>\n`;
    last = close + 1;
    re.lastIndex = last;
  }
  out += text.slice(last);
  return out;
}

function closingBraceIndex(text: string, openAt: number): number {
  let depth = 0;
  for (let i = openAt; i < text.length; i++) {
    const ch = text[i];
    if (ch === "{") depth += 1;
    else if (ch === "}") {
      depth -= 1;
      if (depth === 0) return i;
    } else if (ch === "\\" && i + 1 < text.length) {
      i += 1;
    }
  }
  return -1;
}

function stripNested(s: string): string {
  return s
    .replace(/\\[a-zA-Z]+\*?/g, "")
    .replace(/[{}]/g, "")
    .replace(/\\\\\[.*?\]/g, "")
    .replace(/\\;/g, " ")
    .trim();
}

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function escapeAttr(s: string): string {
  return escapeHtml(s).replace(/'/g, "&#39;");
}
