import { useState, useEffect } from "react";
import { Layout } from "../components/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { useAuth } from "../context/AuthContext";
import axios from "axios";
import {
  Users, Wifi, DollarSign, MessageSquare, Clock, CheckCircle,
  Calculator, Calendar, MapPin, TrendingUp, BarChart3, UserCheck,
} from "lucide-react";

const API_URL = process.env.REACT_APP_BACKEND_URL;

const MONTH_NAMES = [
  "", "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December"
];

const StatCard = ({ title, value, icon: Icon, color, subtitle }) => (
  <Card className="metric-card border-slate-200 bg-white" data-testid={`stat-${title.toLowerCase().replace(/\s+/g, '-')}`}>
    <CardContent className="p-6">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-medium text-slate-500">{title}</p>
          <p className={`text-3xl font-extrabold font-heading mt-1 ${color}`}>{value}</p>
          {subtitle && <p className="text-xs text-slate-400 mt-1">{subtitle}</p>}
        </div>
        <div className={`p-3 rounded-xl ${color.includes('violet') ? 'bg-violet-100' : color.includes('orange') ? 'bg-orange-100' : color.includes('emerald') ? 'bg-emerald-100' : 'bg-slate-100'}`}>
          <Icon className={`w-6 h-6 ${color}`} />
        </div>
      </div>
    </CardContent>
  </Card>
);

const formatMonth = (key) => {
  if (!key) return "";
  const [y, m] = key.split("-");
  return `${MONTH_NAMES[parseInt(m)]} ${y}`;
};

