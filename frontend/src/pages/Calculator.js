import { useState, useEffect } from "react";
import { Layout } from "../components/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import { useAuth } from "../context/AuthContext";
import axios from "axios";
import { toast } from "sonner";
import { Calculator as CalcIcon, Calendar, DollarSign, Info, RotateCcw } from "lucide-react";

const API_URL = process.env.REACT_APP_BACKEND_URL;

const DURATION_OPTIONS = [
  { value: "1", label: "1 Week (7 days)" },
  { value: "2", label: "2 Weeks (14 days)" },
  { value: "3", label: "3 Weeks (21 days)" },
  { value: "4", label: "4 Weeks (28 days)" },
];

export default function Calculator() {
  const { getAuthHeader } = useAuth();
  const [months, setMonths] = useState([]);
  
  // Pro-rata state
  const [selectedMonth, setSelectedMonth] = useState("1");
  const [selectedDay, setSelectedDay] = useState("1");
  const [selectedPlan, setSelectedPlan] = useState("3_devices");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  // Refund state
  const [refundAmount, setRefundAmount] = useState("");
  const [refundDuration, setRefundDuration] = useState("1");
  const [voucherStartDate, setVoucherStartDate] = useState(new Date().toISOString().split("T")[0]);
  const [refundStartDate, setRefundStartDate] = useState(new Date().toISOString().split("T")[0]);
  const [refundResult, setRefundResult] = useState(null);
  const [refundLoading, setRefundLoading] = useState(false);

  useEffect(() => {
    const fetchMonths = async () => {
      try {
        const response = await axios.get(`${API_URL}/api/prorata/months-2026`, getAuthHeader());
        setMonths(response.data);
      } catch (error) {
        console.error("Failed to fetch months:", error);
      }
    };
    fetchMonths();
  }, [getAuthHeader]);

  const selectedMonthData = months.find((m) => m.month === parseInt(selectedMonth));
  const daysInMonth = selectedMonthData?.days || 31;

  const handleCalculate = async () => {
    setLoading(true);
    try {
      const response = await axios.post(
        `${API_URL}/api/prorata/calculate`,
        {
          start_day: parseInt(selectedDay),
          month: parseInt(selectedMonth),
          year: 2026,
          plan: selectedPlan,
        },
        getAuthHeader()
      );
      setResult(response.data);
      toast.success("Pro-rata calculated!");
    } catch (error) {
      toast.error(error.response?.data?.detail || "Calculation failed");
    } finally {
      setLoading(false);
    }
  };

  const handleRefundCalculate = async () => {
    if (!refundAmount || parseFloat(refundAmount) <= 0) {
      toast.error("Please enter a valid amount");
      return;
    }

    if (new Date(refundStartDate) < new Date(voucherStartDate)) {
      toast.error("Refund date cannot be before voucher start date");
      return;
    }
    
    setRefundLoading(true);
    try {
      const response = await axios.post(
        `${API_URL}/api/refund/calculate`,
        {
          amount: parseFloat(refundAmount),
          duration_weeks: parseInt(refundDuration),
          voucher_start_date: voucherStartDate,
          refund_start_date: refundStartDate,
        },
        getAuthHeader()
      );
      setRefundResult(response.data);
      toast.success("Refund calculated!");
    } catch (error) {
      toast.error(error.response?.data?.detail || "Calculation failed");
    } finally {
      setRefundLoading(false);
    }
  };

  return (
    <Layout title="Calculator">
      <div data-testid="calculator-page">
        <Tabs defaultValue="prorata" className="space-y-6">
          <TabsList className="bg-slate-100">
            <TabsTrigger value="prorata" className="data-[state=active]:bg-white" data-testid="prorata-tab">
              <CalcIcon className="w-4 h-4 mr-2" />
              Pro-rata Calculator
            </TabsTrigger>
            <TabsTrigger value="refund" className="data-[state=active]:bg-white" data-testid="refund-tab">
              <RotateCcw className="w-4 h-4 mr-2" />
              Refund Calculator
            </TabsTrigger>
          </TabsList>

          {/* Pro-rata Tab */}
          <TabsContent value="prorata">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              {/* Input Section */}
              <div className="space-y-6">
                <Card className="border-slate-200 bg-white">
                  <CardHeader>
                    <CardTitle className="text-lg font-bold font-heading flex items-center gap-2">
                      <CalcIcon className="w-5 h-5 text-violet-600" />
                      Calculate Pro-rata for 2026
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-6">
                    {/* Month Selection */}
                    <div className="space-y-2">
                      <Label>Select Month</Label>
                      <Select value={selectedMonth} onValueChange={setSelectedMonth}>
                        <SelectTrigger data-testid="month-select">
                          <SelectValue placeholder="Select month" />
                        </SelectTrigger>
                        <SelectContent>
                          {months.map((month) => (
                            <SelectItem key={month.month} value={month.month.toString()}>
                              {month.name} ({month.days} days)
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>

                    {/* Day Selection */}
                    <div className="space-y-2">
                      <Label>Start Day</Label>
                      <Select value={selectedDay} onValueChange={setSelectedDay}>
                        <SelectTrigger data-testid="day-select">
                          <SelectValue placeholder="Select start day" />
                        </SelectTrigger>
                        <SelectContent>
                          {Array.from({ length: daysInMonth }, (_, i) => i + 1).map((day) => (
                            <SelectItem key={day} value={day.toString()}>
                              Day {day}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>

                    {/* Plan Selection */}
                    <div className="space-y-2">
                      <Label>Select Plan</Label>
                      <Select value={selectedPlan} onValueChange={setSelectedPlan}>
                        <SelectTrigger data-testid="plan-select">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="3_devices">3 Devices - R200/month</SelectItem>
                          <SelectItem value="4_devices">4 Devices - R300/month</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    <Button
                      onClick={handleCalculate}
                      disabled={loading}
                      className="w-full bg-violet-600 hover:bg-violet-700 h-12 text-lg font-medium"
                      data-testid="calculate-btn"
                    >
                      {loading ? "Calculating..." : "Calculate Pro-rata"}
                    </Button>
                  </CardContent>
                </Card>

                {/* Info Card */}
                <Card className="border-slate-200 bg-slate-50">
                  <CardContent className="p-4">
                    <div className="flex items-start gap-3">
                      <Info className="w-5 h-5 text-violet-600 mt-0.5" />
                      <div className="text-sm text-slate-600">
                        <p className="font-medium text-slate-700 mb-1">How it works</p>
                        <p>
                          Pro-rata is calculated by dividing the monthly rate by the number of days
                          in the month, then multiplying by the number of days the customer will use
                          the service.
                        </p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Result Section */}
              <div className="space-y-6">
                {result ? (
                  <Card className="border-slate-200 bg-white animate-fade-in" data-testid="result-card">
                    <CardHeader className="pb-2">
                      <CardTitle className="text-lg font-bold font-heading flex items-center gap-2">
                        <DollarSign className="w-5 h-5 text-violet-600" />
                        Calculation Result
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      {/* Main Result */}
                      <div className="bg-gradient-to-br from-violet-600 to-violet-700 rounded-xl p-6 text-white mb-6">
                        <p className="text-sm opacity-90 mb-1">Pro-rata Amount</p>
                        <p className="text-5xl font-extrabold font-mono" data-testid="prorata-amount">
                          R{result.prorata_amount.toFixed(2)}
                        </p>
                        <p className="text-sm opacity-75 mt-2">
                          For {result.days_used} days in {result.month_name} 2026
                        </p>
                      </div>

                      {/* Breakdown */}
                      <div className="space-y-4">
                        <h4 className="font-semibold text-slate-700 flex items-center gap-2">
                          <Calendar className="w-4 h-4" />
                          Calculation Breakdown
                        </h4>
                        
                        <div className="grid grid-cols-2 gap-4">
                          <div className="bg-slate-50 rounded-lg p-4">
                            <p className="text-xs text-slate-500 uppercase tracking-wide">Month</p>
                            <p className="text-lg font-bold text-slate-900 mt-1" data-testid="result-month">
                              {result.month_name} 2026
                            </p>
                          </div>
                          <div className="bg-slate-50 rounded-lg p-4">
                            <p className="text-xs text-slate-500 uppercase tracking-wide">Plan Rate</p>
                            <p className="text-lg font-bold text-slate-900 mt-1 font-mono" data-testid="result-rate">
                              R{result.monthly_rate}
                            </p>
                          </div>
                          <div className="bg-slate-50 rounded-lg p-4">
                            <p className="text-xs text-slate-500 uppercase tracking-wide">Start Day</p>
                            <p className="text-lg font-bold text-slate-900 mt-1" data-testid="result-start-day">
                              Day {result.start_day}
                            </p>
                          </div>
                          <div className="bg-slate-50 rounded-lg p-4">
                            <p className="text-xs text-slate-500 uppercase tracking-wide">Days in Month</p>
                            <p className="text-lg font-bold text-slate-900 mt-1" data-testid="result-days-in-month">
                              {result.days_in_month} days
                            </p>
                          </div>
                        </div>

                        {/* Formula */}
                        <div className="bg-violet-50 rounded-lg p-4 mt-4">
                          <p className="text-xs text-violet-700 uppercase tracking-wide mb-2">Formula</p>
                          <p className="font-mono text-sm text-slate-700" data-testid="result-formula">
                            R{result.monthly_rate} ÷ {result.days_in_month} days × {result.days_used} days = <strong>R{result.prorata_amount.toFixed(2)}</strong>
                          </p>
                          <p className="text-xs text-slate-500 mt-2">
                            Daily rate: R{result.daily_rate.toFixed(2)}
                          </p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ) : (
                  <Card className="border-slate-200 bg-white border-dashed">
                    <CardContent className="py-16 text-center">
                      <CalcIcon className="w-16 h-16 text-slate-200 mx-auto mb-4" />
                      <p className="text-slate-500">
                        Select options and click "Calculate Pro-rata" to see the result
                      </p>
                    </CardContent>
                  </Card>
                )}

                {/* Quick Reference */}
                <Card className="border-slate-200 bg-white">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-semibold text-slate-600">
                      Quick Reference - 2026 Monthly Rates
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-2 gap-3">
                      <div className="flex items-center justify-between p-3 bg-violet-50 rounded-lg">
                        <span className="text-sm text-slate-600">3 Devices</span>
                        <span className="font-mono font-bold text-violet-700">R200</span>
                      </div>
                      <div className="flex items-center justify-between p-3 bg-orange-50 rounded-lg">
                        <span className="text-sm text-slate-600">4 Devices</span>
                        <span className="font-mono font-bold text-orange-600">R300</span>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </div>
          </TabsContent>

          {/* Refund Tab */}
          <TabsContent value="refund">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              {/* Input Section */}
              <div className="space-y-6">
                <Card className="border-slate-200 bg-white">
                  <CardHeader>
                    <CardTitle className="text-lg font-bold font-heading flex items-center gap-2">
                      <RotateCcw className="w-5 h-5 text-orange-500" />
                      Calculate Refund
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-6">
                    {/* Amount Input */}
                    <div className="space-y-2">
                      <Label htmlFor="refund-amount">Voucher Amount (R)</Label>
                      <Input
                        id="refund-amount"
                        type="number"
                        min="0"
                        step="0.01"
                        value={refundAmount}
                        onChange={(e) => setRefundAmount(e.target.value)}
                        placeholder="Enter amount paid"
                        className="font-mono"
                        data-testid="refund-amount-input"
                      />
                    </div>

                    {/* Duration Selection */}
                    <div className="space-y-2">
                      <Label>Voucher Duration</Label>
                      <Select value={refundDuration} onValueChange={setRefundDuration}>
                        <SelectTrigger data-testid="refund-duration-select">
                          <SelectValue placeholder="Select duration" />
                        </SelectTrigger>
                        <SelectContent>
                          {DURATION_OPTIONS.map((option) => (
                            <SelectItem key={option.value} value={option.value}>
                              {option.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>

                    {/* Start Date */}
                    <div className="space-y-2">
                      <Label htmlFor="refund-start-date">Voucher Start Date</Label>
                      <Input
                        id="refund-start-date"
                        type="date"
                        value={refundStartDate}
                        onChange={(e) => setRefundStartDate(e.target.value)}
                        data-testid="refund-start-date-input"
                      />
                      <p className="text-xs text-slate-500">
                        Select the date when the customer started using the voucher
                      </p>
                    </div>

                    <Button
                      onClick={handleRefundCalculate}
                      disabled={refundLoading}
                      className="w-full bg-orange-500 hover:bg-orange-600 h-12 text-lg font-medium"
                      data-testid="calculate-refund-btn"
                    >
                      {refundLoading ? "Calculating..." : "Calculate Refund"}
                    </Button>
                  </CardContent>
                </Card>

                {/* Info Card */}
                <Card className="border-slate-200 bg-orange-50">
                  <CardContent className="p-4">
                    <div className="flex items-start gap-3">
                      <Info className="w-5 h-5 text-orange-600 mt-0.5" />
                      <div className="text-sm text-slate-600">
                        <p className="font-medium text-slate-700 mb-1">How refund works</p>
                        <p>
                          Refund is calculated by dividing the voucher amount by total days,
                          then multiplying by the remaining unused days from the selected start date.
                        </p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Result Section */}
              <div className="space-y-6">
                {refundResult ? (
                  <Card className="border-slate-200 bg-white animate-fade-in" data-testid="refund-result-card">
                    <CardHeader className="pb-2">
                      <CardTitle className="text-lg font-bold font-heading flex items-center gap-2">
                        <DollarSign className="w-5 h-5 text-orange-500" />
                        Refund Result
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      {/* Main Result */}
                      <div className="bg-gradient-to-br from-orange-500 to-orange-600 rounded-xl p-6 text-white mb-6">
                        <p className="text-sm opacity-90 mb-1">Refund Amount</p>
                        <p className="text-5xl font-extrabold font-mono" data-testid="refund-amount-result">
                          R{refundResult.refund_amount.toFixed(2)}
                        </p>
                        <p className="text-sm opacity-75 mt-2">
                          For {refundResult.days_remaining} remaining days
                        </p>
                      </div>

                      {/* Breakdown */}
                      <div className="space-y-4">
                        <h4 className="font-semibold text-slate-700 flex items-center gap-2">
                          <Calendar className="w-4 h-4" />
                          Refund Breakdown
                        </h4>
                        
                        <div className="grid grid-cols-2 gap-4">
                          <div className="bg-slate-50 rounded-lg p-4">
                            <p className="text-xs text-slate-500 uppercase tracking-wide">Original Amount</p>
                            <p className="text-lg font-bold text-slate-900 mt-1 font-mono" data-testid="refund-original">
                              R{refundResult.original_amount.toFixed(2)}
                            </p>
                          </div>
                          <div className="bg-slate-50 rounded-lg p-4">
                            <p className="text-xs text-slate-500 uppercase tracking-wide">Duration</p>
                            <p className="text-lg font-bold text-slate-900 mt-1">
                              {refundResult.duration_weeks} week{refundResult.duration_weeks > 1 ? 's' : ''}
                            </p>
                          </div>
                          <div className="bg-slate-50 rounded-lg p-4">
                            <p className="text-xs text-slate-500 uppercase tracking-wide">Days Used</p>
                            <p className="text-lg font-bold text-red-600 mt-1" data-testid="refund-days-used">
                              {refundResult.days_used} days
                            </p>
                          </div>
                          <div className="bg-slate-50 rounded-lg p-4">
                            <p className="text-xs text-slate-500 uppercase tracking-wide">Days Remaining</p>
                            <p className="text-lg font-bold text-emerald-600 mt-1" data-testid="refund-days-remaining">
                              {refundResult.days_remaining} days
                            </p>
                          </div>
                        </div>

                        {/* Formula */}
                        <div className="bg-orange-50 rounded-lg p-4 mt-4">
                          <p className="text-xs text-orange-700 uppercase tracking-wide mb-2">Formula</p>
                          <p className="font-mono text-sm text-slate-700" data-testid="refund-formula">
                            R{refundResult.original_amount.toFixed(2)} ÷ {refundResult.total_days} days × {refundResult.days_remaining} days = <strong>R{refundResult.refund_amount.toFixed(2)}</strong>
                          </p>
                          <p className="text-xs text-slate-500 mt-2">
                            Daily rate: R{refundResult.daily_rate.toFixed(2)}
                          </p>
                        </div>

                        {/* Summary */}
                        <div className="bg-slate-100 rounded-lg p-4 mt-4">
                          <div className="flex items-center justify-between">
                            <span className="text-sm text-slate-600">Amount Used</span>
                            <span className="font-mono font-bold text-slate-700">
                              R{(refundResult.original_amount - refundResult.refund_amount).toFixed(2)}
                            </span>
                          </div>
                          <div className="flex items-center justify-between mt-2 pt-2 border-t border-slate-200">
                            <span className="text-sm font-semibold text-slate-700">Refund Due</span>
                            <span className="font-mono font-bold text-orange-600 text-lg">
                              R{refundResult.refund_amount.toFixed(2)}
                            </span>
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ) : (
                  <Card className="border-slate-200 bg-white border-dashed">
                    <CardContent className="py-16 text-center">
                      <RotateCcw className="w-16 h-16 text-slate-200 mx-auto mb-4" />
                      <p className="text-slate-500">
                        Enter voucher details and click "Calculate Refund" to see the result
                      </p>
                    </CardContent>
                  </Card>
                )}

                {/* Quick Reference */}
                <Card className="border-slate-200 bg-white">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-semibold text-slate-600">
                      Voucher Duration Reference
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-2 gap-3">
                      {DURATION_OPTIONS.map((option) => (
                        <div key={option.value} className="flex items-center justify-between p-3 bg-slate-50 rounded-lg">
                          <span className="text-sm text-slate-600">{option.value} Week{parseInt(option.value) > 1 ? 's' : ''}</span>
                          <span className="font-mono font-bold text-slate-700">{parseInt(option.value) * 7} days</span>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </div>
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </Layout>
  );
}
