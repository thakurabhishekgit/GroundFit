/** Persist Align-page LaTeX only after the user pastes/edits it. No shared default resume. */

export const LATEX_STORAGE_KEY = "groundfit_latex_source";
export const LATEX_VERSION_KEY = "groundfit_latex_version";
/** Bump to clear old shipped personal resumes from browsers. */
export const LATEX_STORAGE_VERSION = "3";

export function loadStoredLatex(): string {
  try {
    const version = localStorage.getItem(LATEX_VERSION_KEY);
    if (version !== LATEX_STORAGE_VERSION) {
      // Drop previously seeded personal/default LaTeX
      localStorage.removeItem(LATEX_STORAGE_KEY);
      localStorage.setItem(LATEX_VERSION_KEY, LATEX_STORAGE_VERSION);
      return "";
    }
    return localStorage.getItem(LATEX_STORAGE_KEY) || "";
  } catch {
    return "";
  }
}

export function saveStoredLatex(latex: string): void {
  try {
    if (!latex.trim()) {
      localStorage.removeItem(LATEX_STORAGE_KEY);
    } else {
      localStorage.setItem(LATEX_STORAGE_KEY, latex);
    }
    localStorage.setItem(LATEX_VERSION_KEY, LATEX_STORAGE_VERSION);
  } catch {
    /* ignore quota */
  }
}