export default function Dashboard() {
  const { getAuthHeader } = useAuth();
  const [stats, setStats] = useState(null);
  const [analytics, setAnalytics] = useState(null);
  const [recentCustomers, setRecentCustomers] = useState([]);
  const [recentReminders, setRecentReminders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [todayProrata, setTodayProrata] = useState({ threeDevice: null, fourDevice: null });

  useEffect(() => {
    const fetchData = async () => {
      try {
        const today = new Date();
        const currentDay = today.getDate();
        const currentMonth = today.getMonth() + 1;
        const currentYear = today.getFullYear();

        const [statsRes, customersRes, remindersRes, prorata3Res, prorata4Res, analyticsRes] = await Promise.all([
          axios.get(`${API_URL}/api/dashboard/stats`, getAuthHeader()),
          axios.get(`${API_URL}/api/dashboard/recent-customers`, getAuthHeader()),
          axios.get(`${API_URL}/api/dashboard/recent-reminders`, getAuthHeader()),
          axios.post(`${API_URL}/api/prorata/calculate`, {
            start_day: currentDay, month: currentMonth, year: currentYear, plan: "3_devices"
          }, getAuthHeader()),
          axios.post(`${API_URL}/api/prorata/calculate`, {
            start_day: currentDay, month: currentMonth, year: currentYear, plan: "4_devices"
          }, getAuthHeader()),
          axios.get(`${API_URL}/api/dashboard/analytics`, getAuthHeader()),
        ]);
        setStats(statsRes.data);
        setRecentCustomers(customersRes.data);
        setRecentReminders(remindersRes.data);
        setTodayProrata({ threeDevice: prorata3Res.data, fourDevice: prorata4Res.data });
        setAnalytics(analyticsRes.data);
      } catch (error) {
        console.error("Failed to fetch dashboard data:", error);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [getAuthHeader]);

  if (loading) {
    return (
      <Layout title="Dashboard">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {[1, 2, 3, 4].map((i) => (
            <Card key={i} className="animate-pulse">
              <CardContent className="p-6"><div className="h-20 bg-slate-200 rounded" /></CardContent>
            </Card>
          ))}
        </div>
      </Layout>
    );
  }

  const maxLocationRev = analytics?.revenue_by_location?.[0]?.revenue || 1;
  const maxMonthlyRev = Math.max(...(analytics?.monthly_growth?.map(m => m.revenue) || [1]));

  return (
    <Layout title="Dashboard">
      <div className="space-y-8" data-testid="dashboard-content">
        {/* Today's Pro-rata Preview */}
        <Card className="border-slate-200 bg-gradient-to-br from-violet-600 to-violet-700 text-white" data-testid="prorata-preview-card">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg font-bold font-heading flex items-center gap-2 text-white">
              <Calculator className="w-5 h-5" />
              Today's Pro-rata Rates
              <Badge className="bg-white/20 text-white ml-2">
                <Calendar className="w-3 h-3 mr-1" />
                Day {todayProrata.threeDevice?.start_day || new Date().getDate()} of {MONTH_NAMES[todayProrata.threeDevice?.month || (new Date().getMonth() + 1)]}
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-violet-200 mb-4">If a customer signs up today, they pay:</p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-white/10 backdrop-blur-sm rounded-xl p-5 border border-white/20">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2"><Wifi className="w-5 h-5" /><span className="font-semibold">3 Devices</span></div>
                  <Badge className="bg-white/20 text-white">R200/month</Badge>
                </div>
                <p className="text-4xl font-extrabold font-mono" data-testid="prorata-3-devices">R{todayProrata.threeDevice?.prorata_amount?.toFixed(2) || "0.00"}</p>
                <p className="text-sm text-violet-200 mt-2">For {todayProrata.threeDevice?.days_used || 0} remaining days</p>
                <div className="mt-3 pt-3 border-t border-white/20 text-xs text-violet-200">Daily rate: R{todayProrata.threeDevice?.daily_rate?.toFixed(2) || "0.00"}</div>
              </div>
              <div className="bg-orange-500/30 backdrop-blur-sm rounded-xl p-5 border border-orange-400/30">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2"><Wifi className="w-5 h-5" /><span className="font-semibold">4 Devices</span></div>
                  <Badge className="bg-orange-500/50 text-white">R300/month</Badge>
                </div>
                <p className="text-4xl font-extrabold font-mono" data-testid="prorata-4-devices">R{todayProrata.fourDevice?.prorata_amount?.toFixed(2) || "0.00"}</p>
                <p className="text-sm text-violet-200 mt-2">For {todayProrata.fourDevice?.days_used || 0} remaining days</p>
                <div className="mt-3 pt-3 border-t border-white/20 text-xs text-violet-200">Daily rate: R{todayProrata.fourDevice?.daily_rate?.toFixed(2) || "0.00"}</div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <StatCard title="Total Customers" value={stats?.total_customers || 0} icon={Users} color="text-violet-600" subtitle={`${stats?.active_customers || 0} active`} />
          <StatCard title="Total Revenue" value={`R${analytics?.total_revenue?.toLocaleString() || 0}`} icon={DollarSign} color="text-emerald-600" subtitle={`${analytics?.total_paying_users || 0} paying users`} />
          <StatCard title="Avg Spend/User" value={`R${analytics?.avg_spend_per_user || 0}`} icon={UserCheck} color="text-violet-600" subtitle="Per paying user" />
          <StatCard title="Est. Monthly" value={`R${stats?.estimated_monthly_revenue?.toLocaleString() || 0}`} icon={TrendingUp} color="text-orange-500" subtitle="Subscriptions" />
        </div>

        {/* Revenue per Location + Monthly Growth */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Revenue per Location */}
          <Card className="border-slate-200 bg-white" data-testid="revenue-by-location">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg font-bold font-heading flex items-center gap-2">
                <MapPin className="w-5 h-5 text-violet-600" />
                Revenue per Location
              </CardTitle>
            </CardHeader>
            <CardContent>
              {analytics?.revenue_by_location?.length > 0 ? (
                <div className="space-y-4">
                  {analytics.revenue_by_location.map((loc, i) => (
                    <div key={i} data-testid={`location-row-${i}`}>
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm font-medium text-slate-700">{loc.location}</span>
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-slate-400">{loc.count} sales</span>
                          <span className="font-bold text-sm text-slate-900">R{loc.revenue.toLocaleString()}</span>
                        </div>
                      </div>
                      <div className="w-full bg-slate-100 rounded-full h-3">
                        <div
                          className="h-3 rounded-full bg-gradient-to-r from-violet-500 to-violet-600 transition-all duration-500"
                          style={{ width: `${Math.max((loc.revenue / maxLocationRev) * 100, 4)}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-slate-400 py-8 text-center">No sales data yet</p>
              )}
            </CardContent>
          </Card>

          {/* Monthly Growth */}
          <Card className="border-slate-200 bg-white" data-testid="monthly-growth">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg font-bold font-heading flex items-center gap-2">
                <BarChart3 className="w-5 h-5 text-emerald-600" />
                Monthly Growth
              </CardTitle>
            </CardHeader>
            <CardContent>
              {analytics?.monthly_growth?.length > 0 ? (
                <div className="space-y-4">
                  {analytics.monthly_growth.map((m, i) => (
                    <div key={i} data-testid={`month-row-${i}`}>
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm font-medium text-slate-700">{formatMonth(m.month)}</span>
                        <div className="flex items-center gap-2">
                          {m.growth_pct !== 0 && i > 0 && (
                            <Badge className={m.growth_pct > 0 ? "bg-emerald-100 text-emerald-700" : "bg-red-100 text-red-700"}>
                              {m.growth_pct > 0 ? "+" : ""}{m.growth_pct}%
                            </Badge>
                          )}
                          <span className="text-xs text-slate-400">{m.purchases} sales</span>
                          <span className="font-bold text-sm text-slate-900">R{m.revenue.toLocaleString()}</span>
                        </div>
                      </div>
                      <div className="w-full bg-slate-100 rounded-full h-3">
                        <div
                          className="h-3 rounded-full bg-gradient-to-r from-emerald-400 to-emerald-600 transition-all duration-500"
                          style={{ width: `${Math.max((m.revenue / maxMonthlyRev) * 100, 4)}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-slate-400 py-8 text-center">No monthly data yet</p>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Reminder Stats */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Card className="metric-card border-slate-200 bg-white" data-testid="pending-reminders-card">
            <CardContent className="p-6">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-amber-100 rounded-xl"><Clock className="w-6 h-6 text-amber-600" /></div>
                <div>
                  <p className="text-sm font-medium text-slate-500">Pending Reminders</p>
                  <p className="text-2xl font-bold text-amber-600">{stats?.pending_reminders || 0}</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card className="metric-card border-slate-200 bg-white" data-testid="sent-reminders-card">
            <CardContent className="p-6">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-emerald-100 rounded-xl"><CheckCircle className="w-6 h-6 text-emerald-600" /></div>
                <div>
                  <p className="text-sm font-medium text-slate-500">Sent Reminders</p>
                  <p className="text-2xl font-bold text-emerald-600">{stats?.sent_reminders || 0}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Recent Activity */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card className="border-slate-200 bg-white" data-testid="recent-customers-card">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg font-bold font-heading flex items-center gap-2">
                <Users className="w-5 h-5 text-violet-600" />
                Recent Purchases
              </CardTitle>
            </CardHeader>
            <CardContent>
              {recentCustomers.length === 0 ? (
                <p className="text-slate-500 text-sm py-4 text-center">No purchases yet</p>
              ) : (
                <div className="space-y-3">
                  {recentCustomers.map((customer, index) => (
                    <div key={customer.id} className="flex items-center justify-between p-3 bg-slate-50 rounded-lg animate-fade-in" style={{ animationDelay: `${index * 0.1}s` }} data-testid={`customer-row-${customer.id}`}>
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-violet-600 rounded-full flex items-center justify-center text-white font-bold">{customer.name?.charAt(0).toUpperCase() || "?"}</div>
                        <div>
                          <p className="font-medium text-slate-900">{customer.name}</p>
                          <p className="text-xs text-slate-500 font-mono">{customer.phone}</p>
                        </div>
                      </div>
                      <div className="text-right">
                        <Badge className="bg-emerald-100 text-emerald-700">R{customer.amount}</Badge>
                        {customer.accommodation && <p className="text-[10px] text-slate-400 mt-1">{customer.accommodation}</p>}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          <Card className="border-slate-200 bg-white" data-testid="recent-reminders-card">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg font-bold font-heading flex items-center gap-2">
                <MessageSquare className="w-5 h-5 text-violet-600" />
                Recent Reminders
              </CardTitle>
            </CardHeader>
            <CardContent>
              {recentReminders.length === 0 ? (
                <p className="text-slate-500 text-sm py-4 text-center">No reminders yet</p>
              ) : (
                <div className="space-y-3">
                  {recentReminders.map((reminder, index) => (
                    <div key={reminder.id} className="flex items-center justify-between p-3 bg-slate-50 rounded-lg animate-fade-in" style={{ animationDelay: `${index * 0.1}s` }} data-testid={`reminder-row-${reminder.id}`}>
                      <div>
                        <p className="font-medium text-slate-900">{reminder.customer_name}</p>
                        <p className="text-xs text-slate-500">{reminder.customer_phone}</p>
                      </div>
                      <Badge className={reminder.status === "sent" ? "bg-emerald-100 text-emerald-700" : reminder.status === "failed" ? "bg-red-100 text-red-700" : "bg-amber-100 text-amber-700"}>{reminder.status}</Badge>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </Layout>
  );
}
