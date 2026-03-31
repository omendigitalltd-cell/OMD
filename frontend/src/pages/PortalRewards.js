import { useState, useEffect, useCallback } from "react";
import { PortalLayout } from "../components/PortalLayout";
import { usePortalAuth } from "../context/PortalAuthContext";
import { Card, CardContent } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import axios from "axios";
import { toast } from "sonner";
import { Gift, Star, Lock, CheckCircle } from "lucide-react";

const API_URL = process.env.REACT_APP_BACKEND_URL;

export default function PortalRewards() {
  const { getAuthHeader } = usePortalAuth();
  const [data, setData] = useState(null);
  const [pointsHistory, setPointsHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [redeeming, setRedeeming] = useState(null);

  const fetchData = useCallback(async () => {
    try {
      const [rRes, pRes] = await Promise.all([
        axios.get(`${API_URL}/api/portal/rewards`, getAuthHeader()),
        axios.get(`${API_URL}/api/portal/points`, getAuthHeader()),
      ]);
      setData(rRes.data);
      setPointsHistory(pRes.data.history);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [getAuthHeader]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleRedeem = async (plan) => {
    if (!window.confirm(`Redeem this reward? This will deduct points from your balance.`)) return;
    setRedeeming(plan);
    try {
      const token = localStorage.getItem("portal_token");
      const res = await axios.post(`${API_URL}/api/portal/redeem`, { plan }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success(`Redeemed! Your voucher code: ${res.data.voucher_code}`);
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Redemption failed");
    } finally {
      setRedeeming(null);
    }
  };

  if (loading) return <PortalLayout title="Rewards"><div className="text-center py-12 text-slate-400">Loading...</div></PortalLayout>;

  return (
    <PortalLayout title="Rewards">
      <div className="space-y-6" data-testid="portal-rewards">
        {/* Points Balance */}
        <Card className="bg-gradient-to-r from-emerald-600 to-emerald-500 text-white border-0">
          <CardContent className="p-6 flex items-center gap-4">
            <div className="w-14 h-14 bg-white/20 rounded-xl flex items-center justify-center">
              <Star className="w-7 h-7" />
            </div>
            <div>
              <p className="text-sm text-emerald-100">Your Points Balance</p>
              <p className="text-3xl font-bold">{data?.balance || 0} <span className="text-lg font-normal text-emerald-200">points</span></p>
            </div>
          </CardContent>
        </Card>

        {/* Reward Tiers */}
        <div>
          <h3 className="font-semibold text-slate-800 mb-3 flex items-center gap-2"><Gift className="w-5 h-5 text-amber-500" /> Available Rewards</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {data?.tiers?.map((tier) => (
              <Card key={tier.plan} className={`transition-all ${tier.can_redeem ? "border-emerald-200 shadow-sm" : "border-slate-200 opacity-70"}`}>
                <CardContent className="p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-semibold text-slate-800">{tier.label}</span>
                    <Badge className="bg-slate-100 text-slate-600">R{tier.value}</Badge>
                  </div>
                  <div className="flex items-center gap-2">
                    <Star className="w-4 h-4 text-amber-500" />
                    <span className="text-sm font-bold text-amber-600">{tier.points_needed} pts</span>
                  </div>
                  {/* Progress bar */}
                  <div className="w-full bg-slate-100 rounded-full h-1.5">
                    <div
                      className="bg-emerald-500 h-1.5 rounded-full transition-all"
                      style={{ width: `${Math.min(100, ((data?.balance || 0) / tier.points_needed) * 100)}%` }}
                    />
                  </div>
                  <Button
                    onClick={() => handleRedeem(tier.plan)}
                    disabled={!tier.can_redeem || redeeming === tier.plan}
                    className={`w-full text-sm h-9 ${tier.can_redeem ? "bg-emerald-600 hover:bg-emerald-700" : "bg-slate-200 text-slate-400"}`}
                    data-testid={`redeem-${tier.plan}`}
                  >
                    {redeeming === tier.plan ? "Redeeming..." : tier.can_redeem ? (
                      <span className="flex items-center gap-1"><CheckCircle className="w-3.5 h-3.5" /> Redeem</span>
                    ) : (
                      <span className="flex items-center gap-1"><Lock className="w-3.5 h-3.5" /> Need {tier.points_needed - (data?.balance || 0)} more</span>
                    )}
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>

        {/* Points History */}
        <Card className="border-slate-200">
          <CardContent className="p-5">
            <h3 className="font-semibold text-slate-800 mb-3">Points History</h3>
            {pointsHistory.length === 0 ? (
              <p className="text-sm text-slate-400 py-4 text-center">No points activity yet. Buy a plan to start earning!</p>
            ) : (
              <div className="space-y-2 max-h-[300px] overflow-y-auto">
                {pointsHistory.map((h) => (
                  <div key={h.id} className="flex items-center justify-between py-2 border-b border-slate-100 last:border-0">
                    <div>
                      <p className="text-sm text-slate-700">{h.description}</p>
                      <p className="text-xs text-slate-400">{new Date(h.created_at).toLocaleDateString()}</p>
                    </div>
                    <span className={`text-sm font-bold ${h.points > 0 ? "text-emerald-600" : "text-red-500"}`}>
                      {h.points > 0 ? "+" : ""}{h.points} pts
                    </span>
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
