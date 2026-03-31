import { useState, useEffect, useCallback } from "react";
import { Layout } from "../components/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Badge } from "../components/ui/badge";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "../components/ui/table";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "../components/ui/select";
import { useAuth } from "../context/AuthContext";
import axios from "axios";
import { toast } from "sonner";
import { Ticket, Plus, Trash2, RefreshCw, Package, CheckCircle, Clock, Upload } from "lucide-react";

const API_URL = process.env.REACT_APP_BACKEND_URL;

const PLAN_LABELS = {
  "1_day": "1 Day",
  "1dev_1week": "1D 1W",
  "1dev_2weeks": "1D 2W",
  "1dev_3weeks": "1D 3W",
  "1dev_4weeks": "1D 4W",
  "2dev_1week": "2D 1W",
  "2dev_2weeks": "2D 2W",
  "2dev_3weeks": "2D 3W",
  "2dev_4weeks": "2D 4W",
  "test": "Test",
};

const PLAN_COLORS = {
  "1_day": "bg-emerald-100 text-emerald-700",
  "1dev_1week": "bg-sky-100 text-sky-700",
  "1dev_2weeks": "bg-sky-100 text-sky-700",
  "1dev_3weeks": "bg-sky-100 text-sky-700",
  "1dev_4weeks": "bg-sky-100 text-sky-700",
  "2dev_1week": "bg-indigo-100 text-indigo-700",
  "2dev_2weeks": "bg-indigo-100 text-indigo-700",
  "2dev_3weeks": "bg-indigo-100 text-indigo-700",
  "2dev_4weeks": "bg-indigo-100 text-indigo-700",
  "test": "bg-slate-100 text-slate-600",
};

