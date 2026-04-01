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
  RefreshCw,
  Users,
  Smartphone,
} from "lucide-react";

const API_URL = process.env.REACT_APP_BACKEND_URL;

export default function Reminders() {
  const { getAuthHeader } = useAuth();
  const [logs, setLogs] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedCustomer, setSelectedCustomer] = useState("");
  const [sendingReminder, setSendingReminder] = useState(false);
  const [sendingVoucher, setSendingVoucher] = useState(false);
  const [sendingBulk, setSendingBulk] = useState(false);
  const [messagingStatus, setMessagingStatus] = useState(null);

  const fetchData = useCallback(async () => {
    try {
      const [logsRes, customersRes, statusRes] = await Promise.all([
        axios.get(`${API_URL}/api/messaging/logs`, getAuthHeader()),
        axios.get(`${API_URL}/api/customers`, getAuthHeader()),
        axios.get(`${API_URL}/api/messaging/status`, getAuthHeader()),
      ]);
      setLogs(logsRes.data);
      setCustomers(customersRes.data.filter((c) => c.is_active));
      setMessagingStatus(statusRes.data);
    } catch (error) {
      console.error("Failed to fetch data:", error);
    } finally {
      setLoading(false);
    }
  }, [getAuthHeader]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleSendReminder = async () => {
    if (!selectedCustomer) {
      toast.error("Please select a customer");
      return;
    }
    setSendingReminder(true);
    try {
      const response = await axios.post(
        `${API_URL}/api/messaging/send-reminder`,
        { customer_id: selectedCustomer, channel: "sms" },
        getAuthHeader()
      );
      toast.success(response.data.message);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to send reminder");
    } finally {
      setSendingReminder(false);
    }
  };

  const handleSendVoucher = async () => {
    if (!selectedCustomer) {
      toast.error("Please select a customer");
      return;
    }
    setSendingVoucher(true);
    try {
      const response = await axios.post(
        `${API_URL}/api/messaging/send-voucher`,
        { customer_id: selectedCustomer, channel: "sms" },
        getAuthHeader()
      );
      toast.success(response.data.message);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to send voucher");
    } finally {
      setSendingVoucher(false);
    }
  };

  const handleSendBulkReminders = async () => {
    if (!window.confirm("Send payment reminders to ALL active customers via SMS?")) {
      return;
    }
    setSendingBulk(true);
    try {
      const response = await axios.post(
        `${API_URL}/api/messaging/send-bulk-reminders`,
        { channel: "sms" },
        getAuthHeader()
      );
      toast.success(response.data.message);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to send bulk reminders");
    } finally {
      setSendingBulk(false);
    }
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case "sent":
        return <Badge className="bg-emerald-100 text-emerald-700"><CheckCircle className="w-3 h-3 mr-1" />Sent</Badge>;
      case "failed":
        return <Badge className="bg-red-100 text-red-700"><XCircle className="w-3 h-3 mr-1" />Failed</Badge>;
      default:
        return <Badge className="bg-amber-100 text-amber-700"><Clock className="w-3 h-3 mr-1" />Pending</Badge>;
    }
  };

  const formatDate = (isoString) => {
    if (!isoString) return "-";
    return new Date(isoString).toLocaleString();
  };

  const isConfigured = messagingStatus?.bulksms_configured;

  return (
    <Layout title="SMS Messaging">
      <div className="space-y-6" data-testid="reminders-page">
        {/* Status Banner */}
        {messagingStatus && (
          <Card className={`border-2 ${isConfigured ? 'border-emerald-200 bg-emerald-50' : 'border-amber-200 bg-amber-50'}`}>
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className={`w-3 h-3 rounded-full ${isConfigured ? 'bg-emerald-500' : 'bg-amber-500'}`} />
                <span className={`font-medium ${isConfigured ? 'text-emerald-700' : 'text-amber-700'}`} data-testid="sms-status-text">
                  {isConfigured
                    ? "BulkSMS Connected - SMS Ready"
                    : "BulkSMS Not Configured"}
                </span>
                {isConfigured && (
                  <div className="ml-auto">
                    <Badge className="bg-blue-100 text-blue-700">
                      <Smartphone className="w-3 h-3 mr-1" />SMS
                    </Badge>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Actions Card */}
        <Card className="border-slate-200 bg-white">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg font-bold font-heading flex items-center gap-2">
              <MessageSquare className="w-5 h-5 text-violet-600" />
              Send SMS via BulkSMS
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Single Customer Messaging */}
              <div className="bg-slate-50 rounded-lg p-4 space-y-4">
                <h4 className="font-medium text-slate-700">Send to Customer</h4>

                <Select value={selectedCustomer} onValueChange={setSelectedCustomer}>
                  <SelectTrigger data-testid="customer-select">
                    <SelectValue placeholder="Select customer" />
                  </SelectTrigger>
                  <SelectContent>
                    {customers.map((customer) => (
                      <SelectItem key={customer.id} value={customer.id}>
                        {customer.name} ({customer.phone})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                <div className="flex gap-3">
                  <Button
                    onClick={handleSendReminder}
                    disabled={sendingReminder || !selectedCustomer || !isConfigured}
                    className="flex-1 bg-violet-600 hover:bg-violet-700"
                    data-testid="send-reminder-btn"
                  >
                    {sendingReminder ? (
                      <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                    ) : (
                      <Send className="w-4 h-4 mr-2" />
                    )}
                    Payment Reminder
                  </Button>

                  <Button
                    onClick={handleSendVoucher}
                    disabled={sendingVoucher || !selectedCustomer || !isConfigured}
                    variant="secondary"
                    className="flex-1"
                    data-testid="send-voucher-btn"
                  >
                    {sendingVoucher ? (
                      <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                    ) : (
                      <Send className="w-4 h-4 mr-2" />
                    )}
                    Send Voucher
                  </Button>
                </div>
              </div>

              {/* Bulk Messaging */}
              <div className="bg-orange-50 rounded-lg p-4 space-y-4">
                <h4 className="font-medium text-slate-700">Bulk SMS Reminders</h4>
                <p className="text-sm text-slate-500">
                  Send payment reminders to all {customers.length} active customers via SMS
                </p>

                <Button
                  onClick={handleSendBulkReminders}
                  disabled={sendingBulk || customers.length === 0 || !isConfigured}
                  className="w-full bg-orange-500 hover:bg-orange-600"
                  data-testid="send-bulk-btn"
                >
                  {sendingBulk ? (
                    <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                  ) : (
                    <Users className="w-4 h-4 mr-2" />
                  )}
                  Send SMS to All ({customers.length})
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Message Logs */}
        <Card className="border-slate-200 bg-white">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-lg font-bold font-heading">
                Message History
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
                <p className="text-slate-500">No messages sent yet</p>
                <p className="text-sm text-slate-400 mt-1">
                  Send a reminder or voucher to get started
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Date</TableHead>
                      <TableHead>Customer</TableHead>
                      <TableHead>Phone</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead>Channel</TableHead>
                      <TableHead>Status</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {logs.map((log) => (
                      <TableRow key={log.id} className="table-row-hover" data-testid={`log-row-${log.id}`}>
                        <TableCell className="text-sm">
                          {formatDate(log.created_at)}
                        </TableCell>
                        <TableCell className="font-medium">{log.customer_name}</TableCell>
                        <TableCell className="font-mono text-sm">{log.customer_phone}</TableCell>
                        <TableCell>
                          <Badge className={log.message_type === "payment_reminder" ? "bg-violet-100 text-violet-700" : "bg-blue-100 text-blue-700"}>
                            {log.message_type === "payment_reminder" ? "Reminder" : "Voucher"}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-1">
                            <Smartphone className="w-4 h-4 text-blue-600" />
                            <span className="text-sm">SMS</span>
                          </div>
                        </TableCell>
                        <TableCell>{getStatusBadge(log.status)}</TableCell>
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
