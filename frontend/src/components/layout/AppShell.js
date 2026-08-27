import { useCallback, useEffect, useState } from "react";
import { NavLink, useLocation } from "react-router-dom";
import {
  Activity,
  Bell,
  History,
  Image as ImageIcon,
  LayoutDashboard,
  Menu,
  MessageSquareText,
  PlayCircle,
  Send,
  Settings,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { Separator } from "@/components/ui/separator";
import { SeverityDot } from "@/components/shared/bits";
import { api, timeAgo } from "@/lib/api";

const NAV = [
  { to: "/", label: "Market", icon: LayoutDashboard, testid: "nav-dashboard" },
  { to: "/runs", label: "Pipeline", icon: PlayCircle, testid: "nav-runs" },
  {
    to: "/graphics",
    label: "Graphics",
    icon: ImageIcon,
    testid: "nav-graphics",
  },
  {
    to: "/captions",
    label: "Captions",
    icon: MessageSquareText,
    testid: "nav-captions",
  },
  {
    to: "/publishing",
    label: "Publishing",
    icon: Send,
    testid: "nav-publishing",
  },
  {
    to: "/history",
    label: "Run History",
    icon: History,
    testid: "nav-history",
  },
  {
    to: "/settings",
    label: "Settings",
    icon: Settings,
    testid: "nav-settings",
  },
];

const PAGE_TITLES = {
  "/": "Market",
  "/runs": "Pipeline",
  "/graphics": "Graphics",
  "/captions": "Captions",
  "/publishing": "Publishing",
  "/history": "Run History",
  "/settings": "Settings",
};

const NavItems = ({ onNavigate }) => (
  <nav className="flex flex-col gap-1 px-3">
    {NAV.map(({ to, label, icon: Icon, testid }) => (
      <NavLink
        key={to}
        to={to}
        end={to === "/"}
        data-testid={testid}
        onClick={onNavigate}
        className={({ isActive }) =>
          `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors duration-150 ${
            isActive
              ? "bg-secondary text-foreground"
              : "text-muted-foreground hover:bg-secondary/60 hover:text-foreground"
          }`
        }
      >
        <Icon className="h-4 w-4" />
        {label}
      </NavLink>
    ))}
  </nav>
);

const Brand = () => (
  <div className="flex items-center gap-2.5 px-6 py-5">
    <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-400/15 border border-emerald-400/30">
      <Activity className="h-4 w-4 text-emerald-400" />
    </div>
    <div>
      <div className="font-display text-sm font-bold tracking-wide">
        CGSI Automation
      </div>
      <div className="text-[10px] uppercase tracking-widest text-muted-foreground">
        Market Wrap Only
      </div>
    </div>
  </div>
);

export const AppShell = ({ children }) => {
  const location = useLocation();
  const [latestRun, setLatestRun] = useState(null);
  const [notifications, setNotifications] = useState({ items: [], unread: 0 });
  const [sheetOpen, setSheetOpen] = useState(false);

  const poll = useCallback(async () => {
    try {
      const [runRes, notifRes] = await Promise.all([
        api.get("/runs/latest"),
        api.get("/notifications?limit=15"),
      ]);
      setLatestRun(runRes.data);
      setNotifications(notifRes.data);
    } catch {
      /* backend unreachable; keep last state */
    }
  }, []);

  useEffect(() => {
    poll();
    const id = setInterval(poll, 5000);
    return () => clearInterval(id);
  }, [poll]);

  const markRead = async () => {
    if (notifications.unread > 0) {
      try {
        await api.post("/notifications/mark-read");
        setNotifications((n) => ({ ...n, unread: 0 }));
      } catch {
        /* noop */
      }
    }
  };

  return (
    <div className="flex min-h-screen bg-background">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-[248px] flex-col border-r border-border bg-card lg:flex">
        <Brand />
        <Separator className="mb-4" />
        <NavItems />
        <div className="mt-auto px-6 py-5 text-[11px] leading-relaxed text-muted-foreground">
          Note: Some data may not be accurate, please double check
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col lg:pl-[248px]">
        <header className="sticky top-0 z-20 flex h-14 items-center gap-3 border-b border-border bg-background/90 px-4 backdrop-blur sm:px-6">
          <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
            <SheetTrigger asChild>
              <Button
                data-testid="mobile-menu-button"
                variant="ghost"
                size="icon"
                className="lg:hidden"
                aria-label="Open menu"
              >
                <Menu className="h-5 w-5" />
              </Button>
            </SheetTrigger>
            <SheetContent side="left" className="w-[280px] bg-card p-0">
              <Brand />
              <Separator className="mb-4" />
              <NavItems onNavigate={() => setSheetOpen(false)} />
            </SheetContent>
          </Sheet>

          <h1 className="font-display text-base font-semibold sm:text-lg">
            {PAGE_TITLES[location.pathname] || "CGSI Automation"}
          </h1>

          <div className="ml-auto flex items-center gap-3">
           
            <Popover>
              <PopoverTrigger asChild>
                <Button
                  data-testid="notifications-open-button"
                  variant="ghost"
                  size="icon"
                  className="relative"
                  aria-label="Notifications"
                  onClick={markRead}
                >
                  <Bell className="h-4.5 w-4.5 h-5 w-5" />
                  {notifications.unread > 0 && (
                    <span
                      data-testid="notifications-unread-badge"
                      className="absolute right-1 top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-emerald-400 px-1 text-[10px] font-bold text-black"
                    >
                      {notifications.unread}
                    </span>
                  )}
                </Button>
              </PopoverTrigger>
              <PopoverContent
                align="end"
                className="w-96 border-border bg-popover p-0"
              >
                <div className="border-b border-border px-4 py-3 font-display text-sm font-semibold">
                  Notifications
                </div>
                <ScrollArea className="max-h-[380px]">
                  <div
                    data-testid="notifications-list"
                    className="flex flex-col"
                  >
                    {notifications.items.length === 0 && (
                      <div className="px-4 py-8 text-center text-sm text-muted-foreground">
                        No notifications yet
                      </div>
                    )}
                    {notifications.items.map((n) => (
                      <div
                        key={n.id}
                        className="flex gap-3 border-b border-border/60 px-4 py-3 last:border-0"
                      >
                        <SeverityDot severity={n.severity} />
                        <div className="min-w-0">
                          <div className="text-sm font-medium">{n.title}</div>
                          <div className="mt-0.5 text-xs leading-relaxed text-muted-foreground">
                            {n.message}
                          </div>
                          <div className="mt-1 text-[11px] text-muted-foreground/70">
                            {timeAgo(n.created_at)}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              </PopoverContent>
            </Popover>
          </div>
        </header>

        <main className="mx-auto w-full max-w-[1400px] flex-1 px-4 py-6 sm:px-6 lg:px-8">
          {children}
        </main>
      </div>
    </div>
  );
};
