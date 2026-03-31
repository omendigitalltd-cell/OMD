import { useState, useEffect, useCallback } from "react";
import { PortalLayout } from "../components/PortalLayout";
import { usePortalAuth } from "../context/PortalAuthContext";
import { Card, CardContent } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table";
import axios from "axios";
import { History, Copy } from "lucide-react";

const API_URL = process.env.REACT_APP_BACKEND_URL;

const PLAN_LABELS = {
  "1_day": "1 Day Pass", "1dev_1week": "1 Dev 1W", "1dev_2weeks": "1 Dev 2W",
  "1dev_3weeks": "1 Dev 3W", "1dev_4weeks": "1 Dev 4W", "2dev_1week": "2 Dev 1W",
  "2dev_2weeks": "2 Dev 2W", "2dev_3weeks": "2 Dev 3W", "2dev_4weeks": "2 Dev 4W",
  "3_devices": "3 Dev Mon", "4_devices": "4 Dev Mon", "test": "Test",
};

export default function PortalHistory() {
  const { getAuthHeader } = usePortalAuth();
  const [purchases, setPurchases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [copiedId, setCopiedId] = useState(null);

  const fetchData = useCallback(async () => {
    try {
      const res = await axios.get(`${API_URL}/api/portal/purchases`, getAuthHeader());
      setPurchases(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [getAuthHeader]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const copyCode = (code, id) => {
    navigator.clipboard.writeText(code);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 1500);
  };

  return (
    <PortalLayout title="Purchase History">
      <div className="space-y-4" data-testid="portal-history">
        {loading ? (
          <div className="text-center py-12 text-slate-400">Loading...</div>
        ) : purchases.length === 0 ? (
          <Card className="border-slate-200">
            <CardContent className="py-12 text-center">
              <History className="w-12 h-12 text-slate-200 mx-auto mb-3" />
              <p className="text-slate-500">No purchases yet</p>
            </CardContent>
          </Card>
        ) : (
          <Card className="border-slate-200">
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Date</TableHead>
                      <TableHead>Plan</TableHead>
                      <TableHead>Amount</TableHead>
                      <TableHead>Voucher Code</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead>Status</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {purchases.map((p) => (
                      <TableRow key={p.id}>
                        <TableCell className="text-xs text-slate-500">{new Date(p.created_at).toLocaleDateString()}</TableCell>
                        <TableCell>
                          <Badge className="bg-slate-100 text-slate-700 text-xs">{PLAN_LABELS[p.plan] || p.plan}</Badge>
                        </TableCell>
                        <TableCell className="font-semibold">{p.amount > 0 ? `R${p.amount}` : "Free"}</TableCell>
                        <TableCell>
                          {p.voucher_code ? (
                            <button
                              onClick={() => copyCode(p.voucher_code, p.id)}
                              className="flex items-center gap-1 font-mono text-sm text-emerald-700 bg-emerald-50 px-2 py-1 rounded hover:bg-emerald-100"
                              data-testid={`copy-voucher-${p.id}`}
                            >
                              {p.voucher_code}
                              <Copy className="w-3 h-3" />
                              {copiedId === p.id && <span className="text-[10px] text-emerald-500">Copied!</span>}
                            </button>
                          ) : "-"}
                        </TableCell>
                        <TableCell className="text-xs">
                          {p.payment_type === "redemption" ? (
                            <Badge className="bg-amber-100 text-amber-700">Redeemed</Badge>
                          ) : (
                            <Badge className="bg-sky-100 text-sky-700">Purchased</Badge>
                          )}
                        </TableCell>
                        <TableCell>
                          <Badge className={p.status === "complete" ? "bg-emerald-100 text-emerald-700" : p.status === "pending" ? "bg-amber-100 text-amber-700" : "bg-red-100 text-red-700"}>
                            {p.status}
                          </Badge>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </PortalLayout>
  );
}
