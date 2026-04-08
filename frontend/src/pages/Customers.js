import { useState, useEffect, useCallback } from "react";
import { Layout } from "../components/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "../components/ui/table";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "../components/ui/dialog";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "../components/ui/select";
import { useAuth } from "../context/AuthContext";
import axios from "axios";
import { toast } from "sonner";
import {
  Users, Search, ChevronDown, ChevronUp, Star, ShoppingCart,
  Phone, MapPin, Calendar, Filter, TrendingUp, KeyRound,
  Plus, Pencil, Trash2, Key,
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

const initialFormData = {
  name: "", phone: "", voucher_code: "", plan: "3_devices",
  start_date: new Date().toISOString().split("T")[0], is_active: true,
};

export default function Customers() {
  const { getAuthHeader } = useAuth();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [selectedUser, setSelectedUser] = useState(null);
  const [sortField, setSortField] = useState("created_at");
  const [sortDir, setSortDir] = useState("desc");
  const [resetPassword, setResetPassword] = useState("");
  const [resetting, setResetting] = useState(false);

  // Date filter
  const now = new Date();
  const [filterMode, setFilterMode] = useState("all");
  const [selectedMonth, setSelectedMonth] = useState(now.getMonth());
  const [selectedYear, setSelectedYear] = useState(now.getFullYear());
  const [customFrom, setCustomFrom] = useState("");
  const [customTo, setCustomTo] = useState("");

  // Add legacy customer dialog
  const [isAddOpen, setIsAddOpen] = useState(false);
  const [isDeleteOpen, setIsDeleteOpen] = useState(false);
  const [editingCustomer, setEditingCustomer] = useState(null);
  const [deletingCustomer, setDeletingCustomer] = useState(null);
  const [formData, setFormData] = useState(initialFormData);
  const [submitting, setSubmitting] = useState(false);

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
      const res = await axios.get(`${API_URL}/api/admin/portal-users`, { ...getAuthHeader(), params });
      setUsers(res.data);
    } catch (error) {
      console.error("Failed to fetch customers:", error);
    } finally {
      setLoading(false);
    }
  }, [getAuthHeader, filterMode, selectedMonth, selectedYear, customFrom, customTo]);

  useEffect(() => { fetchUsers(); }, [fetchUsers]);

  const handleResetPassword = async (userId, userName) => {
    if (!resetPassword || resetPassword.length < 4) { toast.error("Password must be at least 4 characters"); return; }
    setResetting(true);
    try {
      await axios.post(`${API_URL}/api/admin/portal-users/${userId}/reset-password`, { new_password: resetPassword }, getAuthHeader());
      toast.success(`Password reset for ${userName}`);
      setResetPassword("");
    } catch (err) { toast.error(err.response?.data?.detail || "Failed to reset password"); }
    finally { setResetting(false); }
  };

  // Legacy customer CRUD
  const handleAddSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      if (editingCustomer) {
        await axios.put(`${API_URL}/api/customers/${editingCustomer.id}`, formData, getAuthHeader());
        toast.success("Customer updated");
      } else {
        await axios.post(`${API_URL}/api/customers`, formData, getAuthHeader());
        toast.success("Customer added");
      }
      setIsAddOpen(false);
      setEditingCustomer(null);
      fetchUsers();
    } catch (err) { toast.error(err.response?.data?.detail || "Failed to save"); }
    finally { setSubmitting(false); }
  };

  const handleDelete = async () => {
    try {
      await axios.delete(`${API_URL}/api/customers/${deletingCustomer.id}`, getAuthHeader());
      toast.success("Customer deleted");
      setIsDeleteOpen(false);
      fetchUsers();
    } catch { toast.error("Failed to delete"); }
  };

  const openEdit = (user) => {
    setEditingCustomer(user);
    setFormData({ name: user.name, phone: user.phone, voucher_code: user.voucher_code || "", plan: user.plan || "3_devices", start_date: user.created_at?.slice(0, 10) || new Date().toISOString().split("T")[0], is_active: user.is_active });
    setIsAddOpen(true);
  };

  const generateVoucherCode = () => {
    const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
    let code = "HS-";
    for (let i = 0; i < 6; i++) code += chars.charAt(Math.floor(Math.random() * chars.length));
    setFormData({ ...formData, voucher_code: code });
  };

  const filtered = users
    .filter((u) => {
      const q = search.toLowerCase();
      return !q || u.name?.toLowerCase().includes(q) || u.phone?.includes(q) || u.accommodation?.toLowerCase().includes(q) || (u.voucher_code || "").toLowerCase().includes(q);
    })
    .sort((a, b) => {
      let av = a[sortField] ?? "", bv = b[sortField] ?? "";
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

  const formatDate = (iso) => { if (!iso) return "-"; return new Date(iso).toLocaleDateString("en-ZA", { day: "2-digit", month: "short", year: "numeric" }); };

  const totalSpent = users.reduce((s, u) => s + (u.total_spent || 0), 0);
  const totalPoints = users.reduce((s, u) => s + (u.points || 0), 0);
  const totalPurchases = users.reduce((s, u) => s + (u.total_purchases || 0), 0);
  const lifetimeSpent = users.reduce((s, u) => s + (u.lifetime_spent || 0), 0);

  const filterLabel = filterMode === "all" ? "All Time" : filterMode === "month" ? `${MONTHS[selectedMonth]} ${selectedYear}` : `${customFrom} to ${customTo}`;
  const years = [];
  for (let y = 2024; y <= now.getFullYear() + 1; y++) years.push(y);

  return (
    <Layout title="Customers">
      <div className="space-y-6" data-testid="customers-page">
        {/* Date Filter */}
        <Card className="border-slate-200">
          <CardContent className="p-4">
            <div className="flex flex-wrap items-center gap-4">
              <div className="flex items-center gap-2">
                <Filter className="w-4 h-4 text-slate-500" />
                <span className="text-sm font-medium text-slate-600">Revenue Period:</span>
              </div>
              <div className="flex gap-2">
                {["all", "month", "custom"].map((mode) => (
                  <Button key={mode} size="sm" variant={filterMode === mode ? "default" : "outline"}
                    onClick={() => setFilterMode(mode)}
                    className={filterMode === mode ? "bg-violet-600 hover:bg-violet-700" : ""}
                    data-testid={`filter-${mode}`}
                  >{mode === "all" ? "All Time" : mode === "month" ? "By Month" : "Custom Range"}</Button>
                ))}
              </div>
              {filterMode === "month" && (
                <div className="flex gap-2 items-center">
                  <Select value={String(selectedMonth)} onValueChange={(v) => setSelectedMonth(Number(v))}>
                    <SelectTrigger className="w-36" data-testid="month-select"><SelectValue /></SelectTrigger>
                    <SelectContent>{MONTHS.map((m, i) => <SelectItem key={i} value={String(i)}>{m}</SelectItem>)}</SelectContent>
                  </Select>
                  <Select value={String(selectedYear)} onValueChange={(v) => setSelectedYear(Number(v))}>
                    <SelectTrigger className="w-24" data-testid="year-select"><SelectValue /></SelectTrigger>
                    <SelectContent>{years.map((y) => <SelectItem key={y} value={String(y)}>{y}</SelectItem>)}</SelectContent>
                  </Select>
                </div>
              )}
              {filterMode === "custom" && (
                <div className="flex gap-2 items-center">
                  <label className="text-xs text-slate-500">From</label>
                  <Input type="date" value={customFrom} onChange={(e) => setCustomFrom(e.target.value)} className="w-40" data-testid="date-from" />
                  <label className="text-xs text-slate-500">To</label>
                  <Input type="date" value={customTo} onChange={(e) => setCustomTo(e.target.value)} className="w-40" data-testid="date-to" />
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Stats */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <Card><CardContent className="p-4 flex items-center gap-3">
            <div className="p-2 bg-violet-100 rounded-lg"><Users className="w-5 h-5 text-violet-600" /></div>
            <div><p className="text-2xl font-bold" data-testid="stat-total-users">{users.length}</p><p className="text-xs text-slate-500">Total Customers</p></div>
          </CardContent></Card>
          <Card><CardContent className="p-4 flex items-center gap-3">
            <div className="p-2 bg-emerald-100 rounded-lg"><ShoppingCart className="w-5 h-5 text-emerald-600" /></div>
            <div><p className="text-2xl font-bold" data-testid="stat-total-purchases">{totalPurchases}</p><p className="text-xs text-slate-500">Purchases ({filterLabel})</p></div>
          </CardContent></Card>
          <Card><CardContent className="p-4 flex items-center gap-3">
            <div className="p-2 bg-amber-100 rounded-lg"><Star className="w-5 h-5 text-amber-600" /></div>
            <div><p className="text-2xl font-bold" data-testid="stat-total-points">{totalPoints}</p><p className="text-xs text-slate-500">Points in Circulation</p></div>
          </CardContent></Card>
          <Card><CardContent className="p-4 flex items-center gap-3">
            <div className="p-2 bg-sky-100 rounded-lg"><TrendingUp className="w-5 h-5 text-sky-600" /></div>
            <div><p className="text-2xl font-bold" data-testid="stat-total-revenue">R{totalSpent.toFixed(0)}</p><p className="text-xs text-slate-500">Revenue ({filterLabel})</p>
              {filterMode !== "all" && lifetimeSpent > 0 && <p className="text-[10px] text-slate-400">Lifetime: R{lifetimeSpent.toFixed(0)}</p>}
            </div>
          </CardContent></Card>
        </div>

        {/* Search + Add + Table */}
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between flex-wrap gap-3">
              <CardTitle className="text-lg font-bold flex items-center gap-2">
                <Users className="w-5 h-5 text-violet-600" />
                All Customers ({filtered.length})
              </CardTitle>
              <div className="flex gap-3 items-center">
                <div className="relative w-64">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                  <Input placeholder="Search name, phone, voucher..." value={search} onChange={(e) => setSearch(e.target.value)} className="pl-9" data-testid="customers-search" />
                </div>
                <Button onClick={() => { setEditingCustomer(null); setFormData(initialFormData); setIsAddOpen(true); }} className="bg-violet-600 hover:bg-violet-700" data-testid="add-customer-btn">
                  <Plus className="w-4 h-4 mr-2" />Add Customer
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="py-8 text-center text-slate-500">Loading...</div>
            ) : filtered.length === 0 ? (
              <div className="py-12 text-center">
                <Users className="w-12 h-12 text-slate-200 mx-auto mb-4" />
                <p className="text-slate-500">No customers found</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="cursor-pointer select-none" onClick={() => toggleSort("name")}>Name <SortIcon field="name" /></TableHead>
                      <TableHead>Phone</TableHead>
                      <TableHead>Accommodation</TableHead>
                      <TableHead>Voucher</TableHead>
                      <TableHead className="cursor-pointer select-none text-center" onClick={() => toggleSort("total_purchases")}>Purchases <SortIcon field="total_purchases" /></TableHead>
                      <TableHead className="cursor-pointer select-none text-center" onClick={() => toggleSort("total_spent")}>Spent <SortIcon field="total_spent" /></TableHead>
                      <TableHead className="cursor-pointer select-none text-center" onClick={() => toggleSort("points")}>Points <SortIcon field="points" /></TableHead>
                      <TableHead className="cursor-pointer select-none" onClick={() => toggleSort("created_at")}>Joined <SortIcon field="created_at" /></TableHead>
                      <TableHead></TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filtered.map((user) => (
                      <TableRow key={user.id} data-testid={`customer-row-${user.id}`}>
                        <TableCell className="font-medium">
                          {user.name}
                          {user.source === "legacy" && <Badge className="ml-2 bg-slate-100 text-slate-500 text-[10px]">Manual</Badge>}
                        </TableCell>
                        <TableCell className="font-mono text-sm">{user.phone}</TableCell>
                        <TableCell>
                          {user.accommodation ? <Badge variant="outline" className="text-xs">{user.accommodation}</Badge> : <span className="text-slate-400 text-xs">-</span>}
                        </TableCell>
                        <TableCell>
                          {user.voucher_code ? <code className="bg-slate-100 px-2 py-0.5 rounded text-xs font-mono">{user.voucher_code}</code> : <span className="text-slate-400 text-xs">-</span>}
                        </TableCell>
                        <TableCell className="text-center">{user.total_purchases}</TableCell>
                        <TableCell className="text-center font-medium">R{(user.total_spent || 0).toFixed(0)}</TableCell>
                        <TableCell className="text-center">
                          <Badge className="bg-amber-100 text-amber-700">{user.points} pts</Badge>
                        </TableCell>
                        <TableCell className="text-sm text-slate-500">{formatDate(user.created_at)}</TableCell>
                        <TableCell>
                          <div className="flex gap-1">
                            <Button size="sm" variant="ghost" onClick={() => setSelectedUser(user)} data-testid={`view-customer-${user.id}`}>View</Button>
                            {user.source === "legacy" && (
                              <>
                                <Button size="icon" variant="ghost" onClick={() => openEdit(user)} className="h-8 w-8"><Pencil className="w-3 h-3" /></Button>
                                <Button size="icon" variant="ghost" onClick={() => { setDeletingCustomer(user); setIsDeleteOpen(true); }} className="h-8 w-8 hover:text-red-600"><Trash2 className="w-3 h-3" /></Button>
                              </>
                            )}
                          </div>
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
        <Dialog open={!!selectedUser} onOpenChange={() => { setSelectedUser(null); setResetPassword(""); }}>
          <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
            {selectedUser && (
              <>
                <DialogHeader>
                  <DialogTitle className="flex items-center gap-2 text-lg">
                    <Users className="w-5 h-5 text-violet-600" />
                    {selectedUser.name}
                    {selectedUser.source === "legacy" && <Badge className="bg-slate-100 text-slate-500">Manual</Badge>}
                  </DialogTitle>
                </DialogHeader>
                <div className="space-y-5">
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div className="flex items-center gap-2"><Phone className="w-4 h-4 text-slate-400" /> {selectedUser.phone}</div>
                    <div className="flex items-center gap-2"><MapPin className="w-4 h-4 text-slate-400" /> {selectedUser.accommodation || "N/A"}</div>
                    <div className="flex items-center gap-2"><Calendar className="w-4 h-4 text-slate-400" /> Joined {formatDate(selectedUser.created_at)}</div>
                    <div className="flex items-center gap-2"><Star className="w-4 h-4 text-amber-500" /> {selectedUser.points} points</div>
                  </div>
                  <div className="grid grid-cols-4 gap-3">
                    <div className="bg-emerald-50 rounded-lg p-3 text-center">
                      <p className="text-xl font-bold text-emerald-700">{selectedUser.total_purchases}</p>
                      <p className="text-[10px] text-emerald-600">Purchases</p>
                    </div>
                    <div className="bg-sky-50 rounded-lg p-3 text-center">
                      <p className="text-xl font-bold text-sky-700">R{(selectedUser.total_spent || 0).toFixed(0)}</p>
                      <p className="text-[10px] text-sky-600">Spent</p>
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

                  {/* Purchases */}
                  <div>
                    <h4 className="font-semibold text-sm mb-2 flex items-center gap-1"><ShoppingCart className="w-4 h-4" /> Purchases</h4>
                    {selectedUser.purchases?.length > 0 ? (
                      <div className="overflow-x-auto border rounded-lg">
                        <Table><TableHeader><TableRow>
                          <TableHead>Date</TableHead><TableHead>Plan</TableHead><TableHead>Amount</TableHead><TableHead>Voucher</TableHead>
                        </TableRow></TableHeader><TableBody>
                          {selectedUser.purchases.map((p, i) => (
                            <TableRow key={i}>
                              <TableCell className="text-xs">{formatDate(p.created_at)}</TableCell>
                              <TableCell className="text-sm">{p.plan}</TableCell>
                              <TableCell className="font-medium">R{p.amount}</TableCell>
                              <TableCell className="font-mono text-sm">{p.voucher_code || "-"}</TableCell>
                            </TableRow>
                          ))}
                        </TableBody></Table>
                      </div>
                    ) : <p className="text-sm text-slate-400">No purchases yet</p>}
                  </div>

                  {/* Points History */}
                  <div>
                    <h4 className="font-semibold text-sm mb-2 flex items-center gap-1"><Star className="w-4 h-4" /> Points History</h4>
                    {selectedUser.points_history?.length > 0 ? (
                      <div className="overflow-x-auto border rounded-lg">
                        <Table><TableHeader><TableRow>
                          <TableHead>Date</TableHead><TableHead>Type</TableHead><TableHead>Points</TableHead><TableHead>Description</TableHead>
                        </TableRow></TableHeader><TableBody>
                          {selectedUser.points_history.map((p, i) => (
                            <TableRow key={i}>
                              <TableCell className="text-xs">{formatDate(p.created_at)}</TableCell>
                              <TableCell><Badge className={p.type === "earned" ? "bg-emerald-100 text-emerald-700" : p.type === "redeemed" ? "bg-red-100 text-red-700" : "bg-blue-100 text-blue-700"}>{p.type}</Badge></TableCell>
                              <TableCell className={`font-medium ${p.points > 0 ? "text-emerald-600" : "text-red-600"}`}>{p.points > 0 ? "+" : ""}{p.points}</TableCell>
                              <TableCell className="text-sm">{p.description}</TableCell>
                            </TableRow>
                          ))}
                        </TableBody></Table>
                      </div>
                    ) : <p className="text-sm text-slate-400">No points activity</p>}
                  </div>

                  {/* Reset Password (portal users only) */}
                  {selectedUser.source === "portal" && (
                    <div className="border-t pt-4">
                      <h4 className="font-semibold text-sm mb-2 flex items-center gap-1"><KeyRound className="w-4 h-4" /> Reset Password</h4>
                      <div className="flex gap-2">
                        <Input type="text" placeholder="Enter new password" value={resetPassword} onChange={(e) => setResetPassword(e.target.value)} className="flex-1" data-testid="reset-password-input" />
                        <Button onClick={() => handleResetPassword(selectedUser.id, selectedUser.name)} disabled={resetting || !resetPassword} className="bg-orange-500 hover:bg-orange-600" data-testid="reset-password-btn">
                          {resetting ? "Resetting..." : "Reset"}
                        </Button>
                      </div>
                    </div>
                  )}
                </div>
              </>
            )}
          </DialogContent>
        </Dialog>

        {/* Add/Edit Legacy Customer Dialog */}
        <Dialog open={isAddOpen} onOpenChange={setIsAddOpen}>
          <DialogContent className="sm:max-w-md" data-testid="add-customer-dialog">
            <DialogHeader>
              <DialogTitle>{editingCustomer ? "Edit Customer" : "Add New Customer"}</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleAddSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label>Name</Label>
                <Input value={formData.name} onChange={(e) => setFormData({ ...formData, name: e.target.value })} required data-testid="customer-name-input" />
              </div>
              <div className="space-y-2">
                <Label>Phone</Label>
                <div className="relative">
                  <Phone className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                  <Input value={formData.phone} onChange={(e) => setFormData({ ...formData, phone: e.target.value })} placeholder="+27..." className="pl-10" required data-testid="customer-phone-input" />
                </div>
              </div>
              <div className="space-y-2">
                <Label>Voucher Code</Label>
                <div className="flex gap-2">
                  <div className="relative flex-1">
                    <Key className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                    <Input value={formData.voucher_code} onChange={(e) => setFormData({ ...formData, voucher_code: e.target.value.toUpperCase() })} className="pl-10 font-mono" required data-testid="customer-voucher-input" />
                  </div>
                  <Button type="button" variant="secondary" onClick={generateVoucherCode}>Generate</Button>
                </div>
              </div>
              <div className="space-y-2">
                <Label>Plan</Label>
                <Select value={formData.plan} onValueChange={(v) => setFormData({ ...formData, plan: v })}>
                  <SelectTrigger data-testid="customer-plan-select"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="3_devices">3 Devices - R200/month</SelectItem>
                    <SelectItem value="4_devices">4 Devices - R300/month</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <DialogFooter className="gap-2">
                <Button type="button" variant="secondary" onClick={() => setIsAddOpen(false)}>Cancel</Button>
                <Button type="submit" disabled={submitting} className="bg-violet-600 hover:bg-violet-700" data-testid="save-customer-btn">
                  {submitting ? "Saving..." : editingCustomer ? "Update" : "Add Customer"}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>

        {/* Delete Dialog */}
        <Dialog open={isDeleteOpen} onOpenChange={setIsDeleteOpen}>
          <DialogContent className="sm:max-w-md">
            <DialogHeader><DialogTitle className="text-red-600">Delete Customer</DialogTitle></DialogHeader>
            <p className="text-slate-600">Are you sure you want to delete <strong>{deletingCustomer?.name}</strong>?</p>
            <DialogFooter className="gap-2">
              <Button variant="secondary" onClick={() => setIsDeleteOpen(false)}>Cancel</Button>
              <Button onClick={handleDelete} className="bg-red-500 hover:bg-red-600" data-testid="confirm-delete-btn">Delete</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </Layout>
  );
}
