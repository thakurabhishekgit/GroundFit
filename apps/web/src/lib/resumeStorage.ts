/** Persist Align-page LaTeX source across refreshes. */
import defaultResume from "../data/defaultResume.tex?raw";

export const LATEX_STORAGE_KEY = "groundfit_latex_source";
export const LATEX_VERSION_KEY = "groundfit_latex_version";
/** Bump when the shipped default resume changes so stale stubs get replaced. */
export const LATEX_STORAGE_VERSION = "2";
export const DEFAULT_LATEX_RESUME = defaultResume;

export function loadStoredLatex(): string {
  try {
    const version = localStorage.getItem(LATEX_VERSION_KEY);
    const saved = localStorage.getItem(LATEX_STORAGE_KEY);
    const looksReal =
      !!saved &&
      saved.includes("Wcontent") &&
      saved.includes("Knowable") &&
      saved.includes("\\documentclass");

    if (version === LATEX_STORAGE_VERSION && looksReal) {
      return saved!;
    }

    // Upgrade from stub / old default once
    localStorage.setItem(LATEX_STORAGE_KEY, DEFAULT_LATEX_RESUME);
    localStorage.setItem(LATEX_VERSION_KEY, LATEX_STORAGE_VERSION);
    return DEFAULT_LATEX_RESUME;
  } catch {
    return DEFAULT_LATEX_RESUME;
  }
}

export function saveStoredLatex(latex: string): void {
  try {
    localStorage.setItem(LATEX_STORAGE_KEY, latex);
    localStorage.setItem(LATEX_VERSION_KEY, LATEX_STORAGE_VERSION);
  } catch {
    /* ignore quota */
  }
}
