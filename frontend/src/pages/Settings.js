import { useState, useEffect } from "react";
import { Layout } from "../components/Layout";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Textarea } from "../components/ui/textarea";
import { Switch } from "../components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { useAuth } from "../context/AuthContext";
import axios from "axios";
import { toast } from "sonner";
import {
  Settings as SettingsIcon,
  MessageSquare,
  Bell,
  Save,
  ExternalLink,
  Info,
} from "lucide-react";

const API_URL = process.env.REACT_APP_BACKEND_URL;

export default function Settings() {
  const { getAuthHeader } = useAuth();
  const [whatsappConfig, setWhatsappConfig] = useState({
    phone_number_id: "",
    business_account_id: "",
    access_token: "",
    verify_token: "",
    is_configured: false,
  });
  const [reminderSettings, setReminderSettings] = useState({
    enabled: true,
    reminder_day: 28,
    reminder_message: "Hi {name}, this is a friendly reminder that your WiFi subscription of R{amount} is due on the last day of this month. Voucher: {voucher_code}",
  });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const fetchSettings = async () => {
      try {
        const [whatsappRes, reminderRes] = await Promise.all([
          axios.get(`${API_URL}/api/settings/whatsapp`, getAuthHeader()),
          axios.get(`${API_URL}/api/settings/reminders`, getAuthHeader()),
        ]);
        setWhatsappConfig(whatsappRes.data);
        setReminderSettings(reminderRes.data);
      } catch (error) {
        console.error("Failed to fetch settings:", error);
      }
    };
    fetchSettings();
  }, [getAuthHeader]);

  const handleSaveWhatsApp = async () => {
    setSaving(true);
    try {
      const configToSave = {
        ...whatsappConfig,
        is_configured: !!(
          whatsappConfig.phone_number_id &&
          whatsappConfig.business_account_id &&
          whatsappConfig.access_token
        ),
      };
      await axios.put(`${API_URL}/api/settings/whatsapp`, configToSave, getAuthHeader());
      setWhatsappConfig(configToSave);
      toast.success("WhatsApp settings saved successfully");
    } catch (error) {
      toast.error("Failed to save WhatsApp settings");
    } finally {
      setSaving(false);
    }
  };

  const handleSaveReminders = async () => {
    setSaving(true);
    try {
      await axios.put(`${API_URL}/api/settings/reminders`, reminderSettings, getAuthHeader());
      toast.success("Reminder settings saved successfully");
    } catch (error) {
      toast.error("Failed to save reminder settings");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Layout title="Settings">
      <div className="max-w-4xl" data-testid="settings-page">
        <Tabs defaultValue="whatsapp" className="space-y-6">
          <TabsList className="bg-slate-100">
            <TabsTrigger value="whatsapp" className="data-[state=active]:bg-white" data-testid="whatsapp-tab">
              <MessageSquare className="w-4 h-4 mr-2" />
              WhatsApp API
            </TabsTrigger>
            <TabsTrigger value="reminders" className="data-[state=active]:bg-white" data-testid="reminders-tab">
              <Bell className="w-4 h-4 mr-2" />
              Reminder Settings
            </TabsTrigger>
          </TabsList>

          {/* WhatsApp Settings */}
          <TabsContent value="whatsapp">
            <Card className="border-slate-200 bg-white">
              <CardHeader>
                <CardTitle className="text-lg font-bold font-heading flex items-center gap-2">
                  <MessageSquare className="w-5 h-5 text-violet-600" />
                  WhatsApp Business API Configuration
                </CardTitle>
                <CardDescription>
                  Configure your WhatsApp Business API credentials to send reminders
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Setup guide */}
                <div className="bg-violet-50 rounded-lg p-4">
                  <div className="flex items-start gap-3">
                    <Info className="w-5 h-5 text-violet-600 mt-0.5" />
                    <div className="text-sm">
                      <p className="font-medium text-violet-800 mb-1">How to get your credentials:</p>
                      <ol className="text-violet-700 space-y-1 list-decimal list-inside">
                        <li>Go to <a href="https://developers.facebook.com" target="_blank" rel="noopener noreferrer" className="underline">Meta for Developers</a></li>
                        <li>Create or select your app with WhatsApp product</li>
                        <li>Navigate to WhatsApp {">"} API Setup</li>
                        <li>Copy your Phone Number ID, Business Account ID, and Access Token</li>
                      </ol>
                      <a
                        href="https://developers.facebook.com/docs/whatsapp/cloud-api/get-started"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-violet-600 hover:text-violet-700 mt-2 font-medium"
                      >
                        View full documentation
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    </div>
                  </div>
                </div>

                <div className="grid gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="phone_number_id">Phone Number ID</Label>
                    <Input
                      id="phone_number_id"
                      value={whatsappConfig.phone_number_id}
                      onChange={(e) =>
                        setWhatsappConfig({ ...whatsappConfig, phone_number_id: e.target.value })
                      }
                      placeholder="e.g., 123456789012345"
                      className="font-mono"
                      data-testid="phone-number-id-input"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="business_account_id">WhatsApp Business Account ID</Label>
                    <Input
                      id="business_account_id"
                      value={whatsappConfig.business_account_id}
                      onChange={(e) =>
                        setWhatsappConfig({ ...whatsappConfig, business_account_id: e.target.value })
                      }
                      placeholder="e.g., 123456789012345"
                      className="font-mono"
                      data-testid="business-account-id-input"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="access_token">Access Token</Label>
                    <Input
                      id="access_token"
                      type="password"
                      value={whatsappConfig.access_token}
                      onChange={(e) =>
                        setWhatsappConfig({ ...whatsappConfig, access_token: e.target.value })
                      }
                      placeholder="Your WhatsApp access token"
                      data-testid="access-token-input"
                    />
                    <p className="text-xs text-slate-500">
                      Keep this secure. Never share your access token.
                    </p>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="verify_token">Webhook Verify Token</Label>
                    <Input
                      id="verify_token"
                      value={whatsappConfig.verify_token}
                      onChange={(e) =>
                        setWhatsappConfig({ ...whatsappConfig, verify_token: e.target.value })
                      }
                      placeholder="Your custom webhook verify token"
                      className="font-mono"
                      data-testid="verify-token-input"
                    />
                    <p className="text-xs text-slate-500">
                      Used to verify webhook callbacks from WhatsApp
                    </p>
                  </div>
                </div>

                {/* Status indicator */}
                <div className={`p-4 rounded-lg ${whatsappConfig.is_configured ? 'bg-emerald-50' : 'bg-amber-50'}`}>
                  <div className="flex items-center gap-2">
                    <div className={`w-2 h-2 rounded-full ${whatsappConfig.is_configured ? 'bg-emerald-500' : 'bg-amber-500'}`} />
                    <span className={`text-sm font-medium ${whatsappConfig.is_configured ? 'text-emerald-700' : 'text-amber-700'}`}>
                      {whatsappConfig.is_configured ? "WhatsApp API Configured" : "WhatsApp API Not Configured"}
                    </span>
                  </div>
                </div>

                <Button onClick={handleSaveWhatsApp} disabled={saving} className="bg-violet-600 hover:bg-violet-700" data-testid="save-whatsapp-btn">
                  <Save className="w-4 h-4 mr-2" />
                  {saving ? "Saving..." : "Save WhatsApp Settings"}
                </Button>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Reminder Settings */}
          <TabsContent value="reminders">
            <Card className="border-slate-200 bg-white">
              <CardHeader>
                <CardTitle className="text-lg font-bold font-heading flex items-center gap-2">
                  <Bell className="w-5 h-5 text-violet-600" />
                  Reminder Configuration
                </CardTitle>
                <CardDescription>
                  Configure when and how reminders are sent to customers
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Enable/Disable */}
                <div className="flex items-center justify-between p-4 bg-slate-50 rounded-lg">
                  <div>
                    <p className="font-medium text-slate-700">Enable Automatic Reminders</p>
                    <p className="text-sm text-slate-500">Send payment reminders to customers</p>
                  </div>
                  <Switch
                    checked={reminderSettings.enabled}
                    onCheckedChange={(checked) =>
                      setReminderSettings({ ...reminderSettings, enabled: checked })
                    }
                    data-testid="enable-reminders-switch"
                  />
                </div>

                {/* Reminder Day */}
                <div className="space-y-2">
                  <Label htmlFor="reminder_day">Reminder Day of Month</Label>
                  <Input
                    id="reminder_day"
                    type="number"
                    min="1"
                    max="28"
                    value={reminderSettings.reminder_day}
                    onChange={(e) =>
                      setReminderSettings({
                        ...reminderSettings,
                        reminder_day: parseInt(e.target.value) || 28,
                      })
                    }
                    className="w-32"
                    data-testid="reminder-day-input"
                  />
                  <p className="text-xs text-slate-500">
                    Reminders will be sent on this day each month (1-28 recommended)
                  </p>
                </div>

                {/* Message Template */}
                <div className="space-y-2">
                  <Label htmlFor="reminder_message">Reminder Message Template</Label>
                  <Textarea
                    id="reminder_message"
                    value={reminderSettings.reminder_message}
                    onChange={(e) =>
                      setReminderSettings({ ...reminderSettings, reminder_message: e.target.value })
                    }
                    rows={4}
                    data-testid="reminder-message-input"
                  />
                  <div className="bg-slate-50 rounded-lg p-3">
                    <p className="text-xs text-slate-600 font-medium mb-1">Available variables:</p>
                    <div className="flex flex-wrap gap-2">
                      <code className="text-xs bg-white px-2 py-1 rounded border">{"{name}"}</code>
                      <code className="text-xs bg-white px-2 py-1 rounded border">{"{amount}"}</code>
                      <code className="text-xs bg-white px-2 py-1 rounded border">{"{voucher_code}"}</code>
                    </div>
                  </div>
                </div>

                <Button onClick={handleSaveReminders} disabled={saving} className="bg-violet-600 hover:bg-violet-700" data-testid="save-reminders-btn">
                  <Save className="w-4 h-4 mr-2" />
                  {saving ? "Saving..." : "Save Reminder Settings"}
                </Button>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </Layout>
  );
}
