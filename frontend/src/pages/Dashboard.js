import { useState, useEffect } from "react";
import { Layout } from "../components/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { useAuth } from "../context/AuthContext";
import axios from "axios";
import {
  Users,
  Wifi,
  DollarSign,
  MessageSquare,
  Clock,
  CheckCircle,
} from "lucide-react";

const API_URL = process.env.REACT_APP_BACKEND_URL;

const StatCard = ({ title, value, icon: Icon, color, subtitle }) => (
  <Card className="metric-card border-slate-200 bg-white" data-testid={`stat-${title.toLowerCase().replace(/\s+/g, '-')}`}>
    <CardContent className="p-6">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-medium text-slate-500">{title}</p>
          <p className={`text-3xl font-extrabold font-heading mt-1 ${color}`}>
            {value}
          </p>
          {subtitle && (
            <p className="text-xs text-slate-400 mt-1">{subtitle}</p>
          )}
        </div>
        <div className={`p-3 rounded-xl ${color.includes('violet') ? 'bg-violet-100' : color.includes('orange') ? 'bg-orange-100' : 'bg-slate-100'}`}>
          <Icon className={`w-6 h-6 ${color}`} />
        </div>
      </div>
    </CardContent>
  </Card>
);

export default function Dashboard() {
  const { getAuthHeader } = useAuth();
  const [stats, setStats] = useState(null);
  const [recentCustomers, setRecentCustomers] = useState([]);
  const [recentReminders, setRecentReminders] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [statsRes, customersRes, remindersRes] = await Promise.all([
          axios.get(`${API_URL}/api/dashboard/stats`, getAuthHeader()),
          axios.get(`${API_URL}/api/dashboard/recent-customers`, getAuthHeader()),
          axios.get(`${API_URL}/api/dashboard/recent-reminders`, getAuthHeader()),
        ]);
        setStats(statsRes.data);
        setRecentCustomers(customersRes.data);
        setRecentReminders(remindersRes.data);
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
              <CardContent className="p-6">
                <div className="h-20 bg-slate-200 rounded" />
              </CardContent>
            </Card>
          ))}
        </div>
      </Layout>
    );
  }

  return (
    <Layout title="Dashboard">
      <div className="space-y-8" data-testid="dashboard-content">
        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <StatCard
            title="Total Customers"
            value={stats?.total_customers || 0}
            icon={Users}
            color="text-violet-600"
            subtitle={`${stats?.active_customers || 0} active`}
          />
          <StatCard
            title="3 Device Plans"
            value={stats?.three_device_customers || 0}
            icon={Wifi}
            color="text-violet-600"
            subtitle="R200/month each"
          />
          <StatCard
            title="4 Device Plans"
            value={stats?.four_device_customers || 0}
            icon={Wifi}
            color="text-orange-500"
            subtitle="R300/month each"
          />
          <StatCard
            title="Est. Revenue"
            value={`R${stats?.estimated_monthly_revenue?.toLocaleString() || 0}`}
            icon={DollarSign}
            color="text-violet-600"
            subtitle="Per month"
          />
        </div>

        {/* Reminder Stats */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Card className="metric-card border-slate-200 bg-white" data-testid="pending-reminders-card">
            <CardContent className="p-6">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-amber-100 rounded-xl">
                  <Clock className="w-6 h-6 text-amber-600" />
                </div>
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
                <div className="p-3 bg-emerald-100 rounded-xl">
                  <CheckCircle className="w-6 h-6 text-emerald-600" />
                </div>
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
          {/* Recent Customers */}
          <Card className="border-slate-200 bg-white" data-testid="recent-customers-card">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg font-bold font-heading flex items-center gap-2">
                <Users className="w-5 h-5 text-violet-600" />
                Recent Customers
              </CardTitle>
            </CardHeader>
            <CardContent>
              {recentCustomers.length === 0 ? (
                <p className="text-slate-500 text-sm py-4 text-center">No customers yet</p>
              ) : (
                <div className="space-y-3">
                  {recentCustomers.map((customer, index) => (
                    <div
                      key={customer.id}
                      className="flex items-center justify-between p-3 bg-slate-50 rounded-lg animate-fade-in"
                      style={{ animationDelay: `${index * 0.1}s` }}
                      data-testid={`customer-row-${customer.id}`}
                    >
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-violet-600 rounded-full flex items-center justify-center text-white font-bold">
                          {customer.name.charAt(0).toUpperCase()}
                        </div>
                        <div>
                          <p className="font-medium text-slate-900">{customer.name}</p>
                          <p className="text-xs text-slate-500 font-mono">{customer.voucher_code}</p>
                        </div>
                      </div>
                      <Badge 
                        className={customer.plan === "3_devices" ? "bg-violet-100 text-violet-700" : "bg-orange-100 text-orange-700"}
                      >
                        R{customer.monthly_rate}
                      </Badge>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Recent Reminders */}
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
                    <div
                      key={reminder.id}
                      className="flex items-center justify-between p-3 bg-slate-50 rounded-lg animate-fade-in"
                      style={{ animationDelay: `${index * 0.1}s` }}
                      data-testid={`reminder-row-${reminder.id}`}
                    >
                      <div>
                        <p className="font-medium text-slate-900">{reminder.customer_name}</p>
                        <p className="text-xs text-slate-500">{reminder.customer_phone}</p>
                      </div>
                      <Badge
                        className={
                          reminder.status === "sent"
                            ? "bg-emerald-100 text-emerald-700"
                            : reminder.status === "failed"
                            ? "bg-red-100 text-red-700"
                            : "bg-amber-100 text-amber-700"
                        }
                      >
                        {reminder.status}
                      </Badge>
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
