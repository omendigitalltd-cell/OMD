import { useState, useEffect, useCallback } from "react";
import { Layout } from "../components/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/table";
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
import {
  MessageSquare,
  Send,
  Clock,
  CheckCircle,
  XCircle,
  Calendar,
  RefreshCw,
} from "lucide-react";

const API_URL = process.env.REACT_APP_BACKEND_URL;

export default function Reminders() {
  const { getAuthHeader } = useAuth();
  const [logs, setLogs] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [sendingTest, setSendingTest] = useState(false);
  const [selectedCustomer, setSelectedCustomer] = useState("");
  const [scheduling, setScheduling] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      const [logsRes, customersRes] = await Promise.all([
        axios.get(`${API_URL}/api/reminders/logs`, getAuthHeader()),
        axios.get(`${API_URL}/api/customers`, getAuthHeader()),
      ]);
      setLogs(logsRes.data);
      setCustomers(customersRes.data.filter((c) => c.is_active));
    } catch (error) {
      console.error("Failed to fetch data:", error);
    } finally {
      setLoading(false);
    }
  }, [getAuthHeader]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleSendTest = async () => {
    if (!selectedCustomer) {
      toast.error("Please select a customer");
      return;
    }
    setSendingTest(true);
    try {
      const response = await axios.post(
        `${API_URL}/api/reminders/send-test?customer_id=${selectedCustomer}`,
        {},
        getAuthHeader()
      );
      toast.success(response.data.message);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to send test reminder");
    } finally {
      setSendingTest(false);
    }
  };

  const handleScheduleMonthly = async () => {
    setScheduling(true);
    try {
      const response = await axios.post(
        `${API_URL}/api/reminders/schedule-monthly`,
        {},
        getAuthHeader()
      );
      toast.success(response.data.message);
      fetchData();
    } catch (error) {
      toast.error("Failed to schedule reminders");
    } finally {
      setScheduling(false);
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case "sent":
        return <CheckCircle className="w-4 h-4 text-emerald-600" />;
      case "failed":
        return <XCircle className="w-4 h-4 text-red-600" />;
      default:
        return <Clock className="w-4 h-4 text-amber-600" />;
    }
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case "sent":
        return <Badge className="bg-emerald-100 text-emerald-700">Sent</Badge>;
      case "delivered":
        return <Badge className="bg-blue-100 text-blue-700">Delivered</Badge>;
      case "failed":
        return <Badge className="bg-red-100 text-red-700">Failed</Badge>;
      default:
        return <Badge className="bg-amber-100 text-amber-700">Pending</Badge>;
    }
  };

  const formatDate = (isoString) => {
    if (!isoString) return "-";
    return new Date(isoString).toLocaleString();
  };

  return (
    <Layout title="Reminders">
      <div className="space-y-6" data-testid="reminders-page">
        {/* Actions Card */}
        <Card className="border-slate-200 bg-white">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg font-bold font-heading flex items-center gap-2">
              <MessageSquare className="w-5 h-5 text-violet-600" />
              WhatsApp Reminders
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col lg:flex-row gap-4">
              {/* Send Test */}
              <div className="flex-1 bg-slate-50 rounded-lg p-4">
                <h4 className="font-medium text-slate-700 mb-3">Send Test Reminder</h4>
                <div className="flex gap-3">
                  <Select value={selectedCustomer} onValueChange={setSelectedCustomer}>
                    <SelectTrigger className="flex-1" data-testid="customer-select">
                      <SelectValue placeholder="Select a customer" />
                    </SelectTrigger>
                    <SelectContent>
                      {customers.map((customer) => (
                        <SelectItem key={customer.id} value={customer.id}>
                          {customer.name} ({customer.phone})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Button
                    onClick={handleSendTest}
                    disabled={sendingTest || !selectedCustomer}
                    className="bg-violet-600 hover:bg-violet-700"
                    data-testid="send-test-btn"
                  >
                    {sendingTest ? (
                      <RefreshCw className="w-4 h-4 animate-spin" />
                    ) : (
                      <Send className="w-4 h-4" />
                    )}
                    <span className="ml-2">Send Test</span>
                  </Button>
                </div>
              </div>

              {/* Schedule Monthly */}
              <div className="lg:w-80 bg-orange-50 rounded-lg p-4">
                <h4 className="font-medium text-slate-700 mb-3">Schedule Monthly Reminders</h4>
                <Button
                  onClick={handleScheduleMonthly}
                  disabled={scheduling}
                  variant="secondary"
                  className="w-full border-orange-200 hover:bg-orange-100"
                  data-testid="schedule-monthly-btn"
                >
                  {scheduling ? (
                    <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                  ) : (
                    <Calendar className="w-4 h-4 mr-2" />
                  )}
                  Schedule All Active Customers
                </Button>
              </div>
            </div>

            {/* Info banner */}
            <div className="mt-4 p-3 bg-amber-50 border border-amber-200 rounded-lg">
              <p className="text-sm text-amber-800">
                <strong>Note:</strong> WhatsApp reminders require configuration in Settings.
                Messages will be queued until WhatsApp API is configured.
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Reminder Logs */}
        <Card className="border-slate-200 bg-white">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-lg font-bold font-heading">
                Reminder History
              </CardTitle>
              <Button variant="ghost" size="icon" onClick={fetchData} data-testid="refresh-btn">
                <RefreshCw className="w-4 h-4" />
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="py-8 text-center text-slate-500">Loading...</div>
            ) : logs.length === 0 ? (
              <div className="py-12 text-center">
                <MessageSquare className="w-12 h-12 text-slate-200 mx-auto mb-4" />
                <p className="text-slate-500">No reminders sent yet</p>
                <p className="text-sm text-slate-400 mt-1">
                  Send a test reminder or schedule monthly reminders to get started
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Status</TableHead>
                      <TableHead>Customer</TableHead>
                      <TableHead>Phone</TableHead>
                      <TableHead>Message Preview</TableHead>
                      <TableHead>Scheduled For</TableHead>
                      <TableHead>Sent At</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {logs.map((log) => (
                      <TableRow key={log.id} className="table-row-hover" data-testid={`reminder-log-${log.id}`}>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            {getStatusIcon(log.status)}
                            {getStatusBadge(log.status)}
                          </div>
                        </TableCell>
                        <TableCell className="font-medium">{log.customer_name}</TableCell>
                        <TableCell className="font-mono text-sm">{log.customer_phone}</TableCell>
                        <TableCell className="max-w-xs truncate text-sm text-slate-500">
                          {log.message}
                        </TableCell>
                        <TableCell className="text-sm">{formatDate(log.scheduled_for)}</TableCell>
                        <TableCell className="text-sm">{formatDate(log.sent_at)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </Layout>
  );
}
