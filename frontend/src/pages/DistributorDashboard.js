import { useState, useEffect, useCallback } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useDistributorAuth } from "../context/DistributorAuthContext";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Textarea } from "../components/ui/textarea";
import { Badge } from "../components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "../components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/table";
import { Toaster } from "../components/ui/sonner";
import axios from "axios";
import { toast } from "sonner";
import {
  Upload,
  DollarSign,
  FileText,
  LogOut,
  CheckCircle,
  Clock,
  XCircle,
  Plus,
  Wifi,
  Users,
} from "lucide-react";

const API_URL = process.env.REACT_APP_BACKEND_URL;

export default function DistributorDashboard() {
  const { distributor, logout, getAuthHeader, isAuthenticated, loading } = useDistributorAuth();
  const navigate = useNavigate();
  
  const [commission, setCommission] = useState(null);
  const [proofs, setProofs] = useState([]);
  const [loadingData, setLoadingData] = useState(true);
  
  // Upload dialog state
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [customerPhone, setCustomerPhone] = useState("");
  const [notes, setNotes] = useState("");
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState(null);

  const fetchData = useCallback(async () => {
    if (!isAuthenticated) return;
    
    try {
      const [commissionRes, proofsRes] = await Promise.all([
        axios.get(`${API_URL}/api/distributor/commission`, getAuthHeader()),
        axios.get(`${API_URL}/api/distributor/proofs`, getAuthHeader()),
      ]);
      setCommission(commissionRes.data);
      setProofs(proofsRes.data);
    } catch (error) {
      console.error("Failed to fetch data:", error);
    } finally {
      setLoadingData(false);
    }
  }, [getAuthHeader, isAuthenticated]);

  useEffect(() => {
    if (!loading && !isAuthenticated) {
      navigate("/distributor/login");
    }
  }, [loading, isAuthenticated, navigate]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleUpload = async (e) => {
    e.preventDefault();
    
    if (!file) {
      toast.error("Please select a file");
      return;
    }
    
    setUploading(true);
    setUploadResult(null);
    const formData = new FormData();
    formData.append("customer_phone", customerPhone);
    formData.append("notes", notes);
    formData.append("file", file);
    
    try {
      const response = await axios.post(`${API_URL}/api/distributor/proofs`, formData, {
        ...getAuthHeader(),
        headers: {
          ...getAuthHeader().headers,
          "Content-Type": "multipart/form-data",
        },
      });
      setUploadResult(response.data);
      toast.success("Proof uploaded successfully!");
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Upload failed - could not read file");
    } finally {
      setUploading(false);
    }
  };

  const resetForm = () => {
    setCustomerPhone("");
    setNotes("");
    setFile(null);
    setUploadResult(null);
  };

  const closeUploadDialog = () => {
    setUploadDialogOpen(false);
    resetForm();
  };

  const handleLogout = () => {
    logout();
    navigate("/distributor/login");
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case "matched":
        return <Badge className="bg-emerald-100 text-emerald-700"><CheckCircle className="w-3 h-3 mr-1" />Matched</Badge>;
      case "paid":
        return <Badge className="bg-blue-100 text-blue-700">Paid</Badge>;
      case "rejected":
        return <Badge className="bg-red-100 text-red-700"><XCircle className="w-3 h-3 mr-1" />Rejected</Badge>;
      default:
        return <Badge className="bg-amber-100 text-amber-700"><Clock className="w-3 h-3 mr-1" />Pending</Badge>;
    }
  };

  if (loading || loadingData) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center">
        <div className="text-white">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-900" data-testid="distributor-dashboard">
      <Toaster position="top-right" richColors />
      
      {/* Header */}
      <header className="bg-slate-800 border-b border-slate-700 px-4 lg:px-8 py-4">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-orange-500 rounded-lg">
              <Users className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="font-bold text-lg text-white font-heading">Distributor Portal</h1>
              <p className="text-xs text-slate-400">{distributor?.name}</p>
            </div>
          </div>
          <Button
            variant="ghost"
            onClick={handleLogout}
            className="text-slate-400 hover:text-white hover:bg-slate-700"
          >
            <LogOut className="w-4 h-4 mr-2" />
            Sign Out
          </Button>
        </div>
      </header>

      <main className="max-w-6xl mx-auto p-4 lg:p-8 space-y-6">
        {/* Commission Summary */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card className="bg-slate-800 border-slate-700">
            <CardContent className="p-6">
              <div className="flex items-center gap-3">
                <div className="p-3 bg-violet-500/20 rounded-xl">
                  <FileText className="w-6 h-6 text-violet-400" />
                </div>
                <div>
                  <p className="text-sm text-slate-400">Matched Sales</p>
                  <p className="text-2xl font-bold text-white font-mono">
                    R{commission?.total_matched_sales?.toFixed(2) || "0.00"}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-slate-800 border-slate-700">
            <CardContent className="p-6">
              <div className="flex items-center gap-3">
                <div className="p-3 bg-emerald-500/20 rounded-xl">
                  <DollarSign className="w-6 h-6 text-emerald-400" />
                </div>
                <div>
                  <p className="text-sm text-slate-400">Total Commission</p>
                  <p className="text-2xl font-bold text-emerald-400 font-mono">
                    R{commission?.total_commission?.toFixed(2) || "0.00"}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-slate-800 border-slate-700">
            <CardContent className="p-6">
              <div className="flex items-center gap-3">
                <div className="p-3 bg-blue-500/20 rounded-xl">
                  <CheckCircle className="w-6 h-6 text-blue-400" />
                </div>
                <div>
                  <p className="text-sm text-slate-400">Paid Out</p>
                  <p className="text-2xl font-bold text-blue-400 font-mono">
                    R{commission?.paid_commission?.toFixed(2) || "0.00"}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-orange-500 to-orange-600 border-0">
            <CardContent className="p-6">
              <div className="flex items-center gap-3">
                <div className="p-3 bg-white/20 rounded-xl">
                  <DollarSign className="w-6 h-6 text-white" />
                </div>
                <div>
                  <p className="text-sm text-orange-100">Pending Payout</p>
                  <p className="text-2xl font-bold text-white font-mono">
                    R{commission?.pending_commission?.toFixed(2) || "0.00"}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Upload Button */}
        <Card className="bg-slate-800 border-slate-700">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-bold text-white font-heading">Upload Proof of Payment</h3>
                <p className="text-sm text-slate-400 mt-1">
                  Upload customer payment proofs to earn 20% commission
                </p>
              </div>
              <Button
                onClick={() => setUploadDialogOpen(true)}
                className="bg-orange-500 hover:bg-orange-600"
                data-testid="upload-proof-btn"
              >
                <Plus className="w-4 h-4 mr-2" />
                Upload Proof
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Proofs List */}
        <Card className="bg-slate-800 border-slate-700">
          <CardHeader>
            <CardTitle className="text-lg font-bold text-white font-heading flex items-center gap-2">
              <FileText className="w-5 h-5 text-orange-400" />
              Your Uploaded Proofs ({proofs.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            {proofs.length === 0 ? (
              <div className="py-12 text-center">
                <Upload className="w-12 h-12 text-slate-600 mx-auto mb-4" />
                <p className="text-slate-400">No proofs uploaded yet</p>
                <Button
                  onClick={() => setUploadDialogOpen(true)}
                  variant="link"
                  className="text-orange-400 mt-2"
                >
                  Upload your first proof
                </Button>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow className="border-slate-700">
                      <TableHead className="text-slate-400">Date</TableHead>
                      <TableHead className="text-slate-400">Reference</TableHead>
                      <TableHead className="text-slate-400">Amount</TableHead>
                      <TableHead className="text-slate-400">Commission (20%)</TableHead>
                      <TableHead className="text-slate-400">Status</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {proofs.map((proof) => (
                      <TableRow key={proof.id} className="border-slate-700">
                        <TableCell className="text-slate-300">
                          {new Date(proof.created_at).toLocaleDateString()}
                        </TableCell>
                        <TableCell className="font-mono text-slate-300">{proof.reference}</TableCell>
                        <TableCell className="font-mono text-white">R{proof.amount.toFixed(2)}</TableCell>
                        <TableCell className="font-mono text-emerald-400">
                          R{(proof.amount * 0.2).toFixed(2)}
                        </TableCell>
                        <TableCell>{getStatusBadge(proof.status)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>
      </main>

      {/* Upload Dialog */}
      <Dialog open={uploadDialogOpen} onOpenChange={setUploadDialogOpen}>
        <DialogContent className="bg-slate-800 border-slate-700 text-white">
          <DialogHeader>
            <DialogTitle className="font-heading">Upload Proof of Payment</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleUpload} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="reference" className="text-slate-300">Payment Reference *</Label>
              <Input
                id="reference"
                value={reference}
                onChange={(e) => setReference(e.target.value)}
                placeholder="e.g., REF123456"
                required
                className="bg-slate-700 border-slate-600 text-white"
                data-testid="reference-input"
              />
              <p className="text-xs text-slate-500">Enter the reference number from the payment</p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="amount" className="text-slate-300">Amount (R) *</Label>
              <Input
                id="amount"
                type="number"
                step="0.01"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                placeholder="e.g., 60.00"
                required
                className="bg-slate-700 border-slate-600 text-white font-mono"
                data-testid="amount-input"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="customer-phone" className="text-slate-300">Customer Phone (optional)</Label>
              <Input
                id="customer-phone"
                value={customerPhone}
                onChange={(e) => setCustomerPhone(e.target.value)}
                placeholder="+27 XX XXX XXXX"
                className="bg-slate-700 border-slate-600 text-white"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="notes" className="text-slate-300">Notes (optional)</Label>
              <Textarea
                id="notes"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Any additional notes..."
                rows={2}
                className="bg-slate-700 border-slate-600 text-white"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="file" className="text-slate-300">Proof File (Image/PDF) *</Label>
              <Input
                id="file"
                type="file"
                accept="image/*,.pdf"
                onChange={(e) => setFile(e.target.files[0])}
                required
                className="bg-slate-700 border-slate-600 text-white file:bg-slate-600 file:text-white file:border-0 file:mr-4"
                data-testid="file-input"
              />
            </div>

            <DialogFooter className="gap-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => setUploadDialogOpen(false)}
                className="border-slate-600 text-slate-300 hover:bg-slate-700"
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={uploading}
                className="bg-orange-500 hover:bg-orange-600"
                data-testid="submit-upload-btn"
              >
                {uploading ? "Uploading..." : "Upload Proof"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
