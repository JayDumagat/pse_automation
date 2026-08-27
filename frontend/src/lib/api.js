import axios from "axios";

// In Docker production, nginx proxies /api to the backend so the browser can
// use the same origin. Keep the env override for local CRA development.
export const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || window.location.origin;
export const API = `${BACKEND_URL}/api`;

export const api = axios.create({ baseURL: API });

export const fmtNum = (v, dp = 2) =>
  v === null || v === undefined
    ? "—"
    : Number(v).toLocaleString("en-PH", { minimumFractionDigits: dp, maximumFractionDigits: dp });

export const fmtSigned = (v, dp = 2) => {
  if (v === null || v === undefined) return "—";
  const s = fmtNum(Math.abs(v), dp);
  return `${v >= 0 ? "+" : "-"}${s}`;
};

export const pesoShort = (v) => {
  if (v === null || v === undefined) return "—";
  if (v >= 1e9) return `₱${(v / 1e9).toFixed(2)}B`;
  if (v >= 1e6) return `₱${(v / 1e6).toFixed(1)}M`;
  if (v >= 1e3) return `₱${(v / 1e3).toFixed(1)}K`;
  return `₱${fmtNum(v, 0)}`;
};

export const timeAgo = (iso) => {
  if (!iso) return "";
  const secs = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  if (secs < 60) return `${Math.floor(secs)}s ago`;
  if (secs < 3600) return `${Math.floor(secs / 60)}m ago`;
  if (secs < 86400) return `${Math.floor(secs / 3600)}h ago`;
  return `${Math.floor(secs / 86400)}d ago`;
};

export const fmtDateTime = (iso) => {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString("en-PH", {
      month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
    });
  } catch {
    return iso;
  }
};

export const fmtLongDate = (isoDate) => {
  if (!isoDate) return "—";
  try {
    return new Date(`${isoDate}T00:00:00`).toLocaleDateString("en-PH", {
      weekday: "long", year: "numeric", month: "long", day: "numeric",
    });
  } catch {
    return isoDate;
  }
};

export const GRAPHIC_LABELS = {
  "big-move": "The Big Move",
  "market-drivers": "What Moved the Market",
  "whats-next": "What's Next",
};

export const PLATFORM_LABELS = {
  instagram: "Instagram",
  facebook: "Facebook",
  linkedin: "LinkedIn",
  x: "X (Twitter)",
};
