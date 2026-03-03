// SessionDetail.jsx
import { useState, useEffect, useMemo, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import { catapultService } from '../services/catapultService';
import { veoService } from '../services/veoService';
import api from '../services/api';
import { ChartBarIcon, DocumentChartBarIcon, UserGroupIcon, ArrowLeftIcon } from '@heroicons/react/24/outline';

const UNIT_LABELS = {
  count: '',
  '%': '%',
  minutes: 'min',
  seconds: 'sec',
};

const METRIC_LABELS = {
  team_possession_minutes: 'Possession (minutes)',
  team_possession_pct: 'Possession',
  team_possession_third_att_pct: 'Possession tiers offensif',
  team_possession_third_def_pct: 'Possession tiers defensif',
  team_possession_third_mid_pct: 'Possession tiers milieu',
  team_possession_won: 'Possessions gagnees',
  team_longest_sequence: 'Sequence la plus longue',
  team_passes_completed: 'Passes reussies',
  team_pass_zone_att_pct: 'Passes en zone offensive',
  team_pass_zone_mid_pct: 'Passes en zone milieu',
  team_pass_zone_def_pct: 'Passes en zone defensive',
  team_sequences_3_5: 'Sequences 3-5 passes',
  team_sequences_6_plus: 'Sequences 6+ passes',
  team_corners: 'Corners',
  team_free_kicks: 'Coups francs',
  team_throw_ins: 'Touches',
  team_goals_scored: 'Buts marques',
  team_goals_conceded: 'Buts encaisses',
  team_shots: 'Tirs',
  team_shots_conceded: 'Tirs encaisses',
};

const PLAYER_METRIC_LABELS = {
  player_goal_assists: 'Passes decisives',
  player_shots: 'Tirs',
  player_shots_on_target: 'Tirs cadres',
  player_goals: 'Buts',
  player_duels_won: 'Duels gagnes',
  player_fouls_committed: 'Fautes',
  player_cards: 'Cartons',
  player_offsides: 'Hors-jeu',
  player_dribbles_won: 'Dribbles reussis',
  player_tackles_won: 'Tacles reussis',
  player_recoveries: 'Recuperations',
  player_ball_losses: 'Pertes de balle',
};

const KPI_COMPARISON_ROWS = [
  { label: 'Buts', ownSlug: 'team_goals_scored', opponentSlug: 'team_goals_conceded' },
  { label: 'Tirs', ownSlug: 'team_shots', opponentSlug: 'team_shots_conceded' },
  { label: 'Possession', ownSlug: 'team_possession_pct', opponentFromOwnPct: true, unit: '%' },
  { label: 'Passes reussies', ownSlug: 'team_passes_completed' },
  { label: 'Corners', ownSlug: 'team_corners' },
  { label: 'Coups francs', ownSlug: 'team_free_kicks' },
  { label: 'Touches', ownSlug: 'team_throw_ins' },
];

const OPPONENT_ALIAS_BY_OWN_SLUG = {
  team_goals_scored: 'team_goals_conceded',
  team_shots: 'team_shots_conceded',
};

const OWN_SLUG_BY_OPPONENT_ALIAS = Object.fromEntries(
  Object.entries(OPPONENT_ALIAS_BY_OWN_SLUG).map(([ownSlug, oppSlug]) => [oppSlug, ownSlug])
);

const HIDDEN_VEO_TEAM_METRIC_SLUGS = new Set(['team_goal_kicks']);
const CLUB_LOGO_PATH = '/club_logo.png';

const KPI_TONE_CLASSES = {
  good: {
    card: 'border-emerald-400/40 bg-emerald-500/10',
    label: 'text-emerald-200',
    value: 'text-emerald-100',
  },
  medium: {
    card: 'border-blue-400/40 bg-blue-500/10',
    label: 'text-blue-200',
    value: 'text-blue-100',
  },
  warning: {
    card: 'border-orange-400/40 bg-orange-500/10',
    label: 'text-orange-200',
    value: 'text-orange-100',
  },
  danger: {
    card: 'border-rose-400/40 bg-rose-500/10',
    label: 'text-rose-200',
    value: 'text-rose-100',
  },
  neutral: {
    card: 'border-slate-600 bg-[#223146]',
    label: 'text-slate-400',
    value: 'text-white',
  },
};

function normalizeNumeric(value) {
  if (value === null || value === undefined) {
    return null;
  }
  const numeric = Number(value);
  return Number.isNaN(numeric) ? null : numeric;
}

function getPerformanceTone(metricKey, rawValue) {
  const value = normalizeNumeric(rawValue);
  if (value === null) {
    return 'neutral';
  }

  if (metricKey === 'team_possession_pct') {
    if (value >= 55) return 'good';
    if (value >= 50) return 'medium';
    if (value >= 45) return 'warning';
    return 'danger';
  }

  if (metricKey === 'team_passes_completed') {
    if (value >= 320) return 'good';
    if (value >= 260) return 'medium';
    if (value >= 200) return 'warning';
    return 'danger';
  }

  if (metricKey === 'team_shots') {
    if (value >= 10) return 'good';
    if (value >= 7) return 'medium';
    if (value >= 4) return 'warning';
    return 'danger';
  }

  if (metricKey === 'team_goals_scored') {
    if (value >= 2) return 'good';
    if (value >= 1) return 'medium';
    return 'danger';
  }

  if (metricKey === 'team_corners') {
    if (value >= 6) return 'good';
    if (value >= 4) return 'medium';
    if (value >= 2) return 'warning';
    return 'danger';
  }

  if (metricKey === 'global_score') {
    if (value >= 8) return 'good';
    if (value >= 6) return 'medium';
    if (value >= 4) return 'warning';
    return 'danger';
  }

  return 'neutral';
}

function clampScore(value) {
  return Math.max(0, Math.min(10, Math.round(value)));
}

function formatMetricLabel(metric) {
  return METRIC_LABELS[metric.metric_slug] || metric.metric_label;
}

function formatPlayerMetricLabel(column) {
  return PLAYER_METRIC_LABELS[column.slug] || column.label;
}

function formatMetricValue(value, unit) {
  if (value === null || value === undefined) {
    return '-';
  }
  const numericValue = Number(value);
  const displayValue = Number.isInteger(numericValue) ? String(numericValue) : numericValue.toFixed(1);
  const displayUnit = UNIT_LABELS[unit] ?? unit ?? '';
  return displayUnit ? `${displayValue} ${displayUnit}` : displayValue;
}

function makeTeamTag(name, fallback = 'TEAM') {
  const cleaned = String(name || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^A-Za-z0-9\s]/g, ' ')
    .trim();

  if (!cleaned) {
    return fallback;
  }

  const tokens = cleaned.split(/\s+/).filter(Boolean);
  if (tokens.length >= 2) {
    return `${tokens[0][0] || ''}${tokens[1][0] || ''}${tokens[2]?.[0] || ''}`.toUpperCase();
  }
  return cleaned.slice(0, 3).toUpperCase();
}

function sanitizeFilename(value) {
  return (value || 'rapport-veo')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-zA-Z0-9-_]+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '')
    .toLowerCase();
}

function escapeSvg(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function wrapText(text, maxChars = 56) {
  const words = String(text || '').split(/\s+/).filter(Boolean);
  if (words.length === 0) {
    return [''];
  }

  const lines = [];
  let current = words[0];
  for (let i = 1; i < words.length; i += 1) {
    const next = `${current} ${words[i]}`;
    if (next.length > maxChars) {
      lines.push(current);
      current = words[i];
    } else {
      current = next;
    }
  }
  lines.push(current);
  return lines;
}

function csvCell(value) {
  const raw = value === null || value === undefined ? '' : String(value);
  const escaped = raw.replace(/"/g, '""');
  if (/[;"\n]/.test(escaped)) {
    return `"${escaped}"`;
  }
  return escaped;
}

function toCsvString(rows) {
  return rows.map((row) => row.map((cell) => csvCell(cell)).join(';')).join('\n');
}

function blobToDataUrl(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => resolve(String(reader.result || ''));
    reader.onerror = () => reject(new Error('Unable to convert blob to data URL.'));
    reader.readAsDataURL(blob);
  });
}

function syncFormValuesForClone(sourceRoot, cloneRoot) {
  const sourceFields = sourceRoot.querySelectorAll('textarea, input, select');
  const clonedFields = cloneRoot.querySelectorAll('textarea, input, select');

  sourceFields.forEach((sourceField, index) => {
    const clonedField = clonedFields[index];
    if (!clonedField) {
      return;
    }

    if (sourceField instanceof HTMLTextAreaElement && clonedField instanceof HTMLTextAreaElement) {
      clonedField.textContent = sourceField.value;
      return;
    }

    if (sourceField instanceof HTMLInputElement && clonedField instanceof HTMLInputElement) {
      clonedField.setAttribute('value', sourceField.value);
      if (sourceField.checked) {
        clonedField.setAttribute('checked', 'checked');
      } else {
        clonedField.removeAttribute('checked');
      }
      return;
    }

    if (sourceField instanceof HTMLSelectElement && clonedField instanceof HTMLSelectElement) {
      Array.from(sourceField.options).forEach((option, optionIndex) => {
        const clonedOption = clonedField.options[optionIndex];
        if (clonedOption) {
          clonedOption.selected = option.selected;
        }
      });
    }
  });
}

function collectDocumentCssText() {
  let cssText = '';

  Array.from(document.styleSheets).forEach((styleSheet) => {
    try {
      const rules = styleSheet.cssRules;
      if (!rules) {
        return;
      }

      Array.from(rules).forEach((rule) => {
        cssText += `${rule.cssText}\n`;
      });
    } catch {
      // Ignore cross-origin stylesheets that cannot be inspected.
    }
  });

  return cssText;
}

function escapeStyleTagContent(cssText) {
  return String(cssText || '').replace(/<\/style/gi, '<\\/style');
}

async function inlineImageSources(rootElement) {
  const images = Array.from(rootElement.querySelectorAll('img'));

  await Promise.all(
    images.map(async (image) => {
      const source = image.getAttribute('src');
      if (!source || source.startsWith('data:')) {
        return;
      }

      try {
        const absoluteUrl = new URL(source, window.location.href).href;
        const response = await fetch(absoluteUrl);
        if (!response.ok) {
          return;
        }

        const blob = await response.blob();
        const dataUrl = await blobToDataUrl(blob);
        image.setAttribute('src', dataUrl);
        image.removeAttribute('srcset');
      } catch (error) {
        console.warn('Image not embedded in exported report:', source, error);
      }
    })
  );
}

async function downloadElementAsPng(element, fileName) {
  if (!element) {
    return false;
  }

  const width = Math.ceil(element.scrollWidth || element.clientWidth);
  const height = Math.ceil(element.scrollHeight || element.clientHeight);
  if (width <= 0 || height <= 0) {
    return false;
  }

  const clonedElement = element.cloneNode(true);
  if (!(clonedElement instanceof HTMLElement)) {
    return false;
  }
  clonedElement.style.width = `${width}px`;
  syncFormValuesForClone(element, clonedElement);

  await inlineImageSources(clonedElement);

  const serializedNode = new XMLSerializer().serializeToString(clonedElement);
  const cssText = collectDocumentCssText();
  const foreignObjectHtml = `<div xmlns="http://www.w3.org/1999/xhtml" style="width:${width}px;height:${height}px;">${serializedNode}</div>`;
  const svgMarkup = `
    <svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">
      <foreignObject x="0" y="0" width="100%" height="100%">
        <div xmlns="http://www.w3.org/1999/xhtml" style="width:${width}px;height:${height}px;overflow:hidden;">
          <style>${escapeStyleTagContent(cssText)}</style>
          ${foreignObjectHtml}
        </div>
      </foreignObject>
    </svg>
  `;

  const svgBlob = new Blob([svgMarkup], { type: 'image/svg+xml;charset=utf-8' });
  const svgUrl = URL.createObjectURL(svgBlob);

  try {
    const image = await new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = () => resolve(img);
      img.onerror = reject;
      img.src = svgUrl;
    });

    const scaleCap = Math.min(2, 2600 / Math.max(width, height));
    const scale = Math.max(1, scaleCap);
    const canvas = document.createElement('canvas');
    canvas.width = Math.max(1, Math.round(width * scale));
    canvas.height = Math.max(1, Math.round(height * scale));

    const context = canvas.getContext('2d');
    if (!context) {
      return false;
    }

    context.scale(scale, scale);
    context.drawImage(image, 0, 0, width, height);

    const pngBlob = await new Promise((resolve) => {
      canvas.toBlob((blob) => resolve(blob), 'image/png');
    });

    if (!pngBlob) {
      return false;
    }

    const pngUrl = URL.createObjectURL(pngBlob);
    const link = document.createElement('a');
    link.href = pngUrl;
    link.download = fileName;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(pngUrl);
    return true;
  } catch (error) {
    console.error('Unable to export rendered report to PNG.', error);
    return false;
  } finally {
    URL.revokeObjectURL(svgUrl);
  }
}

