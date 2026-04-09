import { useState } from "react";
import { PortalLayout } from "../components/PortalLayout";
import { usePortalAuth } from "../context/PortalAuthContext";
import { Card, CardContent } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Wifi, CreditCard, Shield } from "lucide-react";
import axios from "axios";

const API_URL = process.env.REACT_APP_BACKEND_URL;

const PLANS = [
  { id: "1_day", name: "1 Day Pass", price: 10, desc: "1 device, 24 hours", color: "bg-emerald-100 text-emerald-700" },
  { id: "1dev_1week", name: "1 Device", price: 60, desc: "1 week", color: "bg-sky-100 text-sky-700" },
  { id: "1dev_2weeks", name: "1 Device", price: 90, desc: "2 weeks", color: "bg-sky-100 text-sky-700" },
  { id: "1dev_3weeks", name: "1 Device", price: 120, desc: "3 weeks", color: "bg-sky-100 text-sky-700" },
  { id: "1dev_4weeks", name: "1 Device", price: 150, desc: "4 weeks", color: "bg-sky-100 text-sky-700" },
  { id: "2dev_1week", name: "2 Devices", price: 90, desc: "1 week", color: "bg-indigo-100 text-indigo-700" },
  { id: "2dev_2weeks", name: "2 Devices", price: 135, desc: "2 weeks", color: "bg-indigo-100 text-indigo-700" },
  { id: "2dev_3weeks", name: "2 Devices", price: 180, desc: "3 weeks", color: "bg-indigo-100 text-indigo-700" },
  { id: "2dev_4weeks", name: "2 Devices", price: 210, desc: "4 weeks", color: "bg-indigo-100 text-indigo-700" },
];

export default function PortalBuy() {
  const { getAuthHeader } = usePortalAuth();
  const [selectedPlan, setSelectedPlan] = useState(null);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState(null);

  const handleBuy = async () => {
    if (!selectedPlan) return;
    setProcessing(true);
    setError(null);

    try {
      const token = localStorage.getItem("portal_token");
      if (!token) {
        window.location.href = "/portal/login";
        return;
      }
      const { data } = await axios.post(
        `${API_URL}/api/portal/payment/initiate`,
        { plan: selectedPlan },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      const form = document.createElement("form");
      form.method = "POST";
      form.action = data.payfast_url;
      Object.entries(data.form_fields).forEach(([key, value]) => {
        const input = document.createElement("input");
        input.type = "hidden";
        input.name = key;
        input.value = value;
        form.appendChild(input);
      });
      document.body.appendChild(form);
      form.submit();
    } catch (err) {
      if (err.response?.status === 401 || err.response?.status === 403) {
        localStorage.removeItem("portal_token");
        localStorage.removeItem("portal_customer_id");
        window.location.href = "/portal/login";
        return;
      }
      setError(err.response?.data?.detail || err.message || "Payment initiation failed");
      setProcessing(false);
    }
  };

  return (
    <PortalLayout title="Buy a Plan">
      <div className="space-y-6" data-testid="portal-buy-page">
        <p className="text-slate-500 text-sm">Select a plan below and pay securely via PayFast. You'll earn <span className="text-emerald-600 font-semibold">1 point per R10</span> spent!</p>

        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
          {PLANS.map((plan) => (
            <Card
              key={plan.id}
              className={`cursor-pointer transition-all duration-150 ${
                selectedPlan === plan.id ? "ring-2 ring-emerald-500 shadow-lg" : "hover:shadow-md"
              }`}
              onClick={() => { setSelectedPlan(plan.id); setError(null); }}
              data-testid={`portal-plan-${plan.id}`}
            >
              <CardContent className="p-3 text-center space-y-1.5">
                <span className={`inline-block px-2 py-0.5 rounded-full text-[10px] font-semibold ${plan.color}`}>
                  {plan.name}
                </span>
                <div className="text-2xl font-bold text-slate-900">R{plan.price}</div>
                <p className="text-xs text-slate-500">{plan.desc}</p>
                <p className="text-[10px] text-emerald-600">+{Math.floor(plan.price / 10)} pts</p>
              </CardContent>
            </Card>
          ))}
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg p-3 text-sm" data-testid="portal-buy-error">{error}</div>
        )}

        <Button
          onClick={handleBuy}
          disabled={processing || !selectedPlan}
          className="w-full sm:w-auto h-11 bg-emerald-600 hover:bg-emerald-700 font-semibold px-8"
          data-testid="portal-pay-btn"
        >
          {processing ? "Redirecting to PayFast..." : (
            <span className="flex items-center gap-2">
              <CreditCard className="w-4 h-4" />
              Pay R{selectedPlan ? PLANS.find(p => p.id === selectedPlan)?.price : "---"} with PayFast
            </span>
          )}
        </Button>

        <p className="text-xs text-slate-400 flex items-center gap-1"><Shield className="w-3 h-3" /> Secure payment via PayFast</p>
      </div>
    </PortalLayout>
  );
}
