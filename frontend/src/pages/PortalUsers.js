import { useState, useEffect, useCallback } from "react";
import { Layout } from "../components/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import { Input } from "../components/ui/input";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "../components/ui/table";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
} from "../components/ui/dialog";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "../components/ui/select";
import { useAuth } from "../context/AuthContext";
import axios from "axios";
import {
  Users, Search, ChevronDown, ChevronUp, Star, ShoppingCart, Gift,
  Phone, MapPin, Calendar, Filter, TrendingUp,
} from "lucide-react";

const API_URL = process.env.REACT_APP_BACKEND_URL;

const MONTHS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

function getMonthRange(year, month) {
  const from = `${year}-${String(month + 1).padStart(2, "0")}-01`;
  const lastDay = new Date(year, month + 1, 0).getDate();
  const to = `${year}-${String(month + 1).padStart(2, "0")}-${String(lastDay).padStart(2, "0")}`;
  return { from, to };
}

export default function PortalUsers() {
  const { getAuthHeader } = useAuth();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [selectedUser, setSelectedUser] = useState(null);
  const [sortField, setSortField] = useState("created_at");
  const [sortDir, setSortDir] = useState("desc");

  // Date filter state
  const [filterMode, setFilterMode] = useState("all"); // "all", "month", "custom"
  const now = new Date();
  const [selectedMonth, setSelectedMonth] = useState(now.getMonth());
  const [selectedYear, setSelectedYear] = useState(now.getFullYear());
  const [customFrom, setCustomFrom] = useState("");
  const [customTo, setCustomTo] = useState("");

  const fetchUsers = useCallback(async () => {
    setLoading(true);
    try {
      let params = {};
      if (filterMode === "month") {
        const range = getMonthRange(selectedYear, selectedMonth);
        params = { date_from: range.from, date_to: range.to };
      } else if (filterMode === "custom" && customFrom && customTo) {
        params = { date_from: customFrom, date_to: customTo };
      }
      const res = await axios.get(`${API_URL}/api/admin/portal-users`, {
        ...getAuthHeader(),
        params,
      });
      setUsers(res.data);
    } catch (error) {
      console.error("Failed to fetch portal users:", error);
    } finally {
      setLoading(false);
    }
  }, [getAuthHeader, filterMode, selectedMonth, selectedYear, customFrom, customTo]);

  useEffect(() => { fetchUsers(); }, [fetchUsers]);

  const filtered = users
    .filter((u) => {
      const q = search.toLowerCase();
      return !q || u.name?.toLowerCase().includes(q) || u.phone?.includes(q) || u.accommodation?.toLowerCase().includes(q);
    })
    .sort((a, b) => {
      let av = a[sortField], bv = b[sortField];
      if (typeof av === "string") av = av.toLowerCase();
      if (typeof bv === "string") bv = bv.toLowerCase();
      if (av < bv) return sortDir === "asc" ? -1 : 1;
      if (av > bv) return sortDir === "asc" ? 1 : -1;
      return 0;
    });

  const toggleSort = (field) => {
    if (sortField === field) setSortDir(sortDir === "asc" ? "desc" : "asc");
    else { setSortField(field); setSortDir("desc"); }
  };

  const SortIcon = ({ field }) => {
    if (sortField !== field) return null;
    return sortDir === "asc" ? <ChevronUp className="w-3 h-3 inline ml-1" /> : <ChevronDown className="w-3 h-3 inline ml-1" />;
  };

  const formatDate = (iso) => {
    if (!iso) return "-";
    return new Date(iso).toLocaleDateString("en-ZA", { day: "2-digit", month: "short", year: "numeric" });
  };

  const totalSpent = users.reduce((s, u) => s + (u.total_spent || 0), 0);
  const totalPoints = users.reduce((s, u) => s + (u.points || 0), 0);
  const totalPurchases = users.reduce((s, u) => s + (u.total_purchases || 0), 0);
  const lifetimeSpent = users.reduce((s, u) => s + (u.lifetime_spent || 0), 0);

  const filterLabel = filterMode === "all"
    ? "All Time"
    : filterMode === "month"
      ? `${MONTHS[selectedMonth]} ${selectedYear}`
      : `${customFrom} to ${customTo}`;

  // Generate year options (from 2024 to current+1)
  const years = [];
  for (let y = 2024; y <= now.getFullYear() + 1; y++) years.push(y);

  return (
    <Layout title="Portal Users">
      <div className="space-y-6" data-testid="portal-users-page">
        {/* Date Filter Bar */}
        <Card className="border-slate-200">
          <CardContent className="p-4">
            <div className="flex flex-wrap items-center gap-4">
              <div className="flex items-center gap-2">
                <Filter className="w-4 h-4 text-slate-500" />
                <span className="text-sm font-medium text-slate-600">Revenue Period:</span>
              </div>

              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant={filterMode === "all" ? "default" : "outline"}
                  onClick={() => setFilterMode("all")}
                  data-testid="filter-all"
                  className={filterMode === "all" ? "bg-violet-600 hover:bg-violet-700" : ""}
                >
                  All Time
                </Button>
                <Button
                  size="sm"
                  variant={filterMode === "month" ? "default" : "outline"}
                  onClick={() => setFilterMode("month")}
                  data-testid="filter-month"
                  className={filterMode === "month" ? "bg-violet-600 hover:bg-violet-700" : ""}
                >
                  By Month
                </Button>
                <Button
                  size="sm"
                  variant={filterMode === "custom" ? "default" : "outline"}
                  onClick={() => setFilterMode("custom")}
                  data-testid="filter-custom"
                  className={filterMode === "custom" ? "bg-violet-600 hover:bg-violet-700" : ""}
                >
                  Custom Range
                </Button>
              </div>

              {filterMode === "month" && (
                <div className="flex gap-2 items-center">
                  <Select value={String(selectedMonth)} onValueChange={(v) => setSelectedMonth(Number(v))}>
                    <SelectTrigger className="w-36" data-testid="month-select">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {MONTHS.map((m, i) => (
                        <SelectItem key={i} value={String(i)}>{m}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Select value={String(selectedYear)} onValueChange={(v) => setSelectedYear(Number(v))}>
                    <SelectTrigger className="w-24" data-testid="year-select">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {years.map((y) => (
                        <SelectItem key={y} value={String(y)}>{y}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              )}

              {filterMode === "custom" && (
                <div className="flex gap-2 items-center">
                  <label className="text-xs text-slate-500">From</label>
                  <Input
                    type="date"
                    value={customFrom}
                    onChange={(e) => setCustomFrom(e.target.value)}
                    className="w-40"
                    data-testid="date-from"
                  />
                  <label className="text-xs text-slate-500">To</label>
                  <Input
                    type="date"
                    value={customTo}
                    onChange={(e) => setCustomTo(e.target.value)}
                    className="w-40"
                    data-testid="date-to"
                  />
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Stats */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardContent className="p-4 flex items-center gap-3">
              <div className="p-2 bg-violet-100 rounded-lg"><Users className="w-5 h-5 text-violet-600" /></div>
              <div>
                <p className="text-2xl font-bold" data-testid="stat-total-users">{users.length}</p>
                <p className="text-xs text-slate-500">Registered Users</p>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 flex items-center gap-3">
              <div className="p-2 bg-emerald-100 rounded-lg"><ShoppingCart className="w-5 h-5 text-emerald-600" /></div>
              <div>
                <p className="text-2xl font-bold" data-testid="stat-total-purchases">{totalPurchases}</p>
                <p className="text-xs text-slate-500">Purchases ({filterLabel})</p>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 flex items-center gap-3">
              <div className="p-2 bg-amber-100 rounded-lg"><Star className="w-5 h-5 text-amber-600" /></div>
              <div>
                <p className="text-2xl font-bold" data-testid="stat-total-points">{totalPoints}</p>
                <p className="text-xs text-slate-500">Points in Circulation</p>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 flex items-center gap-3">
              <div className="p-2 bg-sky-100 rounded-lg"><TrendingUp className="w-5 h-5 text-sky-600" /></div>
              <div>
                <p className="text-2xl font-bold" data-testid="stat-total-revenue">R{totalSpent.toFixed(0)}</p>
                <p className="text-xs text-slate-500">Revenue ({filterLabel})</p>
                {filterMode !== "all" && lifetimeSpent > 0 && (
                  <p className="text-[10px] text-slate-400">Lifetime: R{lifetimeSpent.toFixed(0)}</p>
                )}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Search & Table */}
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between flex-wrap gap-3">
              <CardTitle className="text-lg font-bold flex items-center gap-2">
                <Users className="w-5 h-5 text-violet-600" />
                All Portal Users ({filtered.length})
              </CardTitle>
              <div className="relative w-64">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <Input
                  placeholder="Search name, phone, accommodation..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="pl-9"
                  data-testid="portal-users-search"
                />
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="py-8 text-center text-slate-500">Loading...</div>
            ) : filtered.length === 0 ? (
              <div className="py-12 text-center">
                <Users className="w-12 h-12 text-slate-200 mx-auto mb-4" />
                <p className="text-slate-500">No portal users found</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="cursor-pointer select-none" onClick={() => toggleSort("name")}>
                        Name <SortIcon field="name" />
                      </TableHead>
                      <TableHead>Phone</TableHead>
                      <TableHead>Accommodation</TableHead>
                      <TableHead className="cursor-pointer select-none text-center" onClick={() => toggleSort("total_purchases")}>
                        Purchases <SortIcon field="total_purchases" />
                      </TableHead>
                      <TableHead className="cursor-pointer select-none text-center" onClick={() => toggleSort("total_spent")}>
                        Spent <SortIcon field="total_spent" />
                      </TableHead>
                      <TableHead className="cursor-pointer select-none text-center" onClick={() => toggleSort("points")}>
                        Points <SortIcon field="points" />
                      </TableHead>
                      <TableHead className="cursor-pointer select-none" onClick={() => toggleSort("created_at")}>
                        Joined <SortIcon field="created_at" />
                      </TableHead>
                      <TableHead></TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filtered.map((user) => (
                      <TableRow key={user.id} data-testid={`portal-user-row-${user.id}`}>
                        <TableCell className="font-medium">{user.name}</TableCell>
                        <TableCell className="font-mono text-sm">{user.phone}</TableCell>
                        <TableCell>
                          {user.accommodation ? (
                            <Badge variant="outline" className="text-xs">{user.accommodation}</Badge>
                          ) : <span className="text-slate-400 text-xs">-</span>}
                        </TableCell>
                        <TableCell className="text-center">{user.total_purchases}</TableCell>
                        <TableCell className="text-center font-medium">R{(user.total_spent || 0).toFixed(0)}</TableCell>
                        <TableCell className="text-center">
                          <Badge className="bg-amber-100 text-amber-700">{user.points} pts</Badge>
                        </TableCell>
                        <TableCell className="text-sm text-slate-500">{formatDate(user.created_at)}</TableCell>
                        <TableCell>
                          <Button size="sm" variant="ghost" onClick={() => setSelectedUser(user)} data-testid={`view-user-${user.id}`}>
                            View
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>

        {/* User Detail Dialog */}
        <Dialog open={!!selectedUser} onOpenChange={() => setSelectedUser(null)}>
          <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
            {selectedUser && (
              <>
                <DialogHeader>
                  <DialogTitle className="flex items-center gap-2 text-lg">
                    <Users className="w-5 h-5 text-violet-600" />
                    {selectedUser.name}
                  </DialogTitle>
                </DialogHeader>

                <div className="space-y-5">
                  {/* User Info */}
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div className="flex items-center gap-2"><Phone className="w-4 h-4 text-slate-400" /> {selectedUser.phone}</div>
                    <div className="flex items-center gap-2"><MapPin className="w-4 h-4 text-slate-400" /> {selectedUser.accommodation || "N/A"}</div>
                    <div className="flex items-center gap-2"><Calendar className="w-4 h-4 text-slate-400" /> Joined {formatDate(selectedUser.created_at)}</div>
                    <div className="flex items-center gap-2"><Star className="w-4 h-4 text-amber-500" /> {selectedUser.points} points</div>
                  </div>

                  {/* Stats row */}
                  <div className="grid grid-cols-4 gap-3">
                    <div className="bg-emerald-50 rounded-lg p-3 text-center">
                      <p className="text-xl font-bold text-emerald-700">{selectedUser.total_purchases}</p>
                      <p className="text-[10px] text-emerald-600">Purchases ({filterLabel})</p>
                    </div>
                    <div className="bg-sky-50 rounded-lg p-3 text-center">
                      <p className="text-xl font-bold text-sky-700">R{(selectedUser.total_spent || 0).toFixed(0)}</p>
                      <p className="text-[10px] text-sky-600">Spent ({filterLabel})</p>
                    </div>
                    <div className="bg-amber-50 rounded-lg p-3 text-center">
                      <p className="text-xl font-bold text-amber-700">{selectedUser.total_points_earned}</p>
                      <p className="text-[10px] text-amber-600">Pts Earned</p>
                    </div>
                    <div className="bg-violet-50 rounded-lg p-3 text-center">
                      <p className="text-xl font-bold text-violet-700">{selectedUser.total_points_redeemed}</p>
                      <p className="text-[10px] text-violet-600">Pts Redeemed</p>
                    </div>
                  </div>

                  {/* Purchase History */}
                  <div>
                    <h4 className="font-semibold text-sm mb-2 flex items-center gap-1"><ShoppingCart className="w-4 h-4" /> Purchases</h4>
                    {selectedUser.purchases?.length > 0 ? (
                      <div className="overflow-x-auto border rounded-lg">
                        <Table>
                          <TableHeader>
                            <TableRow>
                              <TableHead>Date</TableHead>
                              <TableHead>Plan</TableHead>
                              <TableHead>Amount</TableHead>
                              <TableHead>Voucher</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {selectedUser.purchases.map((p, i) => (
                              <TableRow key={i}>
                                <TableCell className="text-xs">{formatDate(p.created_at)}</TableCell>
                                <TableCell className="text-sm">{p.plan}</TableCell>
                                <TableCell className="font-medium">R{p.amount}</TableCell>
                                <TableCell className="font-mono text-sm">{p.voucher_code || "-"}</TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                      </div>
                    ) : <p className="text-sm text-slate-400">No purchases yet</p>}
                  </div>

                  {/* Points History */}
                  <div>
                    <h4 className="font-semibold text-sm mb-2 flex items-center gap-1"><Star className="w-4 h-4" /> Points History</h4>
                    {selectedUser.points_history?.length > 0 ? (
                      <div className="overflow-x-auto border rounded-lg">
                        <Table>
                          <TableHeader>
                            <TableRow>
                              <TableHead>Date</TableHead>
                              <TableHead>Type</TableHead>
                              <TableHead>Points</TableHead>
                              <TableHead>Description</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {selectedUser.points_history.map((p, i) => (
                              <TableRow key={i}>
                                <TableCell className="text-xs">{formatDate(p.created_at)}</TableCell>
                                <TableCell>
                                  <Badge className={
                                    p.type === "earned" ? "bg-emerald-100 text-emerald-700" :
                                    p.type === "redeemed" ? "bg-red-100 text-red-700" :
                                    "bg-blue-100 text-blue-700"
                                  }>{p.type}</Badge>
                                </TableCell>
                                <TableCell className={`font-medium ${p.points > 0 ? "text-emerald-600" : "text-red-600"}`}>
                                  {p.points > 0 ? "+" : ""}{p.points}
                                </TableCell>
                                <TableCell className="text-sm">{p.description}</TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                      </div>
                    ) : <p className="text-sm text-slate-400">No points activity</p>}
                  </div>

                  {/* Referral Info */}
                  {selectedUser.referral_code && (
                    <div className="bg-slate-50 rounded-lg p-3 text-sm">
                      <span className="text-slate-500">Referral Code:</span>{" "}
                      <span className="font-mono font-medium">{selectedUser.referral_code}</span>
                      {selectedUser.referred_by && (
                        <span className="text-slate-400 ml-4">Referred by another user</span>
                      )}
                    </div>
                  )}
                </div>
              </>
            )}
          </DialogContent>
        </Dialog>
      </div>
    </Layout>
  );
}
