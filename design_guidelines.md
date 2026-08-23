{
  "brand": {
    "product_name": "PSE Daily Pulse",
    "tagline": "Reliable data → correct analysis → beautiful graphics → minimal manual work",
    "brand_attributes": [
      "institutional",
      "data-forward",
      "calm under pressure",
      "trustworthy",
      "fast to scan",
      "operator-first"
    ],
    "visual_personality": {
      "style_fusion": [
        "Nocturnal finance terminal (dark navy surfaces + hairline borders)",
        "Swiss-style information hierarchy (tight grids, strong alignment)",
        "Bento-card ops dashboard (dense but breathable)",
        "Subtle grain/noise + restrained glow accents (only for status)"
      ],
      "do_not": [
        "No purple for AI features",
        "No decorative gradients on reading areas",
        "No transparent popovers/modals",
        "No centered app container",
        "No emoji icons"
      ]
    }
  },

  "typography": {
    "google_fonts": {
      "heading": {
        "family": "Space Grotesk",
        "weights": [400, 500, 600, 700],
        "usage": "Page titles, KPI numbers, section headers"
      },
      "body": {
        "family": "Inter",
        "weights": [400, 500, 600],
        "usage": "Body text, labels, tables, forms"
      },
      "numbers": {
        "family": "IBM Plex Mono",
        "weights": [400, 500, 600],
        "usage": "All prices, % changes, volumes, timings, run IDs (tabular alignment)"
      }
    },
    "tailwind_font_setup": {
      "instructions": [
        "Add Google Fonts <link> tags in public/index.html for Space Grotesk + Inter + IBM Plex Mono.",
        "In tailwind.config.js extend fontFamily: { sans: ['Inter', 'system-ui'], display: ['Space Grotesk','Inter'], mono: ['IBM Plex Mono','ui-monospace'] }",
        "Use className='font-display' for headings, 'font-sans' for body, 'font-mono tabular-nums' for numeric cells."
      ]
    },
    "type_scale": {
      "h1": "text-4xl sm:text-5xl lg:text-6xl font-display tracking-tight",
      "h2": "text-base md:text-lg font-sans text-muted-foreground",
      "section_title": "text-sm font-sans font-semibold tracking-wide uppercase",
      "kpi_value": "text-3xl sm:text-4xl font-display tracking-tight",
      "table": "text-sm font-sans",
      "mono_metric": "text-sm font-mono tabular-nums",
      "caption_editor": "text-sm leading-6 font-sans"
    }
  },

  "color_system": {
    "mode": "dark-first (finance ops)",
    "notes": [
      "Dashboard should feel cohesive with exported graphics (dark navy #0a0f1e), but use slightly lighter surfaces for readability.",
      "Use emerald for gains and red for losses; never use these as large background fills.",
      "All popovers/dialogs must be solid (no transparency)."
    ],
    "tokens_css": {
      "path": "/app/frontend/src/index.css",
      "instructions": [
        "Replace :root and .dark HSL tokens with the palette below.",
        "Default the app to dark by adding 'dark' class on <html> or root wrapper (implementation choice)."
      ],
      "css_variables": {
        ":root": {
          "--background": "222 47% 98%",
          "--foreground": "222 47% 11%",
          "--card": "0 0% 100%",
          "--card-foreground": "222 47% 11%",
          "--popover": "0 0% 100%",
          "--popover-foreground": "222 47% 11%",
          "--primary": "222 47% 11%",
          "--primary-foreground": "0 0% 98%",
          "--secondary": "220 14% 96%",
          "--secondary-foreground": "222 47% 11%",
          "--muted": "220 14% 96%",
          "--muted-foreground": "220 9% 46%",
          "--accent": "220 14% 96%",
          "--accent-foreground": "222 47% 11%",
          "--destructive": "0 84% 60%",
          "--destructive-foreground": "0 0% 98%",
          "--border": "220 13% 91%",
          "--input": "220 13% 91%",
          "--ring": "222 47% 11%",
          "--radius": "0.75rem",
          "--chart-1": "160 84% 39%",
          "--chart-2": "0 84% 60%",
          "--chart-3": "210 90% 56%",
          "--chart-4": "43 96% 56%",
          "--chart-5": "262 83% 58%"
        },
        ".dark": {
          "--background": "225 52% 7%",
          "--foreground": "210 40% 98%",
          "--card": "224 45% 10%",
          "--card-foreground": "210 40% 98%",
          "--popover": "224 45% 10%",
          "--popover-foreground": "210 40% 98%",
          "--primary": "210 40% 98%",
          "--primary-foreground": "225 52% 7%",
          "--secondary": "223 34% 14%",
          "--secondary-foreground": "210 40% 98%",
          "--muted": "223 34% 14%",
          "--muted-foreground": "215 20% 70%",
          "--accent": "223 34% 14%",
          "--accent-foreground": "210 40% 98%",
          "--destructive": "0 72% 52%",
          "--destructive-foreground": "210 40% 98%",
          "--border": "223 28% 18%",
          "--input": "223 28% 18%",
          "--ring": "160 84% 39%",
          "--radius": "0.75rem",
          "--chart-1": "160 84% 39%",
          "--chart-2": "0 72% 52%",
          "--chart-3": "210 90% 56%",
          "--chart-4": "43 96% 56%",
          "--chart-5": "188 86% 45%"
        }
      },
      "semantic_hex_reference": {
        "bg_canvas": "#070B16",
        "bg_card": "#0B1224",
        "bg_card_2": "#0E1830",
        "border_hairline": "#1B2A44",
        "text_primary": "#EAF0FF",
        "text_muted": "#A9B6D3",
        "gain": "#2EE59D",
        "loss": "#FF5C6C",
        "warning": "#F6C177",
        "info": "#4DA3FF"
      }
    },
    "gradients_and_texture": {
      "allowed_gradients": [
        "Hero-only atmospheric wash: linear-gradient(135deg, rgba(77,163,255,0.10), rgba(46,229,157,0.06), rgba(7,11,22,0))",
        "Section accent strip (max 12% height): linear-gradient(90deg, rgba(46,229,157,0.10), rgba(77,163,255,0.08))"
      ],
      "noise_overlay": {
        "css_snippet": ".noise-overlay{position:absolute;inset:0;pointer-events:none;background-image:url('data:image/svg+xml;utf8,<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"120\" height=\"120\"><filter id=\"n\"><feTurbulence type=\"fractalNoise\" baseFrequency=\"0.9\" numOctaves=\"3\" stitchTiles=\"stitch\"/></filter><rect width=\"120\" height=\"120\" filter=\"url(%23n)\" opacity=\"0.08\"/></svg>');mix-blend-mode:overlay;opacity:.35}",
        "usage": "Only on large background containers (page canvas / hero). Never on tables or caption text areas."
      }
    }
  },

  "layout_and_grid": {
    "app_shell": {
      "pattern": "Collapsible left sidebar + top header (search, run status pill, notifications)",
      "sidebar_width": {
        "collapsed": "w-[72px]",
        "expanded": "w-[264px]"
      },
      "content_container": "max-w-[1400px]",
      "page_padding": "px-4 sm:px-6 lg:px-8 py-6",
      "grid": {
        "dashboard": "grid grid-cols-1 lg:grid-cols-12 gap-6",
        "left_main": "lg:col-span-8",
        "right_rail": "lg:col-span-4"
      },
      "density_rules": [
        "Use 2–3x more spacing than feels comfortable: cards get p-5 on mobile, p-6 on desktop.",
        "Prefer 1px borders over heavy shadows; shadows only for floating layers (dialogs, dropdowns)."
      ]
    },
    "page_skeletons": {
      "1_dashboard_today": {
        "top_row": [
          "KPI Hero Card: PSEi value + change + timestamp + market breadth chips",
          "Latest Run Status Widget: stage + elapsed + CTA to Runs"
        ],
        "middle": [
          "Sector Performance Strip (6 sectors) with mini bars",
          "Top Gainers / Top Losers / Most Active tables (tabs)"
        ],
        "right_rail": [
          "Notifications feed (latest 8)",
          "Dividend disclosures list (latest 6)",
          "REIT board compact table"
        ]
      },
      "2_pipeline_runs": {
        "layout": [
          "Run control header: Trigger Run button + schedule badge + last successful run",
          "Live stage progress: Fetch → Validate → Compute → Store → Graphics → Captions → QA → Ready",
          "Run detail panel: timings, counts, errors, logs (collapsible)"
        ]
      },
      "3_graphics": {
        "layout": [
          "Gallery grid 1-col mobile / 2-col md / 3-col xl",
          "Each card: PNG preview (AspectRatio), metadata (1080x1350), Download button, 'Open full' dialog"
        ]
      },
      "4_captions": {
        "layout": [
          "Platform tabs (Instagram/Facebook/LinkedIn/X)",
          "Caption card: provider/model pill, regenerate, copy, edit textarea, character count, last updated"
        ]
      },
      "5_publishing": {
        "layout": [
          "Kanban-lite board per platform: Pending → Exported → Published",
          "Each platform card shows: graphics downloaded? captions copied? timestamp + operator notes"
        ]
      },
      "6_run_history": {
        "layout": [
          "Filter row: date range (Calendar), status select, provider select",
          "Table: run_id, date, status, duration, errors, exported platforms, actions"
        ]
      },
      "7_settings": {
        "layout": [
          "LLM provider/model switcher (Select + RadioGroup)",
          "Daily schedule time (Input + timezone label)",
          "REIT ticker list management (Table + inline add/remove)",
          "Danger zone: reset cache / clear runs (AlertDialog)"
        ]
      }
    }
  },

  "components": {
    "component_path": {
      "shell": [
        "/app/frontend/src/components/ui/sheet.jsx (mobile sidebar)",
        "/app/frontend/src/components/ui/navigation-menu.jsx (optional top nav)",
        "/app/frontend/src/components/ui/breadcrumb.jsx",
        "/app/frontend/src/components/ui/scroll-area.jsx"
      ],
      "core": [
        "/app/frontend/src/components/ui/button.jsx",
        "/app/frontend/src/components/ui/card.jsx",
        "/app/frontend/src/components/ui/badge.jsx",
        "/app/frontend/src/components/ui/separator.jsx",
        "/app/frontend/src/components/ui/tabs.jsx",
        "/app/frontend/src/components/ui/table.jsx",
        "/app/frontend/src/components/ui/progress.jsx",
        "/app/frontend/src/components/ui/skeleton.jsx"
      ],
      "overlays": [
        "/app/frontend/src/components/ui/dialog.jsx",
        "/app/frontend/src/components/ui/alert-dialog.jsx",
        "/app/frontend/src/components/ui/dropdown-menu.jsx",
        "/app/frontend/src/components/ui/popover.jsx",
        "/app/frontend/src/components/ui/tooltip.jsx"
      ],
      "forms": [
        "/app/frontend/src/components/ui/input.jsx",
        "/app/frontend/src/components/ui/textarea.jsx",
        "/app/frontend/src/components/ui/select.jsx",
        "/app/frontend/src/components/ui/switch.jsx",
        "/app/frontend/src/components/ui/radio-group.jsx",
        "/app/frontend/src/components/ui/calendar.jsx",
        "/app/frontend/src/components/ui/checkbox.jsx"
      ],
      "notifications": [
        "/app/frontend/src/components/ui/sonner.jsx (toast)"
      ]
    },
    "custom_components_to_create_js": {
      "instructions": "Create these as .js components (not .tsx). Use named exports. Keep them small and composable.",
      "list": [
        {
          "name": "AppShell",
          "path": "/app/frontend/src/components/layout/AppShell.js",
          "purpose": "Sidebar + header + content slot; handles mobile Sheet sidebar"
        },
        {
          "name": "KpiCard",
          "path": "/app/frontend/src/components/dashboard/KpiCard.js",
          "purpose": "Metric tile with value, delta, sparkline slot, and status dot"
        },
        {
          "name": "PipelineStageRail",
          "path": "/app/frontend/src/components/runs/PipelineStageRail.js",
          "purpose": "Horizontal stage tracker with per-stage status, duration, and error count"
        },
        {
          "name": "RunStatusPill",
          "path": "/app/frontend/src/components/runs/RunStatusPill.js",
          "purpose": "Compact status indicator used in header and tables"
        },
        {
          "name": "PngPreviewCard",
          "path": "/app/frontend/src/components/graphics/PngPreviewCard.js",
          "purpose": "Preview + download + open dialog; uses AspectRatio"
        },
        {
          "name": "CaptionPlatformCard",
          "path": "/app/frontend/src/components/captions/CaptionPlatformCard.js",
          "purpose": "Textarea editor with copy/regenerate, char count, provider/model"
        },
        {
          "name": "PublishingBoard",
          "path": "/app/frontend/src/components/publishing/PublishingBoard.js",
          "purpose": "Per-platform status tracking board (pending/exported/published)"
        },
        {
          "name": "NotificationPanel",
          "path": "/app/frontend/src/components/notifications/NotificationPanel.js",
          "purpose": "Header dropdown/panel with event list + severity badges"
        }
      ]
    }
  },

  "component_behaviors_and_states": {
    "buttons": {
      "shape": "Professional / Corporate: radius 10–12px (use --radius 0.75rem)",
      "variants": {
        "primary": {
          "usage": "Trigger Run, Approve Run, Download All",
          "tailwind": "bg-primary text-primary-foreground hover:bg-primary/90 active:bg-primary/85",
          "focus": "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
        },
        "secondary": {
          "usage": "Regenerate caption, Open details",
          "tailwind": "bg-secondary text-secondary-foreground hover:bg-secondary/80"
        },
        "ghost": {
          "usage": "Copy, icon-only actions",
          "tailwind": "hover:bg-accent hover:text-accent-foreground"
        },
        "destructive": {
          "usage": "Clear runs, reset cache",
          "tailwind": "bg-destructive text-destructive-foreground hover:bg-destructive/90"
        }
      },
      "micro_interactions": [
        "On hover: subtle brightness increase + border emphasis (not scale on dense tables).",
        "On press: scale-0.98 only for primary CTAs (Trigger Run) to feel tactile.",
        "Loading: show spinner + keep width stable (use inline-flex gap-2)."
      ]
    },
    "status_badges": {
      "rule": "Never rely on color alone; always pair with label + icon/dot.",
      "statuses": {
        "running": {"label": "Running", "dot": "bg-info", "badge": "bg-info/15 text-info border border-info/30"},
        "success": {"label": "Success", "dot": "bg-[color:var(--gain)]", "badge": "bg-emerald-400/15 text-emerald-200 border border-emerald-400/30"},
        "failed": {"label": "Failed", "dot": "bg-[color:var(--loss)]", "badge": "bg-rose-400/15 text-rose-200 border border-rose-400/30"},
        "stale": {"label": "Stale", "dot": "bg-warning", "badge": "bg-amber-400/15 text-amber-200 border border-amber-400/30"}
      }
    },
    "tables": {
      "density": "Compact rows (h-10) with sticky header on long lists",
      "numeric": "Right-align numeric columns; use font-mono tabular-nums",
      "row_hover": "hover:bg-accent/40",
      "empty_state": "Use Card with icon + explanation + primary CTA (Trigger first run)"
    },
    "pipeline_progress": {
      "visual": "Stage rail with connected nodes; each node shows status dot + stage name + duration",
      "error_handling": "If stage fails: highlight node + show error summary in collapsible panel; provide 'Copy error' button",
      "timing": "Always show elapsed time per stage in mono"
    },
    "graphics_gallery": {
      "preview": "Use AspectRatio 4/5 for 1080x1350; show skeleton while loading",
      "download": "Primary button per card + 'Download all' in page header",
      "qa": "Add 'Approved' toggle per graphic (Switch) before publishing"
    },
    "captions": {
      "editing": "Inline edit with autosave indicator (Badge: Saved/Saving/Error)",
      "copy": "Copy button uses sonner toast 'Copied to clipboard'",
      "regenerate": "Regenerate opens Dialog with provider/model + temperature (optional) and a warning about overwriting edits"
    },
    "notifications": {
      "severity": "Info/Warning/Error badges; newest first",
      "unread": "Unread dot + count badge in header",
      "actions": "Each notification can link to Run detail (button/link)"
    },
    "market_closed_state": {
      "banner": "Top-of-page Alert: 'Market closed (Weekend/Holiday) — showing last trading day data' with date",
      "behavior": "Disable Trigger Run unless operator explicitly confirms (AlertDialog)"
    }
  },

  "motion": {
    "principles": [
      "Motion communicates state changes (running → success/fail), not decoration.",
      "Prefer opacity/translateY for entrances; avoid large scaling in dense data views.",
      "Respect prefers-reduced-motion."
    ],
    "recommended_library": {
      "name": "framer-motion",
      "install": "npm i framer-motion",
      "usage": [
        "Stagger card entrances on Dashboard",
        "Animate pipeline stage dots (pulse for running)",
        "Animate toast/notification panel presence"
      ]
    },
    "micro_animation_specs": {
      "card_enter": "initial={{opacity:0,y:8}} animate={{opacity:1,y:0}} transition={{duration:0.25}}",
      "running_pulse": "Use CSS animate-pulse on status dot only (not whole row)",
      "hover": "transition-colors duration-150 on buttons/rows; no transition: all"
    }
  },

  "data_viz": {
    "library": {
      "name": "recharts",
      "usage": [
        "Tiny sparklines in KPI cards (7–14 points)",
        "Sector strip mini bars",
        "Run duration trend in Run History"
      ]
    },
    "chart_style": {
      "grid": "Very subtle (stroke border_hairline at 30% opacity)",
      "lines": "2px, rounded, use chart tokens",
      "tooltips": "Use shadcn Tooltip/Popover with solid background (popover token)"
    }
  },

  "accessibility": {
    "requirements": [
      "WCAG AA contrast for text on dark surfaces",
      "Visible focus rings on all interactive elements",
      "Keyboard navigable sidebar + tables + dialogs",
      "Do not rely on color alone for gain/loss; include arrows/icons + labels",
      "Use aria-label for icon-only buttons"
    ],
    "number_formatting": [
      "Always show sign (+/-) for % change",
      "Use consistent decimals (index: 2dp, %: 2dp, volume: abbreviate with K/M/B but allow hover to show full)"
    ]
  },

  "testing_attributes": {
    "rule": "All interactive and key informational elements MUST include data-testid (kebab-case, role-based).",
    "examples": [
      "data-testid='trigger-run-button'",
      "data-testid='pipeline-stage-fetch-status'",
      "data-testid='graphics-market-summary-download-button'",
      "data-testid='caption-instagram-textarea'",
      "data-testid='caption-x-copy-button'",
      "data-testid='publishing-linkedin-mark-exported-button'",
      "data-testid='run-history-filter-status-select'",
      "data-testid='notifications-open-button'",
      "data-testid='psei-hero-value'"
    ]
  },

  "image_urls": {
    "note": "This is an ops dashboard; keep imagery minimal. Use abstract finance textures only in hero/empty states.",
    "categories": {
      "empty_state_illustration": {
        "description": "Subtle abstract chart/terminal vibe for first-run empty state (optional).",
        "urls": []
      },
      "settings_help": {
        "description": "Tiny inline illustration for LLM provider help dialog (optional).",
        "urls": []
      }
    }
  },

  "instructions_to_main_agent": {
    "global": [
      "Remove CRA default App.css centering patterns; do not use .App { text-align:center }.",
      "Adopt dark-first tokens in index.css and ensure popovers/dialogs are solid backgrounds.",
      "Use Space Grotesk + Inter + IBM Plex Mono; apply mono + tabular-nums to all numeric cells.",
      "Implement an AppShell with sidebar + header; mobile sidebar uses Sheet.",
      "Use shadcn/ui components from /src/components/ui only (no raw HTML dropdowns/calendars/toasts).",
      "Use sonner for toasts.",
      "Add data-testid to every interactive/key info element.",
      "Keep gradients under 20% viewport and only as atmospheric background accents."
    ],
    "page_specific": {
      "dashboard_today": [
        "KPI hero card: PSEi value + delta + timestamp + breadth chips.",
        "Sector strip: 6 cards in horizontal ScrollArea on mobile.",
        "Movers tables: Tabs for Gainers/Losers/Most Active; sticky header."
      ],
      "pipeline_runs": [
        "Stage rail with per-stage duration + error count.",
        "Provide 'Copy error' and 'View logs' collapsible sections."
      ],
      "graphics": [
        "Use AspectRatio 4/5 previews; download buttons per card + bulk download.",
        "Add QA toggle per graphic before publishing."
      ],
      "captions": [
        "Platform tabs; each card has copy/regenerate/edit.",
        "Regenerate confirmation dialog to prevent overwriting edits."
      ],
      "publishing": [
        "Per-platform status tracking with timestamps and notes.",
        "Make statuses explicit (Pending/Exported/Published) with badges + icons."
      ],
      "settings": [
        "Provider/model switcher; schedule time; REIT tickers table.",
        "Danger zone actions behind AlertDialog."
      ]
    }
  },

  "references_used": {
    "inspiration": [
      {
        "source": "shadcn.io Dashboard Data Pipeline block",
        "url": "https://www.shadcn.io/blocks/dashboard-data-pipeline",
        "takeaways": [
          "Stage/status visualization patterns",
          "Status dots + error counts",
          "Framer-motion staggered entrances"
        ]
      },
      {
        "source": "shadcn.io Monitoring dbt Run History block",
        "url": "https://www.shadcn.io/blocks/monitoring-dbt-run-history",
        "takeaways": [
          "Run history monitoring mental model",
          "Failure/outlier emphasis",
          "Ops-friendly density"
        ]
      },
      {
        "source": "ReUI dashboard blocks overview",
        "url": "https://reui.io/blocks/application/dashboard",
        "takeaways": [
          "3-layer dashboard composition: KPI row + chart layer + action table",
          "App shell chrome patterns",
          "Searchable grids and filters"
        ]
      }
    ]
  },

  "general_ui_ux_design_guidelines": [
    "You must not apply universal transition. Eg: transition: all. This results in breaking transforms. Always add transitions for specific interactive elements like button, input excluding transforms",
    "You must not center align the app container, ie do not add .App { text-align: center; } in the css file. This disrupts the human natural reading flow of text",
    "NEVER: use AI assistant Emoji characters like🤖🧠💭💡🔮🎯📚🎭🎬🎪🎉🎊🎁🎀🎂🍰🎈🎨🎰💰💵💳🏦💎🪙💸🤑📊📈📉💹🔢🏆🥇 etc for icons. Always use FontAwesome cdn or lucid-react library already installed in the package.json",
    "GRADIENT RESTRICTION RULE",
    "NEVER use dark/saturated gradient combos (e.g., purple/pink) on any UI element. Prohibited gradients: blue-500 to purple 600, purple 500 to pink-500, green-500 to blue-500, red to pink etc",
    "NEVER use dark gradients for logo, testimonial, footer etc",
    "NEVER let gradients cover more than 20% of the viewport.",
    "NEVER apply gradients to text-heavy content or reading areas.",
    "NEVER use gradients on small UI elements (<100px width).",
    "NEVER stack multiple gradient layers in the same viewport.",
    "ENFORCEMENT RULE:",
    "Id gradient area exceeds 20% of viewport OR affects readability, THEN use solid colors",
    "How and where to use:",
    "Section backgrounds (not content backgrounds)",
    "Hero section header content. Eg: dark to light to dark color",
    "Decorative overlays and accent elements only",
    "Hero section with 2-3 mild color",
    "Gradients creation can be done for any angle say horizontal, vertical or diagonal",
    "For AI chat, voice application, do not use purple color. Use color like light green, ocean blue, peach orange etc",
    "Every interaction needs micro-animations - hover states, transitions, parallax effects, and entrance animations. Static = dead.",
    "Use 2-3x more spacing than feels comfortable. Cramped designs look cheap.",
    "Subtle grain textures, noise overlays, custom cursors, selection states, and loading animations: separates good from extraordinary.",
    "Before generating UI, infer the visual style from the problem statement (palette, contrast, mood, motion) and immediately instantiate it by setting global design tokens (primary, secondary/accent, background, foreground, ring, state colors), rather than relying on any library defaults. Don't make the background dark as a default step, always understand problem first and define colors accordingly",
    "Component Reuse:",
    "Prioritize using pre-existing components from src/components/ui when applicable",
    "Create new components that match the style and conventions of existing components when needed",
    "Examine existing components to understand the project's component patterns before creating new ones",
    "IMPORTANT: Do not use HTML based component like dropdown, calendar, toast etc. You MUST always use /app/frontend/src/components/ui/ only as a primary components as these are modern and stylish component",
    "Best Practices:",
    "Use Shadcn/UI as the primary component library for consistency and accessibility",
    "Import path: ./components/[component-name]",
    "Export Conventions:",
    "Components MUST use named exports (export const ComponentName = ...)",
    "Pages MUST use default exports (export default function PageName() {...})",
    "Toasts:",
    "Use sonner for toasts",
    "Sonner component are located in /app/src/components/ui/sonner.tsx",
    "Use 2–4 color gradients, subtle textures/noise overlays, or CSS-based noise to avoid flat visuals."
  ]
}
