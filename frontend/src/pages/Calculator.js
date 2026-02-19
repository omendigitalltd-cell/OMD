import { useState, useEffect } from "react";
import { Layout } from "../components/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Label } from "../components/ui/label";
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
import { Calculator as CalcIcon, Calendar, DollarSign, Info } from "lucide-react";

const API_URL = process.env.REACT_APP_BACKEND_URL;

export default function Calculator() {
  const { getAuthHeader } = useAuth();
  const [months, setMonths] = useState([]);
  const [selectedMonth, setSelectedMonth] = useState("1");
  const [selectedDay, setSelectedDay] = useState("1");
  const [selectedPlan, setSelectedPlan] = useState("3_devices");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

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

  return (
    <Layout title="Pro-rata Calculator">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8" data-testid="calculator-page">
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
    </Layout>
  );
}