export default function Vouchers() {
  const { getAuthHeader } = useAuth();
  const [vouchers, setVouchers] = useState([]);
  const [stats, setStats] = useState(null);
  const [payments, setPayments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [newCodes, setNewCodes] = useState("");
  const [newPlan, setNewPlan] = useState("3_devices");
  const [adding, setAdding] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [csvPlan, setCsvPlan] = useState("3_devices");

  const fetchData = useCallback(async () => {
    try {
      const [vRes, sRes, pRes] = await Promise.all([
        axios.get(`${API_URL}/api/vouchers`, getAuthHeader()),
        axios.get(`${API_URL}/api/vouchers/stats`, getAuthHeader()),
        axios.get(`${API_URL}/api/admin/payments`, getAuthHeader()),
      ]);
      setVouchers(vRes.data);
      setStats(sRes.data);
      setPayments(pRes.data);
    } catch (err) {
      console.error("Failed to fetch voucher data:", err);
    } finally {
      setLoading(false);
    }
  }, [getAuthHeader]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleAddCodes = async () => {
    const codes = newCodes.split("\n").map(c => c.trim()).filter(Boolean);
    if (codes.length === 0) {
      toast.error("Enter at least one voucher code");
      return;
    }
    setAdding(true);
    try {
      const res = await axios.post(
        `${API_URL}/api/vouchers/add`,
        { codes, plan: newPlan },
        getAuthHeader()
      );
      toast.success(res.data.message);
      setNewCodes("");
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to add codes");
    } finally {
      setAdding(false);
    }
  };

  const handleCsvUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("plan", csvPlan);
      const token = localStorage.getItem("token");
      const res = await axios.post(
        `${API_URL}/api/vouchers/upload-csv`,
        formData,
        { headers: { "Content-Type": "multipart/form-data", Authorization: `Bearer ${token}` } }
      );
      toast.success(res.data.message);
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || "CSV upload failed");
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm("Delete this voucher code?")) return;
    try {
      await axios.delete(`${API_URL}/api/vouchers/${id}`, getAuthHeader());
      toast.success("Voucher deleted");
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to delete");
    }
  };

  const formatDate = (iso) => iso ? new Date(iso).toLocaleString() : "-";

  return (
    <Layout title="Voucher Management">
      <div className="space-y-6" data-testid="vouchers-page">
        {/* Stats */}
        {stats && (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
            {Object.entries(stats).map(([plan, s]) => (
              <Card key={plan} className="bg-slate-50 border-0">
                <CardContent className="p-3 text-center">
                  <p className="text-xs text-slate-500 mb-1">{PLAN_LABELS[plan] || plan}</p>
                  <p className="text-lg font-bold text-slate-800">{s.available} <span className="text-xs font-normal text-slate-400">/ {s.total}</span></p>
                  <p className="text-[10px] text-slate-400">{s.assigned} assigned</p>
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {/* Add Codes */}
        <Card className="border-slate-200">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg flex items-center gap-2">
              <Plus className="w-5 h-5 text-violet-600" />
              Add Voucher Codes
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              <div className="lg:col-span-2">
                <textarea
                  className="w-full min-h-[100px] border border-slate-200 rounded-lg p-3 text-sm font-mono focus:ring-2 focus:ring-violet-500 focus:border-violet-500 outline-none resize-y"
                  placeholder={"Enter voucher codes, one per line:\nVOUCH-001\nVOUCH-002\nVOUCH-003"}
                  value={newCodes}
                  onChange={(e) => setNewCodes(e.target.value)}
                  data-testid="voucher-codes-textarea"
                />
              </div>
              <div className="space-y-3">
                <Select value={newPlan} onValueChange={setNewPlan}>
                  <SelectTrigger data-testid="voucher-plan-select">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="1_day">1 Day Pass (R10)</SelectItem>
                    <SelectItem value="1dev_1week">1 Device 1 Week (R60)</SelectItem>
                    <SelectItem value="1dev_2weeks">1 Device 2 Weeks (R90)</SelectItem>
                    <SelectItem value="1dev_3weeks">1 Device 3 Weeks (R120)</SelectItem>
                    <SelectItem value="1dev_4weeks">1 Device 4 Weeks (R150)</SelectItem>
                    <SelectItem value="2dev_1week">2 Devices 1 Week (R90)</SelectItem>
                    <SelectItem value="2dev_2weeks">2 Devices 2 Weeks (R135)</SelectItem>
                    <SelectItem value="2dev_3weeks">2 Devices 3 Weeks (R180)</SelectItem>
                    <SelectItem value="2dev_4weeks">2 Devices 4 Weeks (R210)</SelectItem>
                  </SelectContent>
                </Select>
                <Button
                  onClick={handleAddCodes}
                  disabled={adding || !newCodes.trim()}
                  className="w-full bg-violet-600 hover:bg-violet-700"
                  data-testid="add-vouchers-btn"
                >
                  {adding ? <RefreshCw className="w-4 h-4 mr-2 animate-spin" /> : <Plus className="w-4 h-4 mr-2" />}
                  Add Codes
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* CSV Upload */}
        <Card className="border-slate-200">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg flex items-center gap-2">
              <Upload className="w-5 h-5 text-violet-600" />
              Upload CSV
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col sm:flex-row items-start sm:items-end gap-4">
              <div className="space-y-1.5 flex-1">
                <p className="text-xs text-slate-500">Upload a CSV file with voucher codes in the first column (one code per row). Header row is auto-skipped.</p>
                <input
                  type="file"
                  accept=".csv,.txt"
                  onChange={handleCsvUpload}
                  disabled={uploading}
                  className="block w-full text-sm text-slate-500 file:mr-3 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-violet-50 file:text-violet-700 hover:file:bg-violet-100 file:cursor-pointer cursor-pointer"
                  data-testid="csv-upload-input"
                />
              </div>
              <div className="w-full sm:w-48">
                <Select value={csvPlan} onValueChange={setCsvPlan}>
                  <SelectTrigger data-testid="csv-plan-select">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="1_day">1 Day Pass (R10)</SelectItem>
                    <SelectItem value="1dev_1week">1 Device 1 Week (R60)</SelectItem>
                    <SelectItem value="1dev_2weeks">1 Device 2 Weeks (R90)</SelectItem>
                    <SelectItem value="1dev_3weeks">1 Device 3 Weeks (R120)</SelectItem>
                    <SelectItem value="1dev_4weeks">1 Device 4 Weeks (R150)</SelectItem>
                    <SelectItem value="2dev_1week">2 Devices 1 Week (R90)</SelectItem>
                    <SelectItem value="2dev_2weeks">2 Devices 2 Weeks (R135)</SelectItem>
                    <SelectItem value="2dev_3weeks">2 Devices 3 Weeks (R180)</SelectItem>
                    <SelectItem value="2dev_4weeks">2 Devices 4 Weeks (R210)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            {uploading && (
              <div className="mt-3 flex items-center gap-2 text-sm text-violet-600">
                <RefreshCw className="w-4 h-4 animate-spin" /> Processing CSV...
              </div>
            )}
          </CardContent>
        </Card>

        {/* Voucher Pool */}
        <Card className="border-slate-200">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-lg flex items-center gap-2">
                <Ticket className="w-5 h-5 text-violet-600" />
                Voucher Pool ({vouchers.length})
              </CardTitle>
              <Button variant="ghost" size="icon" onClick={fetchData} data-testid="refresh-vouchers-btn">
                <RefreshCw className="w-4 h-4" />
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="py-8 text-center text-slate-400">Loading...</div>
            ) : vouchers.length === 0 ? (
              <div className="py-12 text-center">
                <Package className="w-12 h-12 text-slate-200 mx-auto mb-3" />
                <p className="text-slate-500">No voucher codes yet</p>
                <p className="text-xs text-slate-400 mt-1">Add codes above to get started</p>
              </div>
            ) : (
              <div className="overflow-x-auto max-h-[400px] overflow-y-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Code</TableHead>
                      <TableHead>Plan</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Assigned To</TableHead>
                      <TableHead>Added</TableHead>
                      <TableHead className="w-10"></TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {vouchers.map((v) => (
                      <TableRow key={v.id} data-testid={`voucher-row-${v.id}`}>
                        <TableCell className="font-mono font-semibold text-sm">{v.code}</TableCell>
                        <TableCell>
                          <Badge className={PLAN_COLORS[v.plan] || "bg-slate-100 text-slate-600"}>
                            {PLAN_LABELS[v.plan] || v.plan}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          {v.assigned ? (
                            <Badge className="bg-emerald-100 text-emerald-700"><CheckCircle className="w-3 h-3 mr-1" />Assigned</Badge>
                          ) : (
                            <Badge className="bg-slate-100 text-slate-600"><Clock className="w-3 h-3 mr-1" />Available</Badge>
                          )}
                        </TableCell>
                        <TableCell className="text-xs text-slate-500 font-mono">{v.assigned_to || "-"}</TableCell>
                        <TableCell className="text-xs text-slate-500">{formatDate(v.created_at)}</TableCell>
                        <TableCell>
                          {!v.assigned && (
                            <Button variant="ghost" size="icon" className="text-red-400 hover:text-red-600" onClick={() => handleDelete(v.id)}>
                              <Trash2 className="w-4 h-4" />
                            </Button>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Recent Payments */}
        <Card className="border-slate-200">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg flex items-center gap-2">
              <Package className="w-5 h-5 text-emerald-600" />
              Recent Payments ({payments.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            {payments.length === 0 ? (
              <div className="py-8 text-center text-slate-400">No payments yet</div>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Date</TableHead>
                      <TableHead>Customer</TableHead>
                      <TableHead>Phone</TableHead>
                      <TableHead>Plan</TableHead>
                      <TableHead>Amount</TableHead>
                      <TableHead>Voucher</TableHead>
                      <TableHead>Status</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {payments.map((p) => (
                      <TableRow key={p.id} data-testid={`payment-row-${p.id}`}>
                        <TableCell className="text-xs">{formatDate(p.created_at)}</TableCell>
                        <TableCell className="font-medium">{p.customer_name}</TableCell>
                        <TableCell className="font-mono text-xs">{p.customer_phone}</TableCell>
                        <TableCell>
                          <Badge className={PLAN_COLORS[p.plan] || "bg-slate-100 text-slate-600"}>
                            {PLAN_LABELS[p.plan] || p.plan}
                          </Badge>
                        </TableCell>
                        <TableCell className="font-semibold">R{p.amount}</TableCell>
                        <TableCell className="font-mono text-xs">{p.voucher_code || "-"}</TableCell>
                        <TableCell>
                          <Badge className={
                            p.status === "complete" ? "bg-emerald-100 text-emerald-700" :
                            p.status === "failed" ? "bg-red-100 text-red-700" :
                            "bg-amber-100 text-amber-700"
                          }>
                            {p.status}
                          </Badge>
                        </TableCell>
                      </TableRow>
                    ))}
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
