import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Wifi, Smartphone, CreditCard, Shield, ArrowRight } from "lucide-react";

const API_URL = process.env.REACT_APP_BACKEND_URL;

const PLANS = [
  {
    id: "3_devices",
    name: "3 Devices",
    price: 200,
    devices: 3,
    color: "from-violet-600 to-violet-500",
    border: "border-violet-200 hover:border-violet-400",
    badge: "bg-violet-100 text-violet-700",
  },
  {
    id: "4_devices",
    name: "4 Devices",
    price: 300,
    devices: 4,
    color: "from-orange-500 to-amber-500",
    border: "border-orange-200 hover:border-orange-400",
    badge: "bg-orange-100 text-orange-700",
  },
  {
    id: "test",
    name: "Test Plan",
    price: 10,
    devices: 1,
    color: "from-slate-500 to-slate-400",
    border: "border-slate-200 hover:border-slate-400",
    badge: "bg-slate-100 text-slate-600",
  },
];

export default function PaymentPage() {
  const [selectedPlan, setSelectedPlan] = useState(null);
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState(null);

  const handlePay = async () => {
    if (!selectedPlan) {
      setError("Please select a plan");
      return;
    }
    if (!name.trim()) {
      setError("Please enter your name");
      return;
    }
    if (!phone.trim()) {
      setError("Please enter your phone number");
      return;
    }

    setProcessing(true);
    setError(null);

    try {
      const response = await fetch(`${API_URL}/api/payment/initiate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          plan: selectedPlan,
          customer_name: name.trim(),
          customer_phone: phone.trim(),
          customer_email: email.trim() || undefined,
        }),
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || "Payment initiation failed");
      }

      const data = await response.json();

      // Create hidden form and submit to PayFast
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
      setError(err.message);
      setProcessing(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-violet-50/30 to-slate-50">
      {/* Header */}
      <div className="bg-white border-b border-slate-200 shadow-sm">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center gap-3">
          <div className="w-10 h-10 bg-gradient-to-br from-violet-600 to-violet-500 rounded-xl flex items-center justify-center">
            <Wifi className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-slate-900">WiFi Hotspot</h1>
            <p className="text-xs text-slate-500">Get connected instantly</p>
          </div>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 py-8 space-y-8" data-testid="payment-page">
        {/* Title */}
        <div className="text-center space-y-2">
          <h2 className="text-2xl sm:text-3xl font-bold text-slate-900">
            Choose Your WiFi Plan
          </h2>
          <p className="text-slate-500">Select a plan, pay securely, and get your voucher code instantly</p>
        </div>

        {/* Plan Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 max-w-2xl mx-auto">
          {PLANS.map((plan) => (
            <Card
              key={plan.id}
              className={`cursor-pointer transition-all duration-200 ${plan.border} ${
                selectedPlan === plan.id
                  ? "ring-2 ring-violet-500 shadow-lg scale-[1.02]"
                  : "shadow-sm hover:shadow-md"
              }`}
              onClick={() => { setSelectedPlan(plan.id); setError(null); }}
              data-testid={`plan-card-${plan.id}`}
            >
              <CardContent className="p-6 text-center space-y-4">
                <div className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold ${plan.badge}`}>
                  <Wifi className="w-3 h-3" />
                  {plan.devices} Devices
                </div>
                <div>
                  <span className="text-4xl font-bold text-slate-900">R{plan.price}</span>
                  <span className="text-slate-500 text-sm">/month</span>
                </div>
                <p className="text-sm text-slate-500">
                  Connect up to {plan.devices} devices simultaneously
                </p>
                {selectedPlan === plan.id && (
                  <div className="text-violet-600 text-sm font-semibold flex items-center justify-center gap-1">
                    <Shield className="w-4 h-4" /> Selected
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Customer Details */}
        <Card className="max-w-2xl mx-auto border-slate-200">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg flex items-center gap-2">
              <Smartphone className="w-5 h-5 text-violet-600" />
              Your Details
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label htmlFor="name">Full Name *</Label>
                <Input
                  id="name"
                  placeholder="e.g. Thabo Mokoena"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  data-testid="customer-name-input"
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="phone">Phone Number *</Label>
                <Input
                  id="phone"
                  placeholder="e.g. 0812345678"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  data-testid="customer-phone-input"
                />
              </div>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="email">Email (optional)</Label>
              <Input
                id="email"
                type="email"
                placeholder="e.g. thabo@email.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                data-testid="customer-email-input"
              />
            </div>

            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg p-3 text-sm" data-testid="payment-error">
                {error}
              </div>
            )}

            <Button
              onClick={handlePay}
              disabled={processing || !selectedPlan || !name.trim() || !phone.trim()}
              className="w-full h-12 bg-gradient-to-r from-violet-600 to-violet-500 hover:from-violet-700 hover:to-violet-600 text-base font-semibold"
              data-testid="pay-now-btn"
            >
              {processing ? (
                <span className="flex items-center gap-2">
                  <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Redirecting to PayFast...
                </span>
              ) : (
                <span className="flex items-center gap-2">
                  <CreditCard className="w-5 h-5" />
                  Pay R{selectedPlan ? PLANS.find(p => p.id === selectedPlan)?.price : "---"} with PayFast
                  <ArrowRight className="w-4 h-4" />
                </span>
              )}
            </Button>

            <p className="text-xs text-slate-400 text-center flex items-center justify-center gap-1">
              <Shield className="w-3 h-3" />
              Payments processed securely by PayFast
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
