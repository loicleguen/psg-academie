/**
 * clipboardService.js
 *
 * Service responsible for calling the backend VEO clipboard parsing endpoint.
 *
 * Backend contract:
 *   POST /parse-veo-clipboard
 *   Body: { text: string, club_prefix: string }
 * Response:
 *   { type: string, data: object }
 *
 * Important:
 * - The endpoint is protected (coach/admin), so we MUST send the Bearer token.
 * - This service is a thin wrapper: no mapping/transformation is performed here.
 */

import axios from "axios";

/**
 * Tactical API client (same pattern as veoService.js).
 * If you later extract a shared tacticalApi instance, import it here instead.
 */
const tacticalApi = axios.create({
  baseURL: "/api/tactical",
  headers: {
    "Content-Type": "application/json",
  },
});

tacticalApi.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("access_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error),
);

/**
 * Normalize axios error object into a safe message.
 *
 * @param {any} err - Axios error object
 * @returns {{ status: number|null, detail: string }}
 */
function normalizeApiError(err) {
  const detail =
    err?.response?.data?.detail || err?.response?.data?.message || err?.message || "Unknown error";

  const status = err?.response?.status ?? null;

  return { status, detail };
}

/**
 * Parse raw VEO clipboard text using backend parsers.
 *
 * @param {Object} params
 * @param {string} params.text - Raw text pasted from VEO
 * @param {string} [params.clubPrefix="TEG"] - Club prefix used to detect the club team
 *        inside the "Statistiques" menu.
 *
 * @returns {Promise<{ type: string, data: any }>}
 *
 * @throws {Error} When validation fails or backend returns an error.
 */
async function parseVeoClipboard({ text, clubPrefix = "TEG", menuType }) {
  const safeText = String(text ?? "").trim();
  const safePrefix = String(clubPrefix ?? "TEG").trim();

  if (safeText.length < 10) {
    throw new Error("Le texte collé est trop court (min 10 caractères).");
  }

  if (safePrefix.length < 2) {
    throw new Error("Le préfixe club doit contenir au moins 2 caractères.");
  }

  try {
    const payload = {
      text: safeText,
      club_prefix: safePrefix,
      menu_type: menuType,
    };

    // Because tacticalApi.baseURL = "/api/tactical"
    // this becomes POST /api/tactical/parse-veo-clipboard
    const response = await tacticalApi.post("/parse-veo-clipboard", payload);

    const parsed = response?.data ?? {};

    if (!parsed.type || parsed.data === undefined) {
      throw new Error("Réponse backend inattendue (type/data manquants).");
    }

    return parsed;
  } catch (err) {
    const apiErr = normalizeApiError(err);
    throw new Error(apiErr.detail);
  }
}

export const clipboardService = {
  parseVeoClipboard,
};
