import { useState, useEffect } from "react";
import { useSearchParams, Link } from "react-router-dom";
import { Card, CardContent } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { CheckCircle, Wifi, Copy, Clock, Star } from "lucide-react";

const API_URL = process.env.REACT_APP_BACKEND_URL;

export default function PortalPaymentSuccess() {
  const [searchParams] = useSearchParams();
  const [payment, setPayment] = useState(null);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(false);
  const orderId = searchParams.get("order_id");

  useEffect(() => {
    if (!orderId) { setLoading(false); return; }

    const fetchPayment = async () => {
      try {
        const res = await fetch(`${API_URL}/api/payment/verify/${orderId}`);
        if (res.ok) setPayment(await res.json());
      } catch (err) { console.error(err); }
      finally { setLoading(false); }
    };
    fetchPayment();

    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${API_URL}/api/payment/verify/${orderId}`);
        if (res.ok) {
          const data = await res.json();
          setPayment(data);
          if (data.status === "complete") clearInterval(interval);
        }
      } catch (err) {}
    }, 3000);
    return () => clearInterval(interval);
  }, [orderId]);

  const copyVoucher = () => {
    if (payment?.voucher_code) {
      navigator.clipboard.writeText(payment.voucher_code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  if (loading) return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center">
      <div className="animate-spin h-10 w-10 border-4 border-emerald-200 border-t-emerald-600 rounded-full" />
    </div>
  );

  if (!orderId || !payment) return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center px-4">
      <Card className="max-w-md w-full text-center">
        <CardContent className="p-8">
          <p className="text-slate-500 mb-4">No payment found.</p>
          <Link to="/portal/buy"><Button variant="outline">Back to Plans</Button></Link>
        </CardContent>
      </Card>
    </div>
  );

  if (payment.status === "pending") return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center px-4">
      <Card className="max-w-md w-full border-amber-200">
        <CardContent className="p-8 text-center space-y-4" data-testid="portal-payment-pending">
          <Clock className="w-12 h-12 text-amber-500 mx-auto animate-pulse" />
          <h2 className="text-xl font-bold text-slate-900">Processing Payment</h2>
          <p className="text-sm text-slate-500">This page updates automatically.</p>
          <p className="font-mono text-xs text-slate-400">{payment.order_id}</p>
        </CardContent>
      </Card>
    </div>
  );

  const pointsEarned = Math.floor(payment.amount / 10);

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center px-4">
      <Card className="max-w-md w-full border-emerald-200 shadow-lg" data-testid="portal-payment-success">
        <CardContent className="p-8 text-center space-y-5">
          <div className="w-16 h-16 bg-emerald-100 rounded-full flex items-center justify-center mx-auto">
            <CheckCircle className="w-8 h-8 text-emerald-600" />
          </div>
          <h2 className="text-2xl font-bold text-slate-900">Payment Successful!</h2>

          {/* Voucher */}
          <div className="bg-gradient-to-br from-emerald-600 to-emerald-500 rounded-xl p-5 text-white space-y-2">
            <div className="flex items-center justify-center gap-2 text-emerald-200 text-sm">
              <Wifi className="w-4 h-4" /> Your Voucher Code
            </div>
            <div className="text-3xl font-mono font-bold tracking-widest bg-white/10 rounded-lg py-3 px-4" data-testid="portal-voucher-display">
              {payment.voucher_code || "Loading..."}
            </div>
            <Button variant="ghost" className="text-white hover:bg-white/20 text-sm mx-auto" onClick={copyVoucher}>
              <Copy className="w-4 h-4 mr-1" /> {copied ? "Copied!" : "Copy Code"}
            </Button>
          </div>

          {/* Points earned */}
          {pointsEarned > 0 && (
            <div className="bg-amber-50 rounded-lg p-3 flex items-center justify-center gap-2 text-amber-700">
              <Star className="w-4 h-4" />
              <span className="text-sm font-semibold">You earned {pointsEarned} loyalty points!</span>
            </div>
          )}

          <div className="bg-slate-50 rounded-lg p-3 text-sm space-y-1">
            <div className="flex justify-between"><span className="text-slate-500">Amount</span><span className="font-semibold">R{payment.amount}</span></div>
            <div className="flex justify-between"><span className="text-slate-500">Order</span><span className="font-mono text-xs">{payment.order_id}</span></div>
          </div>

          <Link to="/portal"><Button className="w-full bg-emerald-600 hover:bg-emerald-700">Go to Dashboard</Button></Link>
        </CardContent>
      </Card>
    </div>
  );
}
