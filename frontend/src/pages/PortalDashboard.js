import { useState, useEffect, useCallback } from "react";
import { PortalLayout } from "../components/PortalLayout";
import { usePortalAuth } from "../context/PortalAuthContext";
import { Card, CardContent } from "../components/ui/card";
import { Link } from "react-router-dom";
import axios from "axios";
import { Star, ShoppingBag, Gift, Users, ArrowRight } from "lucide-react";

const API_URL = process.env.REACT_APP_BACKEND_URL;

export default function PortalDashboard() {
  const { getAuthHeader } = usePortalAuth();
  const [profile, setProfile] = useState(null);
  const [purchases, setPurchases] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    try {
      const [pRes, purchRes] = await Promise.all([
        axios.get(`${API_URL}/api/portal/profile`, getAuthHeader()),
        axios.get(`${API_URL}/api/portal/purchases`, getAuthHeader()),
      ]);
      setProfile(pRes.data);
      setPurchases(purchRes.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [getAuthHeader]);

  useEffect(() => { fetchData(); }, [fetchData]);

  if (loading) return <PortalLayout title="Dashboard"><div className="text-center py-12 text-slate-400">Loading...</div></PortalLayout>;

  return (
    <PortalLayout title={`Welcome, ${profile?.name || "Customer"}`}>
      <div className="space-y-6" data-testid="portal-dashboard">
        {/* Stats */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <Card className="bg-emerald-50 border-0">
            <CardContent className="p-4 flex items-center gap-3">
              <div className="w-10 h-10 bg-emerald-100 rounded-lg flex items-center justify-center">
                <Star className="w-5 h-5 text-emerald-600" />
              </div>
              <div>
                <p className="text-xs text-slate-500">Points</p>
                <p className="text-xl font-bold text-emerald-700">{profile?.points || 0}</p>
              </div>
            </CardContent>
          </Card>
          <Card className="bg-violet-50 border-0">
            <CardContent className="p-4 flex items-center gap-3">
              <div className="w-10 h-10 bg-violet-100 rounded-lg flex items-center justify-center">
                <ShoppingBag className="w-5 h-5 text-violet-600" />
              </div>
              <div>
                <p className="text-xs text-slate-500">Purchases</p>
                <p className="text-xl font-bold text-violet-700">{purchases.length}</p>
              </div>
            </CardContent>
          </Card>
          <Card className="bg-amber-50 border-0">
            <CardContent className="p-4 flex items-center gap-3">
              <div className="w-10 h-10 bg-amber-100 rounded-lg flex items-center justify-center">
                <Gift className="w-5 h-5 text-amber-600" />
              </div>
              <div>
                <p className="text-xs text-slate-500">Redeemed</p>
                <p className="text-xl font-bold text-amber-700">{purchases.filter(p => p.payment_type === "redemption").length}</p>
              </div>
            </CardContent>
          </Card>
          <Card className="bg-sky-50 border-0">
            <CardContent className="p-4 flex items-center gap-3">
              <div className="w-10 h-10 bg-sky-100 rounded-lg flex items-center justify-center">
                <Users className="w-5 h-5 text-sky-600" />
              </div>
              <div>
                <p className="text-xs text-slate-500">Referrals</p>
                <p className="text-xl font-bold text-sky-700">{profile?.referral_count || 0}</p>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Quick Actions */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <Link to="/portal/buy">
            <Card className="border-emerald-200 hover:border-emerald-400 hover:shadow-md transition-all cursor-pointer">
              <CardContent className="p-5 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <ShoppingBag className="w-5 h-5 text-emerald-600" />
                  <span className="font-semibold text-slate-800">Buy a Plan</span>
                </div>
                <ArrowRight className="w-4 h-4 text-slate-400" />
              </CardContent>
            </Card>
          </Link>
          <Link to="/portal/rewards">
            <Card className="border-amber-200 hover:border-amber-400 hover:shadow-md transition-all cursor-pointer">
              <CardContent className="p-5 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Gift className="w-5 h-5 text-amber-600" />
                  <span className="font-semibold text-slate-800">Redeem Rewards</span>
                </div>
                <ArrowRight className="w-4 h-4 text-slate-400" />
              </CardContent>
            </Card>
          </Link>
          <Link to="/portal/referral">
            <Card className="border-sky-200 hover:border-sky-400 hover:shadow-md transition-all cursor-pointer">
              <CardContent className="p-5 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Users className="w-5 h-5 text-sky-600" />
                  <span className="font-semibold text-slate-800">Refer a Friend</span>
                </div>
                <ArrowRight className="w-4 h-4 text-slate-400" />
              </CardContent>
            </Card>
          </Link>
        </div>

        {/* Recent Purchases */}
        <Card className="border-slate-200">
          <CardContent className="p-5">
            <h3 className="font-semibold text-slate-800 mb-3">Recent Purchases</h3>
            {purchases.length === 0 ? (
              <p className="text-slate-400 text-sm py-4 text-center">No purchases yet. <Link to="/portal/buy" className="text-emerald-600 hover:underline">Buy your first plan!</Link></p>
            ) : (
              <div className="space-y-2">
                {purchases.slice(0, 5).map((p) => (
                  <div key={p.id} className="flex items-center justify-between py-2 border-b border-slate-100 last:border-0">
                    <div>
                      <p className="text-sm font-medium text-slate-800">{p.plan}</p>
                      <p className="text-xs text-slate-400">{new Date(p.created_at).toLocaleDateString()}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-semibold text-slate-800">{p.amount > 0 ? `R${p.amount}` : "Free (Redeemed)"}</p>
                      {p.voucher_code && <p className="text-xs font-mono text-emerald-600">{p.voucher_code}</p>}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </PortalLayout>
  );
}
