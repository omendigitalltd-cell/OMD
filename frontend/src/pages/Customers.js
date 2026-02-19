import { useState, useEffect, useCallback } from "react";
import { Layout } from "../components/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "../components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/table";
import { Badge } from "../components/ui/badge";
import { useAuth } from "../context/AuthContext";
import axios from "axios";
import { toast } from "sonner";
import {
  Plus,
  Pencil,
  Trash2,
  Search,
  UserPlus,
  Phone,
  Key,
} from "lucide-react";

const API_URL = process.env.REACT_APP_BACKEND_URL;

const initialFormData = {
  name: "",
  phone: "",
  voucher_code: "",
  plan: "3_devices",
  start_date: new Date().toISOString().split("T")[0],
  is_active: true,
};

export default function Customers() {
  const { getAuthHeader } = useAuth();
  const [customers, setCustomers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [planFilter, setPlanFilter] = useState("all");
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [editingCustomer, setEditingCustomer] = useState(null);
  const [deletingCustomer, setDeletingCustomer] = useState(null);
  const [formData, setFormData] = useState(initialFormData);
  const [submitting, setSubmitting] = useState(false);

  const fetchCustomers = useCallback(async () => {
    try {
      const response = await axios.get(`${API_URL}/api/customers`, getAuthHeader());
      setCustomers(response.data);
    } catch (error) {
      toast.error("Failed to fetch customers");
    } finally {
      setLoading(false);
    }
  }, [getAuthHeader]);

  useEffect(() => {
    fetchCustomers();
  }, [fetchCustomers]);

  const filteredCustomers = customers.filter((customer) => {
    const matchesSearch =
      customer.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      customer.phone.includes(searchTerm) ||
      customer.voucher_code.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesPlan = planFilter === "all" || customer.plan === planFilter;
    return matchesSearch && matchesPlan;
  });

  const openAddDialog = () => {
    setEditingCustomer(null);
    setFormData(initialFormData);
    setIsDialogOpen(true);
  };

  const openEditDialog = (customer) => {
    setEditingCustomer(customer);
    setFormData({
      name: customer.name,
      phone: customer.phone,
      voucher_code: customer.voucher_code,
      plan: customer.plan,
      start_date: customer.start_date,
      is_active: customer.is_active,
    });
    setIsDialogOpen(true);
  };

  const openDeleteDialog = (customer) => {
    setDeletingCustomer(customer);
    setIsDeleteDialogOpen(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);

    try {
      if (editingCustomer) {
        await axios.put(
          `${API_URL}/api/customers/${editingCustomer.id}`,
          formData,
          getAuthHeader()
        );
        toast.success("Customer updated successfully");
      } else {
        await axios.post(`${API_URL}/api/customers`, formData, getAuthHeader());
        toast.success("Customer added successfully");
      }
      setIsDialogOpen(false);
      fetchCustomers();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to save customer");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async () => {
    try {
      await axios.delete(
        `${API_URL}/api/customers/${deletingCustomer.id}`,
        getAuthHeader()
      );
      toast.success("Customer deleted successfully");
      setIsDeleteDialogOpen(false);
      fetchCustomers();
    } catch (error) {
      toast.error("Failed to delete customer");
    }
  };

  const generateVoucherCode = () => {
    const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
    let code = "HS-";
    for (let i = 0; i < 6; i++) {
      code += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    setFormData({ ...formData, voucher_code: code });
  };

  return (
    <Layout title="Customers">
      <div className="space-y-6" data-testid="customers-page">
        {/* Filters */}
        <Card className="border-slate-200 bg-white">
          <CardContent className="p-4">
            <div className="flex flex-col md:flex-row gap-4">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <Input
                  placeholder="Search by name, phone, or voucher code..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10"
                  data-testid="search-input"
                />
              </div>
              <Select value={planFilter} onValueChange={setPlanFilter}>
                <SelectTrigger className="w-full md:w-48" data-testid="plan-filter">
                  <SelectValue placeholder="Filter by plan" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Plans</SelectItem>
                  <SelectItem value="3_devices">3 Devices (R200)</SelectItem>
                  <SelectItem value="4_devices">4 Devices (R300)</SelectItem>
                </SelectContent>
              </Select>
              <Button onClick={openAddDialog} className="bg-violet-600 hover:bg-violet-700" data-testid="add-customer-btn">
                <Plus className="w-4 h-4 mr-2" />
                Add Customer
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Customers Table */}
        <Card className="border-slate-200 bg-white">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg font-bold font-heading">
              Customer List ({filteredCustomers.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="py-8 text-center text-slate-500">Loading...</div>
            ) : filteredCustomers.length === 0 ? (
              <div className="py-12 text-center">
                <UserPlus className="w-12 h-12 text-slate-300 mx-auto mb-4" />
                <p className="text-slate-500">No customers found</p>
                <Button onClick={openAddDialog} variant="link" className="text-violet-600 mt-2">
                  Add your first customer
                </Button>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Name</TableHead>
                      <TableHead>Phone</TableHead>
                      <TableHead>Voucher Code</TableHead>
                      <TableHead>Plan</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Start Date</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredCustomers.map((customer) => (
                      <TableRow key={customer.id} className="table-row-hover" data-testid={`customer-table-row-${customer.id}`}>
                        <TableCell className="font-medium">{customer.name}</TableCell>
                        <TableCell className="font-mono text-sm">{customer.phone}</TableCell>
                        <TableCell>
                          <code className="bg-slate-100 px-2 py-1 rounded text-sm font-mono">
                            {customer.voucher_code}
                          </code>
                        </TableCell>
                        <TableCell>
                          <Badge
                            className={
                              customer.plan === "3_devices"
                                ? "bg-violet-100 text-violet-700"
                                : "bg-orange-100 text-orange-700"
                            }
                          >
                            R{customer.monthly_rate}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <Badge
                            className={
                              customer.is_active
                                ? "bg-emerald-100 text-emerald-700"
                                : "bg-slate-100 text-slate-600"
                            }
                          >
                            {customer.is_active ? "Active" : "Inactive"}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-sm text-slate-500">
                          {customer.start_date}
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex justify-end gap-2">
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => openEditDialog(customer)}
                              className="hover:bg-violet-100 hover:text-violet-700"
                              data-testid={`edit-btn-${customer.id}`}
                            >
                              <Pencil className="w-4 h-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => openDeleteDialog(customer)}
                              className="hover:bg-red-100 hover:text-red-700"
                              data-testid={`delete-btn-${customer.id}`}
                            >
                              <Trash2 className="w-4 h-4" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Add/Edit Dialog */}
        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <DialogContent className="sm:max-w-md" data-testid="customer-dialog">
            <DialogHeader>
              <DialogTitle className="font-heading">
                {editingCustomer ? "Edit Customer" : "Add New Customer"}
              </DialogTitle>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="name">Customer Name</Label>
                <Input
                  id="name"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="Enter customer name"
                  required
                  data-testid="customer-name-input"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="phone">Phone Number</Label>
                <div className="relative">
                  <Phone className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                  <Input
                    id="phone"
                    value={formData.phone}
                    onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                    placeholder="+27 XX XXX XXXX"
                    className="pl-10"
                    required
                    data-testid="customer-phone-input"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="voucher_code">Voucher Code</Label>
                <div className="flex gap-2">
                  <div className="relative flex-1">
                    <Key className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                    <Input
                      id="voucher_code"
                      value={formData.voucher_code}
                      onChange={(e) => setFormData({ ...formData, voucher_code: e.target.value.toUpperCase() })}
                      placeholder="HS-XXXXXX"
                      className="pl-10 font-mono"
                      required
                      data-testid="customer-voucher-input"
                    />
                  </div>
                  <Button type="button" variant="secondary" onClick={generateVoucherCode} data-testid="generate-voucher-btn">
                    Generate
                  </Button>
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="plan">Plan</Label>
                <Select
                  value={formData.plan}
                  onValueChange={(value) => setFormData({ ...formData, plan: value })}
                >
                  <SelectTrigger data-testid="customer-plan-select">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="3_devices">3 Devices - R200/month</SelectItem>
                    <SelectItem value="4_devices">4 Devices - R300/month</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="start_date">Start Date</Label>
                <Input
                  id="start_date"
                  type="date"
                  value={formData.start_date}
                  onChange={(e) => setFormData({ ...formData, start_date: e.target.value })}
                  required
                  data-testid="customer-start-date-input"
                />
              </div>

              <DialogFooter className="gap-2">
                <Button type="button" variant="secondary" onClick={() => setIsDialogOpen(false)}>
                  Cancel
                </Button>
                <Button type="submit" disabled={submitting} className="bg-violet-600 hover:bg-violet-700" data-testid="save-customer-btn">
                  {submitting ? "Saving..." : editingCustomer ? "Update" : "Add Customer"}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>

        {/* Delete Confirmation Dialog */}
        <Dialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
          <DialogContent className="sm:max-w-md" data-testid="delete-dialog">
            <DialogHeader>
              <DialogTitle className="font-heading text-red-600">Delete Customer</DialogTitle>
            </DialogHeader>
            <p className="text-slate-600">
              Are you sure you want to delete <strong>{deletingCustomer?.name}</strong>? This action cannot be undone.
            </p>
            <DialogFooter className="gap-2">
              <Button variant="secondary" onClick={() => setIsDeleteDialogOpen(false)}>
                Cancel
              </Button>
              <Button onClick={handleDelete} className="bg-red-500 hover:bg-red-600" data-testid="confirm-delete-btn">
                Delete
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </Layout>
  );
}
