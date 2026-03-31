import { useState, useEffect } from "react";
import { useSearchParams, Link } from "react-router-dom";
import { Card, CardContent } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { CheckCircle, Wifi, Copy, Clock, ArrowLeft, MessageCircle } from "lucide-react";

const API_URL = process.env.REACT_APP_BACKEND_URL;

export default function PaymentSuccess() {
  const [searchParams] = useSearchParams();
  const [payment, setPayment] = useState(null);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(false);

  const orderId = searchParams.get("order_id");

  useEffect(() => {
    if (!orderId) {
      setLoading(false);
      return;
    }

    const fetchPayment = async () => {
      try {
        const res = await fetch(`${API_URL}/api/payment/verify/${orderId}`);
        if (res.ok) {
          const data = await res.json();
          setPayment(data);
        }
      } catch (err) {
        console.error("Failed to verify payment:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchPayment();

    // Poll every 3 seconds if payment is still pending (waiting for ITN)
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${API_URL}/api/payment/verify/${orderId}`);
        if (res.ok) {
          const data = await res.json();
          setPayment(data);
          if (data.status === "complete") {
            clearInterval(interval);
          }
        }
      } catch (err) {
        // ignore polling errors
      }
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

  const planLabel = payment?.plan === "3_devices" ? "3 Devices" : payment?.plan === "4_devices" ? "4 Devices" : "Test Plan";

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-emerald-50/30 to-slate-50 flex items-center justify-center">
        <div className="text-center space-y-3">
          <div className="animate-spin h-10 w-10 border-4 border-violet-200 border-t-violet-600 rounded-full mx-auto" />
          <p className="text-slate-500">Verifying payment...</p>
        </div>
      </div>
    );
  }

  if (!orderId || !payment) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-slate-100 to-slate-50 flex items-center justify-center px-4">
        <Card className="max-w-md w-full text-center">
          <CardContent className="p-8 space-y-4">
            <p className="text-slate-500">No payment information found.</p>
            <Link to="/pay">
              <Button variant="outline">
                <ArrowLeft className="w-4 h-4 mr-2" /> Back to Plans
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Payment still pending
  if (payment.status === "pending") {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-amber-50/30 to-slate-50 flex items-center justify-center px-4">
        <Card className="max-w-md w-full border-amber-200">
          <CardContent className="p-8 text-center space-y-5" data-testid="payment-pending">
            <div className="w-16 h-16 bg-amber-100 rounded-full flex items-center justify-center mx-auto">
              <Clock className="w-8 h-8 text-amber-600 animate-pulse" />
            </div>
            <h2 className="text-xl font-bold text-slate-900">Processing Payment</h2>
            <p className="text-slate-500 text-sm">
              Your payment is being processed by PayFast. This page will update automatically once confirmed.
            </p>
            <div className="bg-amber-50 rounded-lg p-3 text-sm text-amber-700">
              Order: <span className="font-mono font-semibold">{payment.order_id}</span>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Payment complete - show voucher
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-emerald-50/30 to-slate-50 flex items-center justify-center px-4">
      <Card className="max-w-md w-full border-emerald-200 shadow-lg" data-testid="payment-success">
        <CardContent className="p-8 text-center space-y-6">
          {/* Success Icon */}
          <div className="w-20 h-20 bg-emerald-100 rounded-full flex items-center justify-center mx-auto">
            <CheckCircle className="w-10 h-10 text-emerald-600" />
          </div>

          <div className="space-y-1">
            <h2 className="text-2xl font-bold text-slate-900">Payment Successful!</h2>
            <p className="text-slate-500 text-sm">
              Thank you, {payment.customer_name}
            </p>
          </div>

          {/* Voucher Code Display */}
          <div className="bg-gradient-to-br from-violet-600 to-violet-500 rounded-xl p-6 text-white space-y-3">
            <div className="flex items-center justify-center gap-2 text-violet-200 text-sm">
              <Wifi className="w-4 h-4" />
              Your WiFi Voucher Code
            </div>
            <div
              className="text-3xl font-mono font-bold tracking-widest bg-white/10 rounded-lg py-3 px-4"
              data-testid="voucher-code-display"
            >
              {payment.voucher_code || "Loading..."}
            </div>
            <Button
              variant="ghost"
              className="text-white hover:bg-white/20 text-sm mx-auto"
              onClick={copyVoucher}
              data-testid="copy-voucher-btn"
            >
              <Copy className="w-4 h-4 mr-1.5" />
              {copied ? "Copied!" : "Copy Code"}
            </Button>
          </div>

          {/* Plan Details */}
          <div className="bg-slate-50 rounded-lg p-4 space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-slate-500">Plan</span>
              <span className="font-semibold text-slate-900">{planLabel}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Amount Paid</span>
              <span className="font-semibold text-slate-900">R{payment.amount}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Order ID</span>
              <span className="font-mono text-xs text-slate-600">{payment.order_id}</span>
            </div>
          </div>

          <div className="flex items-center justify-center gap-2 text-emerald-600 text-sm">
            <MessageCircle className="w-4 h-4" />
            <span>Your voucher code has also been sent to your phone</span>
          </div>

          <Link to="/pay">
            <Button variant="outline" className="w-full" data-testid="buy-another-btn">
              <ArrowLeft className="w-4 h-4 mr-2" /> Buy Another Plan
            </Button>
          </Link>
        </CardContent>
      </Card>
    </div>
  );
}
