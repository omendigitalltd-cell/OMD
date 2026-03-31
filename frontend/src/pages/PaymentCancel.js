import { Link } from "react-router-dom";
import { Card, CardContent } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { XCircle, ArrowLeft } from "lucide-react";

export default function PaymentCancel() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-red-50/20 to-slate-50 flex items-center justify-center px-4">
      <Card className="max-w-md w-full border-red-200" data-testid="payment-cancel">
        <CardContent className="p-8 text-center space-y-6">
          <div className="w-20 h-20 bg-red-100 rounded-full flex items-center justify-center mx-auto">
            <XCircle className="w-10 h-10 text-red-500" />
          </div>

          <div className="space-y-1">
            <h2 className="text-2xl font-bold text-slate-900">Payment Cancelled</h2>
            <p className="text-slate-500 text-sm">
              Your payment was not processed. No charges have been made.
            </p>
          </div>

          <p className="text-sm text-slate-400">
            You can try again anytime. If you're having issues, please contact support.
          </p>

          <Link to="/pay">
            <Button className="w-full bg-violet-600 hover:bg-violet-700" data-testid="try-again-btn">
              <ArrowLeft className="w-4 h-4 mr-2" /> Try Again
            </Button>
          </Link>
        </CardContent>
      </Card>
    </div>
  );
}
