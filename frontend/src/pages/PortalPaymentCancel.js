import { Link } from "react-router-dom";
import { Card, CardContent } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { XCircle } from "lucide-react";

export default function PortalPaymentCancel() {
  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center px-4">
      <Card className="max-w-md w-full border-red-200" data-testid="portal-payment-cancel">
        <CardContent className="p-8 text-center space-y-5">
          <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto">
            <XCircle className="w-8 h-8 text-red-500" />
          </div>
          <h2 className="text-xl font-bold text-slate-900">Payment Cancelled</h2>
          <p className="text-sm text-slate-500">No charges were made.</p>
          <Link to="/portal/buy"><Button className="w-full bg-emerald-600 hover:bg-emerald-700">Try Again</Button></Link>
        </CardContent>
      </Card>
    </div>
  );
}
