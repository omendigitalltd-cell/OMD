import { useState, useEffect, useCallback } from "react";
import { Layout } from "../components/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "../components/ui/table";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "../components/ui/select";
import { useAuth } from "../context/AuthContext";
import axios from "axios";
import {
  AlertTriangle, CheckCircle, RefreshCw, FileText, UserPlus, ShoppingCart, Gift, LogIn, Filter,
} from "lucide-react";

const API_URL = process.env.REACT_APP_BACKEND_URL;

const ACTION_MAP = {
  register: { label: "Registration", icon: UserPlus, color: "text-blue-600 bg-blue-50" },
  login: { label: "Login", icon: LogIn, color: "text-slate-600 bg-slate-50" },
  buy_voucher: { label: "Buy Voucher", icon: ShoppingCart, color: "text-emerald-600 bg-emerald-50" },
  redeem: { label: "Redeem Rewards", icon: Gift, color: "text-amber-600 bg-amber-50" },
};

const STATUS_STYLES = {
  error: "bg-red-100 text-red-700",
  success: "bg-emerald-100 text-emerald-700",
};

export default function Logs() {
  const { getAuthHeader } = useAuth();
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filterAction, setFilterAction] = useState("all");
  const [filterStatus, setFilterStatus] = useState("all");

  const fetchLogs = useCallback(async () => {
    setLoading(true);
    try {
      const params = {};
      if (filterAction !== "all") params.action = filterAction;
      if (filterStatus !== "all") params.status = filterStatus;
      const res = await axios.get(`${API_URL}/api/admin/activity-logs`, { ...getAuthHeader(), params });
      setLogs(res.data);
    } catch (err) {
      console.error("Failed to fetch logs:", err);
    } finally {
      setLoading(false);
    }
  }, [getAuthHeader, filterAction, filterStatus]);

  useEffect(() => { fetchLogs(); }, [fetchLogs]);

  const formatDate = (iso) => {
    if (!iso) return "-";
    return new Date(iso).toLocaleString("en-ZA", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
  };

  const errorCount = logs.filter(l => l.status === "error").length;
  const successCount = logs.filter(l => l.status === "success").length;

  return (
    <Layout title="Activity Logs">
      <div className="space-y-6" data-testid="logs-page">
        {/* Stats */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardContent className="p-4 flex items-center gap-3">
              <div className="p-2 bg-red-100 rounded-lg"><AlertTriangle className="w-5 h-5 text-red-600" /></div>
              <div><p className="text-2xl font-bold text-red-600" data-testid="error-count">{errorCount}</p><p className="text-xs text-slate-500">Errors</p></div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 flex items-center gap-3">
              <div className="p-2 bg-emerald-100 rounded-lg"><CheckCircle className="w-5 h-5 text-emerald-600" /></div>
              <div><p className="text-2xl font-bold text-emerald-600" data-testid="success-count">{successCount}</p><p className="text-xs text-slate-500">Successful</p></div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 flex items-center gap-3">
              <div className="p-2 bg-blue-100 rounded-lg"><UserPlus className="w-5 h-5 text-blue-600" /></div>
              <div><p className="text-2xl font-bold">{logs.filter(l => l.action === "register").length}</p><p className="text-xs text-slate-500">Registrations</p></div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 flex items-center gap-3">
              <div className="p-2 bg-violet-100 rounded-lg"><FileText className="w-5 h-5 text-violet-600" /></div>
              <div><p className="text-2xl font-bold">{logs.length}</p><p className="text-xs text-slate-500">Total Logs</p></div>
            </CardContent>
          </Card>
        </div>

        {/* Filters */}
        <Card>
          <CardContent className="p-4">
            <div className="flex flex-wrap items-center gap-4">
              <div className="flex items-center gap-2">
                <Filter className="w-4 h-4 text-slate-500" />
                <span className="text-sm font-medium text-slate-600">Filters:</span>
              </div>
              <Select value={filterAction} onValueChange={setFilterAction}>
                <SelectTrigger className="w-44" data-testid="filter-action">
                  <SelectValue placeholder="All Actions" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Actions</SelectItem>
                  <SelectItem value="register">Registration</SelectItem>
                  <SelectItem value="login">Login</SelectItem>
                  <SelectItem value="buy_voucher">Buy Voucher</SelectItem>
                  <SelectItem value="redeem">Redeem Rewards</SelectItem>
                </SelectContent>
              </Select>
              <Select value={filterStatus} onValueChange={setFilterStatus}>
                <SelectTrigger className="w-36" data-testid="filter-status">
                  <SelectValue placeholder="All Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Status</SelectItem>
                  <SelectItem value="error">Errors Only</SelectItem>
                  <SelectItem value="success">Success Only</SelectItem>
                </SelectContent>
              </Select>
              <Button variant="ghost" size="icon" onClick={fetchLogs} data-testid="refresh-logs-btn">
                <RefreshCw className="w-4 h-4" />
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Logs Table */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-lg flex items-center gap-2">
              <FileText className="w-5 h-5 text-violet-600" />
              Activity Logs ({logs.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="py-8 text-center text-slate-400">Loading...</div>
            ) : logs.length === 0 ? (
              <div className="py-12 text-center">
                <FileText className="w-12 h-12 text-slate-200 mx-auto mb-3" />
                <p className="text-slate-500">No activity logs yet</p>
              </div>
            ) : (
              <div className="overflow-x-auto max-h-[500px] overflow-y-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Time</TableHead>
                      <TableHead>Action</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>User</TableHead>
                      <TableHead>Phone</TableHead>
                      <TableHead>Detail</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {logs.map((log) => {
                      const actionInfo = ACTION_MAP[log.action] || { label: log.action, icon: FileText, color: "text-slate-600 bg-slate-50" };
                      const ActionIcon = actionInfo.icon;
                      return (
                        <TableRow key={log.id} className={log.status === "error" ? "bg-red-50/50" : ""} data-testid={`log-row-${log.id}`}>
                          <TableCell className="text-xs text-slate-500 whitespace-nowrap">{formatDate(log.created_at)}</TableCell>
                          <TableCell>
                            <div className="flex items-center gap-1.5">
                              <div className={`p-1 rounded ${actionInfo.color}`}><ActionIcon className="w-3 h-3" /></div>
                              <span className="text-xs font-medium">{actionInfo.label}</span>
                            </div>
                          </TableCell>
                          <TableCell>
                            <Badge className={STATUS_STYLES[log.status] || "bg-slate-100 text-slate-600"}>
                              {log.status === "error" ? <AlertTriangle className="w-3 h-3 mr-1" /> : <CheckCircle className="w-3 h-3 mr-1" />}
                              {log.status}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-sm">{log.user_name || "-"}</TableCell>
                          <TableCell className="font-mono text-xs">{log.user_phone || "-"}</TableCell>
                          <TableCell className="text-xs text-slate-600 max-w-xs truncate">{log.detail}</TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </Layout>
  );
}