function BUILD_VEO_REPORT_SVG({
  title,
  dateLabel,
  opponent,
  scoreLabel,
  matchType,
  teamName,
  globalScoreLabel,
  qualityTeamLabel,
  qualityPlayerLabel,
  kpis,
  comparisonRows,
  comparisonChartData,
  territoryRows,
  passZoneRows,
  analysisSections,
  recommendations,
  logoDataUrl = '',
}) {
  const width = 1600;
  const height = 2280;
  const chartLeft = 70;
  const chartWidth = width - chartLeft * 2;

  const kpiCardWidth = 235;
  const kpiGap = 16;
  const kpiStartY = 300;
  const qualityStartY = 450;
  const graphStartY = 620;
  const graphCardHeight = 340;
  const comparisonStartY = graphStartY + graphCardHeight + 24;
  const comparisonRowHeight = 44;
  const comparisonRowsVisible = comparisonRows.slice(0, 8);
  const comparisonTableHeight = 52 + comparisonRowsVisible.length * comparisonRowHeight;
  const analysisStartY = comparisonStartY + comparisonTableHeight + 28;
  const analysisCardHeight = 210;
  const analysisCardGap = 20;
  const recommendationsStartY = analysisStartY + analysisCardHeight * 2 + analysisCardGap + 20;
  const footerY = height - 40;

  const kpiSvg = kpis
    .map((kpi, index) => {
      const x = chartLeft + index * (kpiCardWidth + kpiGap);
      return `
      <rect x="${x}" y="${kpiStartY}" width="${kpiCardWidth}" height="120" rx="14" fill="#243247" />
      <text x="${x + 20}" y="${kpiStartY + 38}" fill="#94a3b8" font-size="18" font-family="Arial, sans-serif">${escapeSvg(
        kpi.label
      )}</text>
      <text x="${x + 20}" y="${kpiStartY + 88}" fill="#f8fafc" font-size="40" font-weight="700" font-family="Arial, sans-serif">${escapeSvg(
        kpi.value
      )}</text>
    `;
    })
    .join('');

  const comparisonGraphSvg = (comparisonChartData || [])
    .slice(0, 6)
    .map((row, idx) => {
      const y = graphStartY + 94 + idx * 30;
      const ownWidth = Math.round((220 * row.ownValue) / row.maxValue);
      const oppWidth = Math.round((220 * row.opponentValue) / row.maxValue);
      const unit = row.unit && row.unit !== 'count' ? ` ${row.unit}` : '';
      return `
      <text x="${chartLeft + 28}" y="${y}" fill="#cbd5e1" font-size="16" font-family="Arial, sans-serif">${escapeSvg(
        row.label
      )}</text>
      <rect x="${chartLeft + 200}" y="${y - 14}" width="220" height="12" rx="6" fill="#334155" />
      <rect x="${chartLeft + 200}" y="${y - 14}" width="${ownWidth}" height="12" rx="6" fill="#60a5fa" />
      <text x="${chartLeft + 430}" y="${y - 2}" fill="#e2e8f0" font-size="14" font-family="Arial, sans-serif">${escapeSvg(
        `${row.ownValue}${unit}`
      )}</text>

      <rect x="${chartLeft + 520}" y="${y - 14}" width="220" height="12" rx="6" fill="#334155" />
      <rect x="${chartLeft + 520}" y="${y - 14}" width="${oppWidth}" height="12" rx="6" fill="#f97316" />
      <text x="${chartLeft + 750}" y="${y - 2}" fill="#e2e8f0" font-size="14" font-family="Arial, sans-serif">${escapeSvg(
        `${row.opponentValue}${unit}`
      )}</text>
    `;
    })
    .join('');

  const territoryPitchSvg = (territoryRows || [])
    .slice(0, 3)
    .map((row, idx) => {
      const x = chartLeft + 840 + idx * 198;
      const isMiddle = idx === 1;
      return `
      <rect x="${x}" y="${graphStartY + 98}" width="186" height="122" rx="10" fill="${
        isMiddle ? '#2f3f56' : '#223146'
      }" />
      <circle cx="${x + 93}" cy="${graphStartY + 146}" r="28" fill="#334155" />
      <text x="${x + 93}" y="${graphStartY + 152}" text-anchor="middle" fill="#f8fafc" font-size="18" font-weight="700" font-family="Arial, sans-serif">${escapeSvg(
        `${row.ownPct}%`
      )}</text>
      <text x="${x + 93}" y="${graphStartY + 202}" text-anchor="middle" fill="#cbd5e1" font-size="13" font-family="Arial, sans-serif">${escapeSvg(
        row.label.replace('Tiers ', '')
      )}</text>
      <text x="${x + 93}" y="${graphStartY + 218}" text-anchor="middle" fill="#94a3b8" font-size="12" font-family="Arial, sans-serif">${escapeSvg(
        `Adv ${row.oppPct}%`
      )}</text>
    `;
    })
    .join('');

  const passZoneSvg = (passZoneRows || [])
    .slice(0, 3)
    .map((row, idx) => {
      const y = graphStartY + 278 + idx * 24;
      const ownWidth = Math.max(0, Math.min(120, Math.round((120 * row.ownPct) / 100)));
      const oppWidth = Math.max(0, Math.min(120, Math.round((120 * row.oppPct) / 100)));
      return `
      <text x="${chartLeft + 840}" y="${y}" fill="#cbd5e1" font-size="12" font-family="Arial, sans-serif">${escapeSvg(
        row.label.replace('Zone ', '')
      )}</text>
      <rect x="${chartLeft + 940}" y="${y - 10}" width="120" height="8" rx="4" fill="#334155" />
      <rect x="${chartLeft + 940}" y="${y - 10}" width="${ownWidth}" height="8" rx="4" fill="#60a5fa" />
      <text x="${chartLeft + 1066}" y="${y - 2}" fill="#e2e8f0" font-size="11" font-family="Arial, sans-serif">${escapeSvg(
        `${row.ownPct}%`
      )}</text>

      <rect x="${chartLeft + 1102}" y="${y - 10}" width="120" height="8" rx="4" fill="#334155" />
      <rect x="${chartLeft + 1102}" y="${y - 10}" width="${oppWidth}" height="8" rx="4" fill="#f97316" />
      <text x="${chartLeft + 1228}" y="${y - 2}" fill="#e2e8f0" font-size="11" font-family="Arial, sans-serif">${escapeSvg(
        `${row.oppPct}%`
      )}</text>
    `;
    })
    .join('');

  const comparisonSvg = comparisonRowsVisible
    .map((row, idx) => {
      const y = comparisonStartY + 54 + (idx + 1) * comparisonRowHeight;
      const isEven = idx % 2 === 0;
      return `
      <rect x="${chartLeft + 2}" y="${y - 30}" width="${chartWidth - 4}" height="${comparisonRowHeight}" fill="${
        isEven ? '#1f2b3f' : '#1a2434'
      }" />
      <text x="${chartLeft + 24}" y="${y}" fill="#e2e8f0" font-size="18" font-family="Arial, sans-serif">${escapeSvg(
        row.label
      )}</text>
      <text x="${chartLeft + 780}" y="${y}" fill="#f8fafc" font-size="18" text-anchor="middle" font-family="Arial, sans-serif">${escapeSvg(
        row.ownDisplay
      )}</text>
      <text x="${chartLeft + 1155}" y="${y}" fill="#f8fafc" font-size="18" text-anchor="middle" font-family="Arial, sans-serif">${escapeSvg(
        row.opponentDisplay
      )}</text>
    `;
    })
    .join('');

  const analysisCards = analysisSections
    .slice(0, 4)
    .map((section, idx) => {
      const col = idx % 2;
      const row = Math.floor(idx / 2);
      const x = chartLeft + col * (chartWidth / 2 + 10);
      const y = analysisStartY + row * (analysisCardHeight + analysisCardGap);
      const cardWidth = chartWidth / 2 - 10;
      const bulletLines = section.bullets.flatMap((bullet) => wrapText(`• ${bullet}`, 62)).slice(0, 5);
      const bulletsSvg = bulletLines
        .map(
          (line, lineIdx) => `
        <text x="${x + 24}" y="${y + 92 + lineIdx * 30}" fill="#cbd5e1" font-size="17" font-family="Arial, sans-serif">${escapeSvg(
            line
          )}</text>
      `
        )
        .join('');

      return `
      <rect x="${x}" y="${y}" width="${cardWidth}" height="${analysisCardHeight}" rx="14" fill="#243247" />
      <text x="${x + 24}" y="${y + 40}" fill="#f8fafc" font-size="24" font-weight="700" font-family="Arial, sans-serif">${escapeSvg(
        section.title
      )}</text>
      <text x="${x + cardWidth - 24}" y="${y + 40}" text-anchor="end" fill="#60a5fa" font-size="24" font-weight="700" font-family="Arial, sans-serif">${escapeSvg(
        `${section.score}/10`
      )}</text>
      ${bulletsSvg}
    `;
    })
    .join('');

  const recommendationLines = recommendations
    .flatMap((item) => wrapText(`• ${item}`, 122))
    .slice(0, 8)
    .map(
      (line, idx) => `
    <text x="${chartLeft + 24}" y="${recommendationsStartY + 74 + idx * 30}" fill="#e2e8f0" font-size="18" font-family="Arial, sans-serif">${escapeSvg(
        line
      )}</text>
  `
    )
    .join('');

  return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">
  <rect width="100%" height="100%" fill="#1a2332" />

  <rect x="${chartLeft}" y="70" width="${chartWidth}" height="180" fill="#ffffff" rx="8" />
  ${logoDataUrl ? `<image href="${logoDataUrl}" x="${chartLeft + 16}" y="82" width="170" height="160" />` : ''}
  <text x="${chartLeft + 210}" y="130" fill="#0f172a" font-size="50" font-weight="700" font-family="Arial, sans-serif">RAPPORT VEO</text>
  <text x="${chartLeft + 210}" y="178" fill="#475569" font-size="24" font-family="Arial, sans-serif">${escapeSvg(
    title
  )}</text>
  <text x="${chartLeft + 210}" y="214" fill="#64748b" font-size="22" font-family="Arial, sans-serif">${escapeSvg(
    `${dateLabel} • ${scoreLabel}`
  )}</text>
  <text x="${chartLeft + 970}" y="126" fill="#64748b" font-size="20" font-family="Arial, sans-serif">EQUIPE</text>
  <text x="${chartLeft + 970}" y="162" fill="#0f172a" font-size="28" font-weight="700" font-family="Arial, sans-serif">${escapeSvg(
    teamName
  )}</text>
  <text x="${chartLeft + 970}" y="198" fill="#64748b" font-size="20" font-family="Arial, sans-serif">${escapeSvg(
    `${matchType} vs ${opponent}`
  )}</text>

  ${kpiSvg}

  <rect x="${chartLeft}" y="${qualityStartY}" width="${chartWidth}" height="150" rx="14" fill="#243247" />
  <text x="${chartLeft + 24}" y="${qualityStartY + 50}" fill="#f8fafc" font-size="28" font-weight="700" font-family="Arial, sans-serif">Score global plan de jeu: ${escapeSvg(
    globalScoreLabel
  )}</text>
  <text x="${chartLeft + 24}" y="${qualityStartY + 95}" fill="#cbd5e1" font-size="20" font-family="Arial, sans-serif">${escapeSvg(
    qualityTeamLabel
  )}</text>
  <text x="${chartLeft + 24}" y="${qualityStartY + 128}" fill="#cbd5e1" font-size="20" font-family="Arial, sans-serif">${escapeSvg(
    qualityPlayerLabel
  )}</text>

  <rect x="${chartLeft}" y="${graphStartY}" width="${chartWidth}" height="${graphCardHeight}" rx="14" fill="#243247" />
  <text x="${chartLeft + 24}" y="${graphStartY + 40}" fill="#f8fafc" font-size="26" font-weight="700" font-family="Arial, sans-serif">Graphiques VEO</text>
  <text x="${chartLeft + 24}" y="${graphStartY + 66}" fill="#93c5fd" font-size="16" font-family="Arial, sans-serif">Comparatif visuel des indicateurs</text>
  ${comparisonGraphSvg}
  <text x="${chartLeft + 840}" y="${graphStartY + 66}" fill="#93c5fd" font-size="16" font-family="Arial, sans-serif">Carte de possession (tiers)</text>
  <rect x="${chartLeft + 840}" y="${graphStartY + 98}" width="592" height="122" rx="10" fill="#1e293b" />
  ${territoryPitchSvg}
  <text x="${chartLeft + 840}" y="${graphStartY + 258}" fill="#93c5fd" font-size="14" font-family="Arial, sans-serif">Zones de passes (nous vs adv)</text>
  <text x="${chartLeft + 992}" y="${graphStartY + 258}" fill="#93c5fd" font-size="12" font-family="Arial, sans-serif">Nous</text>
  <text x="${chartLeft + 1155}" y="${graphStartY + 258}" fill="#93c5fd" font-size="12" font-family="Arial, sans-serif">Adv</text>
  ${passZoneSvg}

  <rect x="${chartLeft}" y="${comparisonStartY}" width="${chartWidth}" height="${comparisonTableHeight}" rx="14" fill="#243247" />
  <text x="${chartLeft + 24}" y="${comparisonStartY + 40}" fill="#f8fafc" font-size="26" font-weight="700" font-family="Arial, sans-serif">Comparatif equipe vs adversaire</text>
  <text x="${chartLeft + 24}" y="${comparisonStartY + 90}" fill="#93c5fd" font-size="18" font-family="Arial, sans-serif">Indicateur</text>
  <text x="${chartLeft + 780}" y="${comparisonStartY + 90}" text-anchor="middle" fill="#93c5fd" font-size="18" font-family="Arial, sans-serif">Notre equipe</text>
  <text x="${chartLeft + 1155}" y="${comparisonStartY + 90}" text-anchor="middle" fill="#93c5fd" font-size="18" font-family="Arial, sans-serif">Adversaire</text>
  ${comparisonSvg}

  ${analysisCards}

  <rect x="${chartLeft}" y="${recommendationsStartY}" width="${chartWidth}" height="300" rx="14" fill="#243247" />
  <text x="${chartLeft + 24}" y="${recommendationsStartY + 40}" fill="#f8fafc" font-size="26" font-weight="700" font-family="Arial, sans-serif">Recommandations coach</text>
  ${recommendationLines}

  <text x="${chartLeft}" y="${footerY}" fill="#94a3b8" font-size="18" font-family="Arial, sans-serif">Genere depuis PSG Academie - Rapport VEO centralise</text>
</svg>`;
}

export default function SessionDetail() {
  const { sessionId } = useParams();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [reportImage, setReportImage] = useState(null);
  const [showReport, setShowReport] = useState(false);
  const [showVeoReport, setShowVeoReport] = useState(false);
  const [veoReportMode, setVeoReportMode] = useState('GRAPH');
  const [weeklyReportUrl, setWeeklyReportUrl] = useState(null);
  const [showWeeklyReport, setShowWeeklyReport] = useState(false);
  const [individualReportUrl, setIndividualReportUrl] = useState(null);
  const [showIndividualReport, setShowIndividualReport] = useState(false);
  const [availablePlayers, setAvailablePlayers] = useState([]);
  const [selectedPlayer, setSelectedPlayer] = useState('');
  const [sessionInfo, setSessionInfo] = useState(null);
  const [, _setLoadingSessionInfo] = useState(true);
  const [selectedVeoMatchId, setSelectedVeoMatchId] = useState('');
  const [veoSummary, setVeoSummary] = useState(null);
  const [loadingVeoSummary, setLoadingVeoSummary] = useState(false);
  const [veoEntrySchema, setVeoEntrySchema] = useState(null);
  const [coachManualNote, setCoachManualNote] = useState('');
  const [coachNoteSaved, setCoachNoteSaved] = useState(false);
  const [zoneViewSide, setZoneViewSide] = useState('OWN');
  const veoGraphReportRef = useRef(null);

  const sessionTitle = decodeURIComponent(sessionId);
  const sessionDate = sessionInfo?.date ? String(sessionInfo.date).slice(0, 10) : '';

  const getTeamMetric = (summary, metricSlug, side = 'OWN') => {
    if (!summary?.team_metrics?.[side]) {
      return null;
    }
    const metric = summary.team_metrics[side].find((item) => item.metric_slug === metricSlug);
    return metric?.value ?? null;
  };

  // Récupérer les infos de la session pour le rapport hebdo
  useEffect(() => {
    const fetchSessionInfo = async () => {
      try {
        const response = await api.get('/catapult/sessions');
        console.log('All sessions:', response.data);
        console.log('Looking for session:', sessionTitle);
        const session = response.data.find(s => s.session_title === sessionTitle);
        console.log('Found session:', session);
        if (session) {
          setSessionInfo(session);
          console.log('Session info set:', session);
        } else {
          console.warn('Session not found in list');
        }
      } catch (err) {
        console.error('Erreur récupération session:', err);
      }
    };
    fetchSessionInfo();
  }, [sessionTitle]);

  // Récupérer la liste des joueurs de la semaine pour le rapport individuel
  useEffect(() => {
    const fetchWeekPlayers = async () => {
      if (!sessionInfo || !sessionInfo.week || !sessionInfo.year) {
        return;
      }

      try {
        const response = await api.get('/catapult/players-by-week', {
          params: {
            week: sessionInfo.week,
            year: sessionInfo.year
          }
        });
        console.log('Players for week:', response.data);
        setAvailablePlayers(response.data);

        // Présélectionner le premier joueur si disponible
        if (response.data.length > 0) {
          setSelectedPlayer(response.data[0]);
        }
      } catch (err) {
        console.error('Erreur récupération joueurs semaine:', err);
      }
    };

    fetchWeekPlayers();
  }, [sessionInfo]);

  useEffect(() => {
    const fetchVeoEntrySchema = async () => {
      try {
        const schema = await veoService.getEntrySchema(false);
        setVeoEntrySchema(schema);
      } catch (err) {
        console.error('Erreur récupération schéma métriques VEO:', err);
      }
    };

    fetchVeoEntrySchema();
  }, []);

  useEffect(() => {
    const fetchVeoMatches = async () => {
      if (!sessionDate) {
        setSelectedVeoMatchId('');
        setVeoSummary(null);
        return;
      }

      try {
        const matches = await veoService.getMatchesByDate(sessionDate);

        const normalizedTitle = (sessionTitle || '').trim().toLowerCase();
        const matchByTitle = matches.find(
          (match) => (match.veo_title || '').trim().toLowerCase() === normalizedTitle
        );

        if (matchByTitle) {
          setSelectedVeoMatchId(String(matchByTitle.id));
        } else {
          setSelectedVeoMatchId(matches.length > 0 ? String(matches[0].id) : '');
          if (matches.length === 0) {
            setVeoSummary(null);
          }
        }
      } catch (err) {
        setSelectedVeoMatchId('');
        setVeoSummary(null);
        console.error(err);
      }
    };

    fetchVeoMatches();
  }, [sessionDate, sessionTitle]);

  useEffect(() => {
    const fetchVeoSummary = async () => {
      if (!selectedVeoMatchId) {
        setVeoSummary(null);
        return;
      }

      try {
        setLoadingVeoSummary(true);
        const summary = await veoService.getMatchSummary(Number(selectedVeoMatchId));
        setVeoSummary(summary);
      } catch (err) {
        setVeoSummary(null);
        console.error(err);
      } finally {
        setLoadingVeoSummary(false);
      }
    };

    fetchVeoSummary();
  }, [selectedVeoMatchId]);

  useEffect(() => {
    if (!selectedVeoMatchId) {
      setCoachManualNote('');
      setCoachNoteSaved(false);
      setZoneViewSide('OWN');
      return;
    }

    try {
      const stored = window.localStorage.getItem(`veo_coach_note_${selectedVeoMatchId}`);
      setCoachManualNote(stored || '');
    } catch (err) {
      console.error('Impossible de charger la note coach locale:', err);
      setCoachManualNote('');
    }
    setCoachNoteSaved(false);
    setZoneViewSide('OWN');
  }, [selectedVeoMatchId]);


  const handleGenerateSessionReport = async () => {
    try {
      setLoading(true);
      setError('');
      setShowReport(false);
      setShowVeoReport(false);
      setShowWeeklyReport(false);
      setShowIndividualReport(false);

      const data = await catapultService.generateSessionReport(sessionTitle);

      if (data.report_image) {
        setReportImage(`data:image/png;base64,${data.report_image}`);
        setShowReport(true);
        setShowVeoReport(true);
        setVeoReportMode('GRAPH');
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Erreur lors de la génération du rapport');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateWeeklyReport = async () => {
    console.log('sessionInfo:', sessionInfo);
    if (!sessionInfo) {
      setError('Informations de la session manquantes (sessionInfo null)');
      return;
    }
    if (!sessionInfo.team_id) {
      setError('Informations de la session manquantes (team_id manquant)');
      console.error('sessionInfo without team_id:', sessionInfo);
      return;
    }
    if (!sessionInfo.date) {
      setError('Informations de la session manquantes (date manquante)');
      console.error('sessionInfo without date:', sessionInfo);
      return;
    }

    try {
      setLoading(true);
      setError('');
      setShowReport(false);
      setShowVeoReport(false);
      setShowWeeklyReport(false);
      setShowIndividualReport(false);

      // Utiliser directement le numéro de semaine ISO calculé par le backend
      const weekNumber = sessionInfo.week;
      const year = sessionInfo.year;

      console.log('Session date:', sessionInfo.date);
      console.log('Year (from backend):', year);
      console.log('Week number (from backend):', weekNumber);

      if (!weekNumber || !year) {
        setError('Numéro de semaine manquant');
        setLoading(false);
        return;
      }

      // Fetch avec token d'authentification
      const response = await api.get('/catapult/reports/weekly.png', {
        params: {
          team_id: sessionInfo.team_id,
          week: weekNumber,
          year: year
        },
        responseType: 'blob'
      });

      // Créer un object URL à partir du blob
      const imageUrl = URL.createObjectURL(response.data);
      setWeeklyReportUrl(imageUrl);
      setShowWeeklyReport(true);
    } catch (err) {
      setError('Erreur lors de la génération du rapport hebdomadaire');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };


  const handleGenerateIndividualReport = async () => {
    if (!sessionInfo) {
      setError('Informations de la session manquantes');
      return;
    }
    if (!selectedPlayer) {
      setError('Veuillez sélectionner un joueur');
      return;
    }

    try {
      setLoading(true);
      setError('');
      setShowReport(false);
      setShowVeoReport(false);
      setShowWeeklyReport(false);
      setShowIndividualReport(false);

      const weekNumber = sessionInfo.week;
      const year = sessionInfo.year;

      if (!weekNumber || !year) {
        setError('Numéro de semaine manquant');
        setLoading(false);
        return;
      }

      // Fetch avec token d'authentification
      const response = await api.get('/catapult/reports/individual-week.png', {
        params: {
          player_name: selectedPlayer,
          week: weekNumber,
          year: year
        },
        responseType: 'blob'
      });

      // Créer un object URL à partir du blob
      const imageUrl = URL.createObjectURL(response.data);
      setIndividualReportUrl(imageUrl);
      setShowIndividualReport(true);
    } catch (err) {
      setError('Erreur lors de la génération du rapport individuel');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const reportTypes = [
    {
      id: 'session',
      title: 'Rapport de séance',
      description: 'Analyse complète de la session avec graphiques et statistiques des joueurs',
      icon: ChartBarIcon,
      available: true,
      onClick: handleGenerateSessionReport
    },
    {
      id: 'weekly',
      title: 'Rapport Hebdomadaire',
      description: 'Synthèse de la semaine d\'entraînement avec comparaison des sessions',
      icon: DocumentChartBarIcon,
      available: true,
      onClick: handleGenerateWeeklyReport
    },
    {
      id: 'individual',
      title: 'Rapport semaine individuel',
      description: 'Analyse individuelle du joueur sur la semaine',
      icon: UserGroupIcon,
      available: true,
      onClick: handleGenerateIndividualReport
    }
  ];

  const veoPossession = getTeamMetric(veoSummary, 'team_possession_pct', 'OWN');
  const veoPasses = getTeamMetric(veoSummary, 'team_passes_completed', 'OWN');
  const veoShots = getTeamMetric(veoSummary, 'team_shots', 'OWN');
  const veoShotsAgainst = getTeamMetric(veoSummary, 'team_shots_conceded', 'OPPONENT');
  const veoGoals = getTeamMetric(veoSummary, 'team_goals_scored', 'OWN');
  const veoGoalsAgainst = getTeamMetric(veoSummary, 'team_goals_conceded', 'OPPONENT');
  const veoCorners = getTeamMetric(veoSummary, 'team_corners', 'OWN');
  const veoPlayersTracked = veoSummary?.player_metrics?.players?.length ?? 0;
  const ownTeamLabel = sessionInfo?.team_name || sessionInfo?.team || 'TEG';
  const ownTeamTag = makeTeamTag(ownTeamLabel, 'TEG');
  const opponentTeamLabel = veoSummary?.match?.opponent_name || 'Adversaire';
  const opponentTeamTag = makeTeamTag(opponentTeamLabel, 'ADV');
  const veoOwnMetrics = useMemo(
    () =>
      (veoSummary?.team_metrics?.OWN ?? []).filter(
        (metric) => !HIDDEN_VEO_TEAM_METRIC_SLUGS.has(metric.metric_slug)
      ),
    [veoSummary]
  );
  const veoOpponentMetrics = useMemo(
    () =>
      (veoSummary?.team_metrics?.OPPONENT ?? []).filter(
        (metric) => !HIDDEN_VEO_TEAM_METRIC_SLUGS.has(metric.metric_slug)
      ),
    [veoSummary]
  );

  const veoOwnMetricMap = useMemo(
    () => new Map(veoOwnMetrics.map((metric) => [metric.metric_slug, metric])),
    [veoOwnMetrics]
  );
  const veoOpponentMetricMap = useMemo(
    () => new Map(veoOpponentMetrics.map((metric) => [metric.metric_slug, metric])),
    [veoOpponentMetrics]
  );

  const getOwnMetricValue = (slug) => veoOwnMetricMap.get(slug)?.value ?? null;
  const getOpponentMetricValue = (slug) => veoOpponentMetricMap.get(slug)?.value ?? null;

  const veoTeamMetricsFilled = useMemo(() => {
    const keys = new Set();

    veoOwnMetrics.forEach((metric) => {
      keys.add(`${metric.metric_slug}__OWN`);
    });

    veoOpponentMetrics.forEach((metric) => {
      const mappedSlug = OWN_SLUG_BY_OPPONENT_ALIAS[metric.metric_slug] || metric.metric_slug;
      keys.add(`${mappedSlug}__OPPONENT`);
    });

    return keys.size;
  }, [veoOwnMetrics, veoOpponentMetrics]);
  const veoShotConversion =
    veoShots && veoShots > 0 && veoGoals !== null ? (veoGoals / veoShots) * 100 : null;
  const veoShotBalance =
    veoShots !== null && veoShotsAgainst !== null ? veoShots - veoShotsAgainst : null;
  const opponentPossession =
    veoPossession !== null ? Number((100 - veoPossession).toFixed(1)) : null;
  const possessionOffThird = getOwnMetricValue('team_possession_third_att_pct');
  const possessionMidThird = getOwnMetricValue('team_possession_third_mid_pct');
  const passZoneAtt = getOwnMetricValue('team_pass_zone_att_pct');
  const passZoneMid = getOwnMetricValue('team_pass_zone_mid_pct');

  const veoExpectedTeamMetricCells = useMemo(() => {
    const groups = veoEntrySchema?.team_metrics_by_category ?? [];
    return groups.reduce(
      (total, group) =>
        total +
        (group.metrics ?? []).reduce((groupTotal, metric) => {
          if (HIDDEN_VEO_TEAM_METRIC_SLUGS.has(metric.slug)) {
            return groupTotal;
          }

          if (OWN_SLUG_BY_OPPONENT_ALIAS[metric.slug]) {
            return groupTotal;
          }

          if (metric.side === 'OPPONENT') {
            return groupTotal + 1;
          }

          return groupTotal + 2;
        }, 0),
      0
    );
  }, [veoEntrySchema]);

  const veoCatalogPlayerMetricsCount = useMemo(() => {
    const groups = veoEntrySchema?.player_metrics_by_category ?? [];
    return groups.reduce((acc, group) => acc + (group.metrics?.length ?? 0), 0);
  }, [veoEntrySchema]);

  const veoPlayerMetricValuesFilled = useMemo(() => {
    const valuesByPlayer = veoSummary?.player_metrics?.values ?? {};
    return Object.values(valuesByPlayer).reduce((total, row) => {
      const rowValues = Object.values(row || {});
      return total + rowValues.filter((value) => value !== null && value !== undefined).length;
    }, 0);
  }, [veoSummary]);

  const veoExpectedPlayerMetricCells =
    (veoSummary?.participations?.length ?? 0) * veoCatalogPlayerMetricsCount;
  const veoTeamCompletionPct =
    veoExpectedTeamMetricCells > 0 ? (veoTeamMetricsFilled / veoExpectedTeamMetricCells) * 100 : null;
  const veoPlayerCompletionPct =
    veoExpectedPlayerMetricCells > 0
      ? (veoPlayerMetricValuesFilled / veoExpectedPlayerMetricCells) * 100
      : null;

  const comparisonRows = useMemo(
    () =>
      KPI_COMPARISON_ROWS.map((row) => {
        const ownMetric = row.ownSlug ? veoOwnMetricMap.get(row.ownSlug) : null;
        const opponentMetric = row.opponentSlug
          ? veoOpponentMetricMap.get(row.opponentSlug) || veoOpponentMetricMap.get(row.ownSlug)
          : veoOpponentMetricMap.get(row.ownSlug);
        const ownValue = ownMetric?.value ?? null;
        const opponentValue = row.opponentFromOwnPct
          ? opponentPossession
          : opponentMetric?.value ?? null;

        return {
          label: row.label,
          ownDisplay: formatMetricValue(ownValue, row.unit || ownMetric?.unit),
          opponentDisplay: formatMetricValue(opponentValue, row.unit || opponentMetric?.unit),
        };
      }),
    [veoOwnMetricMap, veoOpponentMetricMap, opponentPossession]
  );

  const comparisonChartData = useMemo(
    () =>
      KPI_COMPARISON_ROWS.map((row) => {
        const ownMetric = row.ownSlug ? veoOwnMetricMap.get(row.ownSlug) : null;
        const opponentMetric = row.opponentSlug
          ? veoOpponentMetricMap.get(row.opponentSlug) || veoOpponentMetricMap.get(row.ownSlug)
          : veoOpponentMetricMap.get(row.ownSlug);
        const ownValue = ownMetric?.value ?? null;
        const opponentValue = row.opponentFromOwnPct
          ? opponentPossession
          : opponentMetric?.value ?? null;

        const ownNumber = ownValue === null ? 0 : Number(ownValue);
        const opponentNumber = opponentValue === null ? 0 : Number(opponentValue);
        return {
          label: row.label,
          ownValue: ownNumber,
          opponentValue: opponentNumber,
          maxValue: Math.max(ownNumber, opponentNumber, 1),
          unit: row.unit || ownMetric?.unit || opponentMetric?.unit || '',
        };
      }),
    [veoOwnMetricMap, veoOpponentMetricMap, opponentPossession]
  );

  const territoryRows = useMemo(() => {
    const ownAtt = Number(getOwnMetricValue('team_possession_third_att_pct') ?? 0);
    const ownMid = Number(getOwnMetricValue('team_possession_third_mid_pct') ?? 0);
    const ownDef = Number(getOwnMetricValue('team_possession_third_def_pct') ?? 0);

    const oppAtt =
      getOpponentMetricValue('team_possession_third_att_pct') !== null
        ? Number(getOpponentMetricValue('team_possession_third_att_pct'))
        : Math.max(0, 100 - ownDef - ownMid);
    const oppMid =
      getOpponentMetricValue('team_possession_third_mid_pct') !== null
        ? Number(getOpponentMetricValue('team_possession_third_mid_pct'))
        : Math.max(0, 100 - ownAtt - ownDef);
    const oppDef =
      getOpponentMetricValue('team_possession_third_def_pct') !== null
        ? Number(getOpponentMetricValue('team_possession_third_def_pct'))
        : Math.max(0, 100 - ownAtt - ownMid);

    return [
      { label: 'Tiers offensif', ownPct: Math.round(ownAtt), oppPct: Math.round(oppAtt) },
      { label: 'Tiers milieu', ownPct: Math.round(ownMid), oppPct: Math.round(oppMid) },
      { label: 'Tiers defensif', ownPct: Math.round(ownDef), oppPct: Math.round(oppDef) },
    ];
  }, [veoOwnMetricMap, veoOpponentMetricMap]);

  const passZoneRows = useMemo(() => {
    const ownAtt = Number(getOwnMetricValue('team_pass_zone_att_pct') ?? 0);
    const ownMid = Number(getOwnMetricValue('team_pass_zone_mid_pct') ?? 0);
    const ownDef = Number(getOwnMetricValue('team_pass_zone_def_pct') ?? 0);

    const oppAtt =
      getOpponentMetricValue('team_pass_zone_att_pct') !== null
        ? Number(getOpponentMetricValue('team_pass_zone_att_pct'))
        : Math.max(0, 100 - ownDef - ownMid);
    const oppMid =
      getOpponentMetricValue('team_pass_zone_mid_pct') !== null
        ? Number(getOpponentMetricValue('team_pass_zone_mid_pct'))
        : Math.max(0, 100 - ownAtt - ownDef);
    const oppDef =
      getOpponentMetricValue('team_pass_zone_def_pct') !== null
        ? Number(getOpponentMetricValue('team_pass_zone_def_pct'))
        : Math.max(0, 100 - ownAtt - ownMid);

    return [
      { label: 'Zone defensive', ownPct: Math.round(ownDef), oppPct: Math.round(oppDef) },
      { label: 'Zone milieu', ownPct: Math.round(ownMid), oppPct: Math.round(oppMid) },
      { label: 'Zone offensive', ownPct: Math.round(ownAtt), oppPct: Math.round(oppAtt) },
    ];
  }, [veoOwnMetricMap, veoOpponentMetricMap]);

  const comparisonVisualRows = useMemo(
    () =>
      comparisonChartData.map((row, index) => {
        const total = row.ownValue + row.opponentValue;
        const ownShare = total > 0 ? (row.ownValue / total) * 100 : 50;
        const oppShare = total > 0 ? (row.opponentValue / total) * 100 : 50;
        const diff = row.ownValue - row.opponentValue;
        return {
          ...row,
          ownShare,
          oppShare,
          diff,
          ownDisplay: comparisonRows[index]?.ownDisplay ?? formatMetricValue(row.ownValue, row.unit),
          opponentDisplay:
            comparisonRows[index]?.opponentDisplay ?? formatMetricValue(row.opponentValue, row.unit),
        };
      }),
    [comparisonChartData, comparisonRows]
  );

  const activeZoneTeamLabel = zoneViewSide === 'OWN' ? ownTeamLabel : opponentTeamLabel;
  const activeZoneTeamTag = zoneViewSide === 'OWN' ? ownTeamTag : opponentTeamTag;
  const activeZoneAccentClass = zoneViewSide === 'OWN' ? 'text-cyan-100' : 'text-amber-100';
  const activeTerritoryRows = useMemo(
    () =>
      territoryRows.map((row) => ({
        label: row.label,
        value: zoneViewSide === 'OWN' ? row.ownPct : row.oppPct,
      })),
    [territoryRows, zoneViewSide]
  );
  const activePassZoneRows = useMemo(
    () =>
      passZoneRows.map((row) => ({
        label: row.label,
        value: zoneViewSide === 'OWN' ? row.ownPct : row.oppPct,
      })),
    [passZoneRows, zoneViewSide]
  );

  const coachAnalysis = useMemo(() => {
    const possessionScoreBase = veoPossession === null ? 5 : veoPossession >= 55 ? 7 : veoPossession >= 50 ? 6 : 4;
    const progressionScoreBase =
      passZoneAtt === null ? 5 : passZoneAtt >= 20 ? 7 : passZoneAtt >= 15 ? 6 : 4;
    const finishingScoreBase =
      veoShotConversion === null ? 4 : veoShotConversion >= 25 ? 8 : veoShotConversion >= 12 ? 6 : 3;
    const defensiveScoreBase =
      veoGoalsAgainst === null ? 5 : veoGoalsAgainst === 0 ? 8 : veoGoalsAgainst <= 1 ? 6 : 4;

    const possessionScore = clampScore(
      possessionScoreBase + (possessionOffThird !== null && possessionOffThird >= 20 ? 1 : 0)
    );
    const progressionScore = clampScore(
      progressionScoreBase + (passZoneMid !== null && passZoneMid <= 70 ? 1 : 0)
    );
    const finishingScore = clampScore(
      finishingScoreBase + (veoShots !== null && veoShots >= 10 ? 1 : 0)
    );
    const defensiveScore = clampScore(
      defensiveScoreBase + (veoShotsAgainst !== null && veoShotsAgainst <= 8 ? 1 : 0)
    );

    const globalScore = clampScore(
      (possessionScore + progressionScore + finishingScore + defensiveScore) / 4
    );

    const recommendations = [];
    if (finishingScore <= 5) {
      recommendations.push('Prioriser un cycle finition: enchainement controle-frappe dans la surface.');
    }
    if (progressionScore <= 5) {
      recommendations.push('Augmenter les circuits vers le dernier tiers (appui-remise + appel profondeur).');
    }
    if (defensiveScore <= 5) {
      recommendations.push('Travailler la protection axe + pressing a la perte sur 8-10 secondes.');
    }
    if (possessionScore <= 5) {
      recommendations.push('Renforcer la qualite de conservation sous pression (rondo directionnel).');
    }
    if (recommendations.length === 0) {
      recommendations.push('Conserver les principes actuels et augmenter le volume de situations de tir.');
    }

    const sections = [
      {
        title: 'Maitrise et occupation',
        score: possessionScore,
        bullets: [
          `Possession: ${formatMetricValue(veoPossession, '%')} (adversaire ${formatMetricValue(opponentPossession, '%')}).`,
          `Occupation tiers offensif: ${formatMetricValue(possessionOffThird, '%')}.`,
          `Occupation tiers milieu: ${formatMetricValue(possessionMidThird, '%')}.`,
        ],
      },
      {
        title: 'Progression et creation',
        score: progressionScore,
        bullets: [
          `Passes reussies: ${formatMetricValue(veoPasses, '')}.`,
          `Passes en zone offensive: ${formatMetricValue(passZoneAtt, '%')}.`,
          `Passes en zone milieu: ${formatMetricValue(passZoneMid, '%')}.`,
        ],
      },
      {
        title: 'Finition',
        score: finishingScore,
        bullets: [
          `Tirs: ${formatMetricValue(veoShots, '')}, buts: ${formatMetricValue(veoGoals, '')}.`,
          `Conversion tirs/buts: ${formatMetricValue(veoShotConversion, '%')}.`,
          `Differentiel tirs: ${veoShotBalance === null ? '-' : veoShotBalance > 0 ? `+${veoShotBalance}` : veoShotBalance}.`,
        ],
      },
      {
        title: 'Solidite defensive',
        score: defensiveScore,
        bullets: [
          `Tirs encaisses: ${formatMetricValue(veoShotsAgainst, '')}.`,
          `Buts encaisses: ${formatMetricValue(veoGoalsAgainst, '')}.`,
          `Corners obtenus: ${formatMetricValue(veoCorners, '')}.`,
        ],
      },
    ];

    return {
      globalScore,
      sections,
      recommendations,
    };
  }, [
    veoPossession,
    opponentPossession,
    possessionOffThird,
    possessionMidThird,
    passZoneAtt,
    passZoneMid,
    veoPasses,
    veoShots,
    veoGoals,
    veoShotConversion,
    veoShotBalance,
    veoShotsAgainst,
    veoGoalsAgainst,
    veoCorners,
  ]);

  const preferredPlayerMetricOrder = [
    'player_goal_assists',
    'player_shots',
    'player_shots_on_target',
    'player_goals',
    'player_duels_won',
    'player_fouls_committed',
    'player_cards',
    'player_offsides',
    'player_dribbles_won',
    'player_tackles_won',
    'player_recoveries',
    'player_ball_losses',
  ];

  const veoPlayerColumns = (() => {
    const allColumns = veoSummary?.player_metrics?.columns ?? [];
    const selected = allColumns.filter((col) => preferredPlayerMetricOrder.includes(col.slug));
    if (selected.length > 0) {
      return selected;
    }
    return allColumns.slice(0, 6);
  })();

  const veoReportKpis = useMemo(
    () => [
      {
        label: 'Possession',
        value: veoPossession !== null ? `${veoPossession.toFixed(1)}%` : '-',
        tone: getPerformanceTone('team_possession_pct', veoPossession),
      },
      {
        label: 'Passes',
        value: formatMetricValue(veoPasses, ''),
        tone: getPerformanceTone('team_passes_completed', veoPasses),
      },
      {
        label: 'Tirs',
        value: formatMetricValue(veoShots, ''),
        tone: getPerformanceTone('team_shots', veoShots),
      },
      {
        label: 'Buts',
        value: formatMetricValue(veoGoals, ''),
        tone: getPerformanceTone('team_goals_scored', veoGoals),
      },
      {
        label: 'Corners',
        value: formatMetricValue(veoCorners, ''),
        tone: getPerformanceTone('team_corners', veoCorners),
      },
      {
        label: 'Score plan de jeu',
        value: `${coachAnalysis.globalScore}/10`,
        tone: getPerformanceTone('global_score', coachAnalysis.globalScore),
      },
    ],
    [veoPossession, veoPasses, veoShots, veoGoals, veoCorners, coachAnalysis.globalScore]
  );

  const handleDownloadVeoStyledReport = async () => {
    if (!veoSummary) {
      return;
    }

    const fileBase = `${sanitizeFilename(sessionTitle)}-veo`;
    const downloadedFromView = await downloadElementAsPng(veoGraphReportRef.current, `${fileBase}.png`);
    if (downloadedFromView) {
      return;
    }

    let logoDataUrl = '';
    try {
      const response = await fetch(CLUB_LOGO_PATH);
      if (response.ok) {
        const blob = await response.blob();
        logoDataUrl = await blobToDataUrl(blob);
      }
    } catch (fetchError) {
      console.error('Logo VEO indisponible pour export:', fetchError);
    }

    const svg = BUILD_VEO_REPORT_SVG({
      title: veoSummary.match.veo_title || sessionTitle,
      dateLabel: veoSummary.match.date,
      opponent: veoSummary.match.opponent_name || '-',
      scoreLabel: `Score ${veoSummary.match.score_for ?? 0}-${veoSummary.match.score_against ?? 0}`,
      matchType: veoSummary.match.match_type || 'MATCH',
      teamName: ownTeamLabel,
      globalScoreLabel: `${coachAnalysis.globalScore}/10`,
      qualityTeamLabel: `Qualite metriques equipe: ${veoTeamMetricsFilled} / ${veoExpectedTeamMetricCells || '-'}`,
      qualityPlayerLabel: `Qualite metriques joueurs: ${veoPlayerMetricValuesFilled} / ${veoExpectedPlayerMetricCells || '-'}`,
      kpis: veoReportKpis,
      comparisonRows,
      comparisonChartData,
      territoryRows,
      passZoneRows,
      analysisSections: coachAnalysis.sections,
      recommendations: coachManualNote.trim()
        ? coachManualNote
            .split('\n')
            .map((line) => line.trim())
            .filter(Boolean)
        : coachAnalysis.recommendations,
      logoDataUrl,
    });

    const svgBlob = new Blob([svg], { type: 'image/svg+xml;charset=utf-8' });
    const svgUrl = URL.createObjectURL(svgBlob);

    const downloadSvgFallback = () => {
      const fallbackUrl = URL.createObjectURL(svgBlob);
      const fallbackAnchor = document.createElement('a');
      fallbackAnchor.href = fallbackUrl;
      fallbackAnchor.download = `${fileBase}.svg`;
      document.body.appendChild(fallbackAnchor);
      fallbackAnchor.click();
      document.body.removeChild(fallbackAnchor);
      URL.revokeObjectURL(fallbackUrl);
    };

    const image = new Image();
    image.onload = () => {
      const canvas = document.createElement('canvas');
      canvas.width = image.width;
      canvas.height = image.height;

      const ctx = canvas.getContext('2d');
      if (!ctx) {
        URL.revokeObjectURL(svgUrl);
        downloadSvgFallback();
        setError("Export exact indisponible: fichier template téléchargé (SVG).");
        return;
      }

      ctx.drawImage(image, 0, 0);
      canvas.toBlob((pngBlob) => {
        URL.revokeObjectURL(svgUrl);
        if (!pngBlob) {
          downloadSvgFallback();
          setError("Export exact indisponible: fichier template téléchargé (SVG).");
          return;
        }

        const pngUrl = URL.createObjectURL(pngBlob);
        const link = document.createElement('a');
        link.href = pngUrl;
        link.download = `${fileBase}.png`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(pngUrl);
        setError("Export exact indisponible sur ce navigateur: template PNG téléchargé.");
      }, 'image/png');
    };

    image.onerror = () => {
      URL.revokeObjectURL(svgUrl);
      downloadSvgFallback();
      setError("Export exact indisponible sur ce navigateur: template SVG téléchargé.");
    };

    image.src = svgUrl;
  };

  const visibleOpponentMetrics = useMemo(() => {
    return veoOpponentMetrics.slice(0, 8).map((metric) => ({
      label: formatMetricLabel(metric),
      value: formatMetricValue(metric.value, metric.unit),
      tone: getPerformanceTone(metric.metric_slug, metric.value),
    }));
  }, [veoOpponentMetrics]);

  const visibleOwnMetrics = useMemo(() => {
    return veoOwnMetrics.slice(0, 8).map((metric) => ({
      label: formatMetricLabel(metric),
      value: formatMetricValue(metric.value, metric.unit),
      tone: getPerformanceTone(metric.metric_slug, metric.value),
    }));
  }, [veoOwnMetrics]);

  const handleDownloadVeoRawCsv = () => {
    if (!veoSummary) {
      return;
    }

    const rows = [];

    rows.push(['Rapport VEO - Donnees brutes']);
    rows.push(['Session', sessionTitle]);
    rows.push(['Date', veoSummary.match.date]);
    rows.push(['Adversaire', veoSummary.match.opponent_name]);
    rows.push(['Type', veoSummary.match.match_type || '']);
    rows.push([
      'Score',
      `${veoSummary.match.score_for ?? 0}-${veoSummary.match.score_against ?? 0}`,
    ]);
    rows.push([]);

    rows.push(['Comparatif equipe vs adversaire']);
    rows.push(['Indicateur', 'Notre equipe', 'Adversaire']);
    comparisonRows.forEach((row) => {
      rows.push([row.label, row.ownDisplay, row.opponentDisplay]);
    });
    rows.push([]);

    rows.push(['Metriques equipe - notre equipe']);
    rows.push(['Metrique', 'Valeur']);
    veoOwnMetrics.forEach((metric) => {
      rows.push([formatMetricLabel(metric), formatMetricValue(metric.value, metric.unit)]);
    });
    rows.push([]);

    rows.push(['Metriques equipe - adversaire']);
    rows.push(['Metrique', 'Valeur']);
    veoOpponentMetrics.forEach((metric) => {
      rows.push([formatMetricLabel(metric), formatMetricValue(metric.value, metric.unit)]);
    });
    rows.push([]);

    rows.push(['Metriques joueurs']);
    if (veoPlayersTracked === 0 || veoPlayerColumns.length === 0) {
      rows.push(['Aucune metrique joueur disponible']);
    } else {
      rows.push([
        'Joueur',
        ...veoPlayerColumns.map((column) => formatPlayerMetricLabel(column)),
      ]);
      (veoSummary.player_metrics?.players ?? []).forEach((player) => {
        rows.push([
          player.name,
          ...veoPlayerColumns.map((column) => {
            const rawValue =
              veoSummary.player_metrics?.values?.[String(player.id)]?.[column.slug];
            return rawValue ?? '';
          }),
        ]);
      });
    }

    const csvContent = toCsvString(rows);
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${sanitizeFilename(sessionTitle)}-veo-data.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const handleSaveCoachNote = () => {
    if (!selectedVeoMatchId) {
      return;
    }
    try {
      window.localStorage.setItem(`veo_coach_note_${selectedVeoMatchId}`, coachManualNote);
      setCoachNoteSaved(true);
      window.setTimeout(() => setCoachNoteSaved(false), 1800);
    } catch (err) {
      console.error('Impossible de sauvegarder la note coach locale:', err);
    }
  };

  const handleClearCoachNote = () => {
    if (!selectedVeoMatchId) {
      return;
    }
    try {
      window.localStorage.removeItem(`veo_coach_note_${selectedVeoMatchId}`);
    } catch (err) {
      console.error('Impossible de supprimer la note coach locale:', err);
    }
    setCoachManualNote('');
    setCoachNoteSaved(false);
  };

  return (
    <div className="max-w-5xl mx-auto py-6 sm:px-6 lg:px-8">
      <div className="px-4 py-6 sm:px-0">
        {/* Header with back button */}
        <div className="mb-6">
          <Link
            to="/catapult/sessions"
            className="inline-flex text-xl font-medium text-orange-600 hover:text-black"
          >
            <ArrowLeftIcon className="h-5 w-5 mr-2" />
            Retour aux sessions
          </Link>
          <h1 className="inline-block-center bg-white/50 px-4 py-2 rounded-md text-3xl text-center font-bold text-gray-900">
            {sessionTitle}
          </h1>
          <p className="justify-self-center inline-block-center bg-white/50 rounded-md mt-2 text-m text-center text-black">
            Choisissez un type de rapport à générer
          </p>
        </div>

        {/* Error message */}
        {error && (
          <div className="rounded-md bg-red-50 p-4 mb-6">
            <p className="text-sm text-red-800">{error}</p>
          </div>
        )}

        {/* Report type cards - player select integrated inside individual card */}
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3 mb-8">
          {reportTypes.map((report) => {
            const Icon = report.icon;
            if (report.id === 'individual') {
              return (
                <div key={report.id} className="flex flex-col gap-2">
                  {availablePlayers.length > 0 && (
                    <div className="bg-white/80 rounded-lg shadow px-4 py-3">
                      <label htmlFor="player-select" className="block text-xs font-medium text-gray-600 mb-1">
                        Sélectionner un joueur
                      </label>
                      <select
                        id="player-select"
                        value={selectedPlayer}
                        onChange={(e) => setSelectedPlayer(e.target.value)}
                        className="block w-full pl-3 pr-10 py-1.5 text-sm border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 rounded-md"
                      >
                        {availablePlayers.map((player) => (
                          <option key={player} value={player}>{player}</option>
                        ))}
                      </select>
                    </div>
                  )}
                  <button
                    onClick={report.onClick}
                    disabled={!report.available || loading}
                    className={`
                      relative rounded-lg border p-6 text-left transition-all flex-1
                      ${report.available
                        ? 'border-gray-300 bg-white/80 hover:border-blue-500 hover:shadow-lg cursor-pointer'
                        : 'border-gray-200 bg-gray-50 cursor-not-allowed opacity-60'}
                      ${loading && report.available ? 'opacity-50' : ''}
                    `}
                  >
                    <div className="flex items-center justify-between mb-4">
                      <Icon className={`h-8 w-8 ${report.available ? 'text-blue-600' : 'text-gray-400'}`} />
                      {!report.available && (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-200 text-gray-800">
                          Bientôt disponible
                        </span>
                      )}
                    </div>
                    <h3 className="text-lg font-medium text-gray-900">{report.title}</h3>
                    <p className="mt-2 text-sm text-gray-500">{report.description}</p>
                  </button>
                </div>
              );
            }
            return (
              <button
                key={report.id}
                onClick={report.onClick}
                disabled={!report.available || loading}
                  className={`
                  relative rounded-lg border p-6 text-left transition-all
                  ${report.available
                    ? 'border-gray-300 bg-white/80 hover:border-blue-500 hover:shadow-lg cursor-pointer'
                    : 'border-gray-200 bg-gray-50 cursor-not-allowed opacity-60'}
                  ${loading && report.available ? 'opacity-50' : ''}
                `}
              >
                <div className="flex items-center justify-between mb-4">
                  <Icon className={`h-8 w-8 ${report.available ? 'text-blue-600' : 'text-gray-400'}`} />
                  {!report.available && (
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-200 text-gray-800">
                      Bientôt disponible
                    </span>
                  )}
                </div>
                <h3 className="text-lg font-medium text-gray-900">{report.title}</h3>
                <p className="mt-2 text-sm text-gray-500">{report.description}</p>
              </button>
            );
          })}
        </div>

        {/* Display session report image */}
        {showReport && reportImage && (
          <div className="bg-white/60 rounded-lg shadow-lg p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold text-gray-900">Rapport de séance</h2>
              <a
                href={reportImage}
                download={`rapport-${sessionTitle}.png`}
                className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700"
              >
                <svg className="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                Télécharger
              </a>
            </div>
            <div className="overflow-x-auto">
              <img
                src={reportImage}
                alt="Rapport de séance"
                className="max-w-full h-auto rounded-lg"
              />
            </div>
          </div>
        )}

        {showReport && (
          <div className="bg-white/80 rounded-lg shadow-lg p-6 mt-6">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-4">
                <h2 className="text-xl font-bold text-gray-900">Rapport Veo (session)</h2>
                <div className="inline-flex rounded-md border border-gray-300 overflow-hidden">
                  <button
                    type="button"
                    onClick={() => setVeoReportMode('GRAPH')}
                    className={`px-3 py-1.5 text-xs font-semibold ${
                      veoReportMode === 'GRAPH'
                        ? 'bg-blue-600 text-white'
                        : 'bg-white text-gray-700 hover:bg-gray-50'
                    }`}
                  >
                    Rapport graphique
                  </button>
                  <button
                    type="button"
                    onClick={() => setVeoReportMode('DATA')}
                    className={`px-3 py-1.5 text-xs font-semibold ${
                      veoReportMode === 'DATA'
                        ? 'bg-blue-600 text-white'
                        : 'bg-white text-gray-700 hover:bg-gray-50'
                    }`}
                  >
                    Données brutes
                  </button>
                </div>
              </div>
              {showVeoReport && veoSummary && (
                <button
                  type="button"
                  onClick={
                    veoReportMode === 'GRAPH'
                      ? handleDownloadVeoStyledReport
                      : handleDownloadVeoRawCsv
                  }
                  className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700"
                >
                  <svg className="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                  </svg>
                  {veoReportMode === 'GRAPH' ? 'Télécharger' : 'Télécharger'}
                </button>
              )}
            </div>

            {!showVeoReport ? (
              <div className="rounded-md bg-yellow-50 p-4">
                <p className="text-sm text-yellow-800">
                  Aucun match Veo associe a cette session. Cree ou complete un match depuis l'onglet VEO,
                  puis regénère le rapport de séance.
                </p>
              </div>
            ) : loadingVeoSummary ? (
              <div className="rounded-md bg-blue-50 p-4">
                <div className="flex items-center gap-2 text-sm text-blue-900">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-700"></div>
                  Chargement des donnees VEO pour le rapport...
                </div>
              </div>
            ) : !veoSummary ? (
              <div className="rounded-md bg-yellow-50 p-4">
                <p className="text-sm text-yellow-800">
                  Donnees VEO indisponibles pour cette session. Verifie le match dans l'onglet VEO.
                </p>
              </div>
            ) : (
              <div className="space-y-6">
                {veoReportMode === 'GRAPH' && (
                  <div ref={veoGraphReportRef} className="rounded-xl overflow-hidden border border-slate-700 bg-[#141f30]">
                    <div className="bg-white mx-4 mt-4 rounded-md px-6 py-5">
                      <div className="flex flex-wrap items-end justify-between gap-4">
                        <div className="flex items-center gap-4">
                          <img src={CLUB_LOGO_PATH} alt="Logo club" className="h-20 w-20 object-contain" />
                          <div>
                            <p className="text-xs uppercase tracking-wide text-slate-500">Rapport VEO</p>
                            <p className="text-2xl font-bold text-slate-900">{veoSummary.match.veo_title || sessionTitle}</p>
                            <p className="text-sm text-slate-600">
                              {veoSummary.match.date} • {veoSummary.match.match_type} • Score {veoSummary.match.score_for ?? 0}-{veoSummary.match.score_against ?? 0}
                            </p>
                          </div>
                        </div>
                        <div className="text-right">
                          <p className="text-xs uppercase tracking-wide text-slate-500">Adversaire</p>
                          <p className="text-lg font-semibold text-slate-900">{veoSummary.match.opponent_name}</p>
                          <div className="mt-1 inline-flex items-center rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-700">
                            {veoSummary.match.match_type}
                          </div>
                        </div>
                      </div>
                    </div>

                    <div className="p-4 space-y-3">
                      <div className="grid grid-cols-2 lg:grid-cols-6 gap-3">
                        {veoReportKpis.map((kpi) => {
                          const tone = KPI_TONE_CLASSES[kpi.tone] || KPI_TONE_CLASSES.neutral;
                          return (
                          <div key={kpi.label} className={`rounded-md border px-3 py-3 ${tone.card}`}>
                            <p className={`text-[11px] uppercase tracking-wide ${tone.label}`}>{kpi.label}</p>
                            <p className={`mt-1 text-xl font-bold ${tone.value}`}>{kpi.value}</p>
                          </div>
                        );
                        })}
                      </div>

                      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
                        <div className="rounded-md border border-blue-400/30 bg-linear-to-br from-blue-500/20 to-slate-900/30 p-4">
                          <p className="text-xs uppercase tracking-wide text-blue-200">Score global plan de jeu</p>
                          <p className="mt-2 text-4xl font-bold text-white">{coachAnalysis.globalScore}/10</p>
                          <p className="mt-2 text-xs text-blue-100">
                            Lecture globale basée sur maîtrise, progression, finition et solidité.
                          </p>
                        </div>
                        <div className="rounded-md border border-slate-600 bg-[#223146] p-4">
                          <p className="text-sm font-semibold text-white">Qualité des données</p>
                          <div className="mt-3 space-y-3">
                            <div>
                              <div className="flex items-center justify-between text-xs text-slate-300">
                                <span>Équipe</span>
                                <span>
                                  {veoTeamMetricsFilled}
                                  {veoExpectedTeamMetricCells > 0 ? ` / ${veoExpectedTeamMetricCells}` : ''}
                                  {veoTeamCompletionPct !== null ? ` (${veoTeamCompletionPct.toFixed(0)}%)` : ''}
                                </span>
                              </div>
                              <div className="mt-1 h-2 rounded-full bg-slate-700 overflow-hidden">
                                <div
                                  className="h-2 bg-blue-400"
                                  style={{
                                    width: `${Math.max(0, Math.min(100, veoTeamCompletionPct ?? 0))}%`,
                                  }}
                                ></div>
                              </div>
                            </div>
                            <div>
                              <div className="flex items-center justify-between text-xs text-slate-300">
                                <span>Joueurs</span>
                                <span>
                                  {veoPlayerMetricValuesFilled}
                                  {veoExpectedPlayerMetricCells > 0 ? ` / ${veoExpectedPlayerMetricCells}` : ''}
                                  {veoPlayerCompletionPct !== null ? ` (${veoPlayerCompletionPct.toFixed(0)}%)` : ''}
                                </span>
                              </div>
                              <div className="mt-1 h-2 rounded-full bg-slate-700 overflow-hidden">
                                <div
                                  className="h-2 bg-emerald-400"
                                  style={{
                                    width: `${Math.max(0, Math.min(100, veoPlayerCompletionPct ?? 0))}%`,
                                  }}
                                ></div>
                              </div>
                            </div>
                          </div>
                        </div>
                        <div className="rounded-md border border-slate-600 bg-[#223146] p-4">
                          <p className="text-sm font-semibold text-white mb-3">Profil de performance</p>
                          <div className="space-y-2">
                            {coachAnalysis.sections.map((section) => (
                              <div key={`profile-${section.title}`} className="space-y-1">
                                <div className="flex items-center justify-between text-xs text-slate-300">
                                  <span>{section.title}</span>
                                  <span>{section.score}/10</span>
                                </div>
                                <div className="h-2 rounded bg-slate-700 overflow-hidden">
                                  <div
                                    className="h-2 bg-blue-400"
                                    style={{ width: `${section.score * 10}%` }}
                                  ></div>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>

                      <div className="grid grid-cols-1 xl:grid-cols-3 gap-3">
                        <div className="rounded-md border border-slate-600 bg-[#223146] p-4 xl:col-span-3">
                          <p className="text-sm font-semibold text-white mb-3">Comparatif visuel équipe vs adversaire</p>
                          <div className="grid grid-cols-1 2xl:grid-cols-2 gap-3">
                            {comparisonVisualRows.slice(0, 7).map((row) => {
                              const advantageClass =
                                row.diff === 0 ? 'text-slate-300' : row.diff > 0 ? 'text-blue-300' : 'text-orange-300';
                              return (
                                <div key={`chart-visual-${row.label}`} className="rounded border border-slate-600 bg-[#1b283a] p-3">
                                  <div className="flex items-center justify-between gap-2 text-xs">
                                    <span className="font-semibold text-slate-100">{row.label}</span>
                                    <span className="text-slate-300">
                                      Nous {row.ownDisplay} • Adv {row.opponentDisplay}
                                    </span>
                                  </div>
                                  <div className="mt-2 relative h-3 rounded-full bg-slate-700 overflow-hidden">
                                    <div className="absolute inset-y-0 left-0 bg-blue-400" style={{ width: `${row.ownShare}%` }}></div>
                                    <div className="absolute inset-y-0 right-0 bg-orange-400" style={{ width: `${row.oppShare}%` }}></div>
                                    <div className="absolute left-1/2 top-0 h-3 w-px bg-slate-200/70"></div>
                                  </div>
                                  <div className="mt-1 flex items-center justify-between text-[11px]">
                                    <span className="text-blue-200">{row.ownShare.toFixed(0)}%</span>
                                    <span className={advantageClass}>
                                      {row.diff === 0 ? 'Équilibré' : row.diff > 0 ? `+${row.diff.toFixed(1)} nous` : `${row.diff.toFixed(1)} adv`}
                                    </span>
                                    <span className="text-orange-200">{row.oppShare.toFixed(0)}%</span>
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        </div>

                        <div className="rounded-md border border-slate-600 bg-[#223146] p-4 xl:col-span-3">
                          <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
                            <div className="inline-flex items-center gap-2">
                              <span className={`inline-flex h-6 min-w-6 items-center justify-center rounded bg-slate-900 px-1 text-xs font-semibold ${activeZoneAccentClass}`}>
                                {activeZoneTeamTag}
                              </span>
                              <span className="text-xs text-slate-300">
                                Vue zones: {activeZoneTeamLabel}
                              </span>
                            </div>
                            <button
                              type="button"
                              onClick={() => setZoneViewSide(zoneViewSide === 'OWN' ? 'OPPONENT' : 'OWN')}
                              className="inline-flex items-center rounded bg-slate-700 px-3 py-1.5 text-xs font-semibold text-slate-100 hover:bg-slate-600"
                            >
                              {zoneViewSide === 'OWN' ? 'Passer aux zones adversaires' : 'Revenir à nos zones'}
                            </button>
                          </div>

                          <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
                            <div className="rounded-lg border border-slate-600 bg-[#1b283a] p-3">
                              <p className="text-sm font-semibold text-white mb-2">Zones de possession</p>
                              <div className="rounded-xl border border-slate-500 overflow-hidden">
                                <div className="grid grid-cols-3">
                                  {activeTerritoryRows.map((row, index) => (
                                    <div
                                      key={`territory-active-${row.label}`}
                                      className={`px-2 py-4 text-center ${
                                        index === 1 ? 'bg-cyan-100/20' : 'bg-slate-800/50'
                                      }`}
                                    >
                                      <div className="mx-auto h-20 w-20 rounded-full bg-slate-700/90 flex items-center justify-center text-white text-2xl font-bold">
                                        {row.value}%
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              </div>
                              <div className="grid grid-cols-3 mt-2">
                                {activeTerritoryRows.map((row) => (
                                  <p key={`territory-active-label-${row.label}`} className="text-[11px] text-center text-slate-300 font-medium">
                                    {row.label.replace('Tiers ', '')}
                                  </p>
                                ))}
                              </div>
                            </div>

                            <div className="rounded-lg border border-slate-600 bg-[#1b283a] p-3">
                              <p className="text-sm font-semibold text-white mb-2">Zones de passes</p>
                              <div className="rounded-xl border border-slate-500 overflow-hidden">
                                <div className="grid grid-cols-3">
                                  {activePassZoneRows.map((row, index) => (
                                    <div
                                      key={`pass-zone-active-${row.label}`}
                                      className={`px-2 py-4 text-center ${
                                        index === 1 ? 'bg-cyan-100/20' : 'bg-slate-800/50'
                                      }`}
                                    >
                                      <div className="mx-auto h-20 w-20 rounded-full bg-slate-700/90 flex items-center justify-center text-white text-2xl font-bold">
                                        {row.value}%
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              </div>
                              <div className="grid grid-cols-3 mt-2">
                                {activePassZoneRows.map((row) => (
                                  <p key={`pass-zone-active-label-${row.label}`} className="text-[11px] text-center text-slate-300 font-medium">
                                    {row.label.replace('Zone ', '')}
                                  </p>
                                ))}
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>

                      <div className="grid grid-cols-1 xl:grid-cols-2 gap-3">
                        <div className="rounded-md border border-slate-600 bg-[#223146] p-4">
                          <p className="text-sm font-semibold text-white mb-3">Métriques clés - notre équipe</p>
                          {visibleOwnMetrics.length === 0 ? (
                            <p className="text-xs text-slate-400">Aucune métrique disponible.</p>
                          ) : (
                            <div className="space-y-2">
                              {visibleOwnMetrics.map((metric) => (
                                <div key={`own-visible-${metric.label}`} className="flex items-center justify-between text-xs">
                                  <span className="text-slate-300">{metric.label}</span>
                                  <span className={`font-semibold ${(KPI_TONE_CLASSES[metric.tone] || KPI_TONE_CLASSES.neutral).value}`}>
                                    {metric.value}
                                  </span>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                        <div className="rounded-md border border-slate-600 bg-[#223146] p-4">
                          <p className="text-sm font-semibold text-white mb-3">Métriques clés - adversaire</p>
                          {visibleOpponentMetrics.length === 0 ? (
                            <p className="text-xs text-slate-400">Aucune métrique disponible.</p>
                          ) : (
                            <div className="space-y-2">
                              {visibleOpponentMetrics.map((metric) => (
                                <div key={`opp-visible-${metric.label}`} className="flex items-center justify-between text-xs">
                                  <span className="text-slate-300">{metric.label}</span>
                                  <span className={`font-semibold ${(KPI_TONE_CLASSES[metric.tone] || KPI_TONE_CLASSES.neutral).value}`}>
                                    {metric.value}
                                  </span>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>

                      <div className="grid grid-cols-1 xl:grid-cols-2 gap-3">
                        {coachAnalysis.sections.map((section) => {
                          const scoreTone =
                            section.score >= 8
                              ? 'border-emerald-400/30 bg-emerald-500/5 text-emerald-200'
                              : section.score >= 6
                                ? 'border-blue-400/30 bg-blue-500/5 text-blue-200'
                                : 'border-orange-400/30 bg-orange-500/5 text-orange-200';
                          return (
                            <div key={section.title} className={`rounded-md border p-4 ${scoreTone}`}>
                              <div className="flex items-center justify-between mb-2">
                                <h3 className="text-sm font-semibold text-white">{section.title}</h3>
                                <span className="text-sm font-bold text-white">{section.score}/10</span>
                              </div>
                              <ul className="space-y-1 text-sm text-slate-200">
                                {section.bullets.map((bullet) => (
                                  <li key={bullet}>• {bullet}</li>
                                ))}
                              </ul>
                            </div>
                          );
                        })}
                      </div>

                      <div className="rounded-md border border-slate-600 bg-[#223146] p-4">
                        <div className="flex items-center justify-between gap-2 mb-2">
                          <h3 className="text-sm font-semibold text-white">Notes coach (manuel)</h3>
                          {coachNoteSaved && <span className="text-[11px] text-emerald-300">Sauvegardé</span>}
                        </div>
                        <textarea
                          value={coachManualNote}
                          onChange={(e) => setCoachManualNote(e.target.value)}
                          placeholder="Ajoute ici tes observations et recommandations terrain pour ce match..."
                          rows={5}
                          className="w-full rounded-md border border-slate-500 bg-[#141f30] text-slate-100 placeholder-slate-400 text-sm p-3 focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                        <div className="mt-2 flex items-center gap-2">
                          <button
                            type="button"
                            onClick={handleSaveCoachNote}
                            className="inline-flex items-center px-3 py-1.5 rounded bg-blue-600 text-white text-xs font-semibold hover:bg-blue-500"
                          >
                            Enregistrer la note
                          </button>
                          <button
                            type="button"
                            onClick={handleClearCoachNote}
                            className="inline-flex items-center px-3 py-1.5 rounded border border-slate-500 text-slate-200 text-xs font-semibold hover:bg-slate-700"
                          >
                            Vider
                          </button>
                        </div>
                        <details className="mt-3 pt-3 border-t border-slate-600">
                          <summary className="cursor-pointer text-xs font-semibold uppercase tracking-wide text-slate-400">
                            Suggestions automatiques (optionnel)
                          </summary>
                          <ul className="mt-2 space-y-1 text-sm text-slate-200">
                            {coachAnalysis.recommendations.map((item) => (
                              <li key={item}>• {item}</li>
                            ))}
                          </ul>
                        </details>
                      </div>
                    </div>
                  </div>
                )}

                {veoReportMode === 'DATA' && (
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-7 gap-3">
                    <div className="bg-gray-50 rounded-md p-3 lg:col-span-2">
                      <p className="text-xs uppercase text-gray-500">Match</p>
                      <p className="text-sm font-semibold text-gray-900">{veoSummary.match.opponent_name}</p>
                      <p className="text-xs text-gray-500">
                        {veoSummary.match.date} • Score {veoSummary.match.score_for ?? 0}-{veoSummary.match.score_against ?? 0}
                      </p>
                    </div>
                    <div className="bg-gray-50 rounded-md p-3">
                      <p className="text-xs uppercase text-gray-500">Possession</p>
                      <p className="text-lg font-bold text-gray-900">
                        {veoPossession !== null ? `${veoPossession.toFixed(1)}%` : '-'}
                      </p>
                    </div>
                    <div className="bg-gray-50 rounded-md p-3">
                      <p className="text-xs uppercase text-gray-500">Passes</p>
                      <p className="text-lg font-bold text-gray-900">{veoPasses !== null ? veoPasses : '-'}</p>
                    </div>
                    <div className="bg-gray-50 rounded-md p-3">
                      <p className="text-xs uppercase text-gray-500">Tirs</p>
                      <p className="text-lg font-bold text-gray-900">{veoShots !== null ? veoShots : '-'}</p>
                    </div>
                    <div className="bg-gray-50 rounded-md p-3">
                      <p className="text-xs uppercase text-gray-500">Buts</p>
                      <p className="text-lg font-bold text-gray-900">{veoGoals !== null ? veoGoals : '-'}</p>
                    </div>
                    <div className="bg-gray-50 rounded-md p-3">
                      <p className="text-xs uppercase text-gray-500">Corners</p>
                      <p className="text-lg font-bold text-gray-900">{veoCorners !== null ? veoCorners : '-'}</p>
                    </div>
                  </div>
                )}

                {veoReportMode === 'DATA' && (
                  <div className="border rounded-md p-4">
                    <h3 className="text-sm font-semibold text-gray-900 mb-2">Qualité de données</h3>
                    <div className="space-y-1 text-sm text-gray-700">
                      <p>
                        Métriques équipe: {veoTeamMetricsFilled}
                        {veoExpectedTeamMetricCells > 0 ? ` / ${veoExpectedTeamMetricCells}` : ''}
                        {veoTeamCompletionPct !== null ? ` (${veoTeamCompletionPct.toFixed(0)}%)` : ''}
                      </p>
                      <p>
                        Métriques joueurs: {veoPlayerMetricValuesFilled}
                        {veoExpectedPlayerMetricCells > 0 ? ` / ${veoExpectedPlayerMetricCells}` : ''}
                        {veoPlayerCompletionPct !== null ? ` (${veoPlayerCompletionPct.toFixed(0)}%)` : ''}
                      </p>
                    </div>
                  </div>
                )}

                {veoReportMode === 'DATA' && (
                  <div className="border rounded-md p-4">
                    <h3 className="text-sm font-semibold text-gray-900 mb-3">Comparatif équipe vs adversaire</h3>
                    <div className="overflow-auto">
                      <table className="min-w-full text-sm">
                        <thead>
                          <tr className="border-b bg-gray-50">
                            <th className="text-left py-2 px-3">Indicateur</th>
                            <th className="text-left py-2 px-3">Notre équipe</th>
                            <th className="text-left py-2 px-3">Adversaire</th>
                          </tr>
                        </thead>
                        <tbody>
                          {comparisonRows.map((row) => (
                            <tr key={row.label} className="border-b last:border-b-0">
                              <td className="py-2 px-3 font-medium text-gray-900">{row.label}</td>
                              <td className="py-2 px-3 text-gray-700">{row.ownDisplay}</td>
                              <td className="py-2 px-3 text-gray-700">{row.opponentDisplay}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {veoReportMode === 'DATA' && (
                  <>
                    <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
                      <div className="border rounded-md p-4">
                        <h3 className="text-sm font-semibold text-gray-900 mb-3">Détail métriques - notre équipe</h3>
                        {veoOwnMetrics.length === 0 ? (
                          <p className="text-sm text-gray-500">Aucune métrique équipe disponible.</p>
                        ) : (
                          <div className="space-y-2 max-h-72 overflow-auto">
                            {veoOwnMetrics.map((metric) => (
                              <div key={`${metric.metric_slug}-${metric.side}`} className="flex justify-between text-sm">
                                <span className="text-gray-600">{formatMetricLabel(metric)}</span>
                                <span className="font-semibold text-gray-900">
                                  {formatMetricValue(metric.value, metric.unit)}
                                </span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                      <div className="border rounded-md p-4">
                        <h3 className="text-sm font-semibold text-gray-900 mb-3">Détail métriques - adversaire</h3>
                        {veoOpponentMetrics.length === 0 ? (
                          <p className="text-sm text-gray-500">Aucune métrique adversaire disponible.</p>
                        ) : (
                          <div className="space-y-2 max-h-72 overflow-auto">
                            {veoOpponentMetrics.map((metric) => (
                              <div key={`${metric.metric_slug}-${metric.side}`} className="flex justify-between text-sm">
                                <span className="text-gray-600">{formatMetricLabel(metric)}</span>
                                <span className="font-semibold text-gray-900">
                                  {formatMetricValue(metric.value, metric.unit)}
                                </span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>

                    <div className="border rounded-md p-4">
                      <h3 className="text-sm font-semibold text-gray-900 mb-3">
                        Metriques joueurs ({veoPlayersTracked} joueurs suivis)
                      </h3>
                      {veoPlayersTracked === 0 || veoPlayerColumns.length === 0 ? (
                        <p className="text-sm text-gray-500">Aucune metrique joueur disponible.</p>
                      ) : (
                        <div className="overflow-auto">
                          <table className="min-w-full text-sm">
                            <thead>
                              <tr className="border-b">
                                <th className="text-left py-2 pr-3">Joueur</th>
                                {veoPlayerColumns.map((column) => (
                                  <th key={column.slug} className="text-left py-2 pr-3 whitespace-nowrap">
                                    {formatPlayerMetricLabel(column)}
                                  </th>
                                ))}
                              </tr>
                            </thead>
                            <tbody>
                              {(veoSummary.player_metrics?.players ?? []).map((player) => (
                                <tr key={player.id} className="border-b last:border-b-0">
                                  <td className="py-2 pr-3 font-medium">{player.name}</td>
                                  {veoPlayerColumns.map((column) => {
                                    const rawValue =
                                      veoSummary.player_metrics?.values?.[String(player.id)]?.[column.slug];
                                    return (
                                      <td key={`${player.id}-${column.slug}`} className="py-2 pr-3">
                                        {rawValue ?? '-'}
                                      </td>
                                    );
                                  })}
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      )}
                    </div>
                  </>
                )}
              </div>
            )}
          </div>
        )}

        {/* Display weekly report image */}
        {showWeeklyReport && weeklyReportUrl && (
          <div className="bg-white/60 rounded-lg shadow-lg p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold text-gray-900">Rapport Hebdomadaire</h2>
              <a
                href={weeklyReportUrl}
                download={`rapport-hebdo-${sessionTitle}.png`}
                className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-green-600 hover:bg-green-700"
              >
                <svg className="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                Télécharger
              </a>
            </div>
            <div className="overflow-x-auto">
              <img
                src={weeklyReportUrl}
                alt="Rapport hebdomadaire"
                className="max-w-full h-auto rounded-lg"
                onError={() => setError('Erreur lors du chargement du rapport. Aucune séance trouvée pour cette semaine.')}
              />
            </div>
          </div>
        )}
        {/* Display individual report image */}
        {showIndividualReport && individualReportUrl && (
          <div className="bg-white/60 rounded-lg shadow-lg p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold text-gray-900">Rapport Semaine Individuel</h2>
              <a
                href={individualReportUrl}
                download={`rapport-individuel-${sessionTitle}.png`}
                className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-purple-600 hover:bg-purple-700"
              >
                <svg className="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                Télécharger
              </a>
            </div>
            <div className="overflow-x-auto">
              <img
                src={individualReportUrl}
                alt="Rapport semaine individuel"
                className="max-w-full h-auto rounded-lg"
                onError={() => setError('Erreur lors du chargement du rapport individuel.')}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
