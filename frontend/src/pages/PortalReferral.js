import { useState, useEffect, useCallback } from "react";
import { PortalLayout } from "../components/PortalLayout";
import { usePortalAuth } from "../context/PortalAuthContext";
import { Card, CardContent } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import axios from "axios";
import { toast } from "sonner";
import { Users, Copy, Gift, Share2 } from "lucide-react";

const API_URL = process.env.REACT_APP_BACKEND_URL;

export default function PortalReferral() {
  const { getAuthHeader } = usePortalAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(false);
  const [copiedLink, setCopiedLink] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      const res = await axios.get(`${API_URL}/api/portal/referral`, getAuthHeader());
      setData(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [getAuthHeader]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const copyCode = () => {
    navigator.clipboard.writeText(data?.referral_code || "");
    setCopied(true);
    toast.success("Referral code copied!");
    setTimeout(() => setCopied(false), 2000);
  };

  const copyLink = () => {
    navigator.clipboard.writeText(data?.referral_link || "");
    setCopiedLink(true);
    toast.success("Referral link copied!");
    setTimeout(() => setCopiedLink(false), 2000);
  };

  if (loading) return <PortalLayout title="Referrals"><div className="text-center py-12 text-slate-400">Loading...</div></PortalLayout>;

  return (
    <PortalLayout title="Refer a Friend">
      <div className="space-y-6" data-testid="portal-referral">
        {/* Referral Card */}
        <Card className="bg-gradient-to-r from-sky-600 to-sky-500 text-white border-0">
          <CardContent className="p-6 space-y-4">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 bg-white/20 rounded-xl flex items-center justify-center">
                <Gift className="w-6 h-6" />
              </div>
              <div>
                <h3 className="font-bold text-lg">Earn {data?.points_per_referral} bonus points</h3>
                <p className="text-sky-100 text-sm">For every friend who signs up with your code!</p>
              </div>
            </div>
            <div className="bg-white/10 rounded-xl p-4 space-y-3">
              <div>
                <p className="text-xs text-sky-200 mb-1">Your Referral Code</p>
                <div className="flex items-center gap-2">
                  <code className="text-2xl font-bold font-mono tracking-wider" data-testid="referral-code">{data?.referral_code}</code>
                  <Button variant="ghost" size="sm" className="text-white hover:bg-white/20" onClick={copyCode} data-testid="copy-referral-code">
                    <Copy className="w-4 h-4" /> {copied ? "Copied!" : "Copy"}
                  </Button>
                </div>
              </div>
              <div>
                <p className="text-xs text-sky-200 mb-1">Or share this link</p>
                <div className="flex items-center gap-2">
                  <Input
                    readOnly
                    value={data?.referral_link || ""}
                    className="bg-white/10 border-white/20 text-white text-xs"
                    data-testid="referral-link"
                  />
                  <Button variant="ghost" size="sm" className="text-white hover:bg-white/20 shrink-0" onClick={copyLink} data-testid="copy-referral-link">
                    <Share2 className="w-4 h-4" /> {copiedLink ? "Copied!" : "Copy"}
                  </Button>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Stats */}
        <div className="grid grid-cols-2 gap-4">
          <Card className="bg-sky-50 border-0">
            <CardContent className="p-4 text-center">
              <Users className="w-6 h-6 text-sky-600 mx-auto mb-1" />
              <p className="text-2xl font-bold text-sky-700">{data?.total_referrals || 0}</p>
              <p className="text-xs text-slate-500">Total Referrals</p>
            </CardContent>
          </Card>
          <Card className="bg-emerald-50 border-0">
            <CardContent className="p-4 text-center">
              <Gift className="w-6 h-6 text-emerald-600 mx-auto mb-1" />
              <p className="text-2xl font-bold text-emerald-700">{(data?.total_referrals || 0) * (data?.points_per_referral || 5)}</p>
              <p className="text-xs text-slate-500">Points Earned</p>
            </CardContent>
          </Card>
        </div>

        {/* Referral List */}
        <Card className="border-slate-200">
          <CardContent className="p-5">
            <h3 className="font-semibold text-slate-800 mb-3">Your Referrals</h3>
            {data?.referrals?.length === 0 ? (
              <p className="text-sm text-slate-400 py-4 text-center">No referrals yet. Share your code to start earning!</p>
            ) : (
              <div className="space-y-2">
                {data?.referrals?.map((r, i) => (
                  <div key={i} className="flex items-center justify-between py-2 border-b border-slate-100 last:border-0">
                    <span className="text-sm text-slate-700">{r.name}</span>
                    <span className="text-xs text-slate-400">{new Date(r.created_at).toLocaleDateString()}</span>
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
