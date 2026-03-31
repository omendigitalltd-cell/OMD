import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { usePortalAuth } from "../context/PortalAuthContext";
import { Wifi, LayoutDashboard, ShoppingBag, History, Gift, Users, LogOut, Menu, X } from "lucide-react";

const navItems = [
  { path: "/portal", label: "Dashboard", icon: LayoutDashboard },
  { path: "/portal/buy", label: "Buy Plan", icon: ShoppingBag },
  { path: "/portal/history", label: "Purchases", icon: History },
  { path: "/portal/rewards", label: "Rewards", icon: Gift },
  { path: "/portal/referral", label: "Referrals", icon: Users },
];

export const PortalLayout = ({ children, title }) => {
  const { logout } = usePortalAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);

  const handleLogout = () => {
    logout();
    navigate("/portal/login");
  };

  return (
    <div className="min-h-screen bg-slate-50 flex">
      {/* Sidebar */}
      <aside className={`fixed inset-y-0 left-0 z-40 w-56 bg-slate-900 text-white transform transition-transform duration-200 lg:translate-x-0 lg:static lg:flex-shrink-0 ${mobileOpen ? "translate-x-0" : "-translate-x-full"}`}>
        <div className="p-4 border-b border-slate-700 flex items-center gap-2.5">
          <div className="w-8 h-8 bg-emerald-500 rounded-lg flex items-center justify-center">
            <Wifi className="w-4 h-4 text-white" />
          </div>
          <div>
            <h1 className="text-sm font-bold">WiFi Portal</h1>
            <p className="text-[10px] text-slate-400">My Account</p>
          </div>
        </div>
        <nav className="p-2 space-y-0.5">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = location.pathname === item.path;
            return (
              <Link
                key={item.path}
                to={item.path}
                onClick={() => setMobileOpen(false)}
                className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors ${active ? "bg-emerald-600 text-white" : "text-slate-300 hover:bg-slate-800 hover:text-white"}`}
                data-testid={`portal-nav-${item.label.toLowerCase().replace(/ /g, "-")}`}
              >
                <Icon className="w-4 h-4" />
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="absolute bottom-0 left-0 right-0 p-3">
          <button onClick={handleLogout} className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-slate-400 hover:bg-slate-800 hover:text-white w-full" data-testid="portal-logout-btn">
            <LogOut className="w-4 h-4" /> Logout
          </button>
        </div>
      </aside>

      {/* Overlay */}
      {mobileOpen && <div className="fixed inset-0 bg-black/40 z-30 lg:hidden" onClick={() => setMobileOpen(false)} />}

      {/* Main */}
      <div className="flex-1 flex flex-col min-h-screen">
        <header className="bg-white border-b border-slate-200 px-4 py-3 flex items-center gap-3 sticky top-0 z-20">
          <button className="lg:hidden" onClick={() => setMobileOpen(true)}>
            <Menu className="w-5 h-5 text-slate-600" />
          </button>
          <h2 className="text-lg font-bold text-slate-900">{title}</h2>
        </header>
        <main className="flex-1 p-4 lg:p-6 max-w-5xl w-full">
          {children}
        </main>
      </div>
    </div>
  );
};
