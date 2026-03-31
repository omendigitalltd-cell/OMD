import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { usePortalAuth } from "../context/PortalAuthContext";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "../components/ui/select";
import { Wifi, LogIn, UserPlus } from "lucide-react";

const API_URL = process.env.REACT_APP_BACKEND_URL;

export default function PortalLogin() {
  const [isRegister, setIsRegister] = useState(false);
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [accommodation, setAccommodation] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const { login } = usePortalAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const url = isRegister ? `${API_URL}/api/portal/register` : `${API_URL}/api/portal/login`;
      const body = isRegister
        ? { name: name.trim(), phone: phone.trim(), password, accommodation }
        : { phone: phone.trim(), password };

      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Authentication failed");
      }

      const data = await res.json();
      login(data.access_token, data.customer_id);
      navigate("/portal");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-emerald-900 flex items-center justify-center px-4">
      <Card className="w-full max-w-sm border-slate-700 bg-slate-800/80 backdrop-blur" data-testid="portal-login-card">
        <CardHeader className="text-center pb-2">
          <div className="w-14 h-14 bg-emerald-500 rounded-xl flex items-center justify-center mx-auto mb-3">
            <Wifi className="w-7 h-7 text-white" />
          </div>
          <CardTitle className="text-xl text-white">{isRegister ? "Create Account" : "Customer Portal"}</CardTitle>
          <p className="text-sm text-slate-400">{isRegister ? "Sign up to get started" : "Login with your phone"}</p>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            {isRegister && (
              <div className="space-y-1.5">
                <Label className="text-slate-300">Full Name</Label>
                <Input
                  placeholder="e.g. Thabo Mokoena"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required={isRegister}
                  className="bg-slate-700 border-slate-600 text-white placeholder:text-slate-500"
                  data-testid="portal-name-input"
                />
              </div>
            )}
            <div className="space-y-1.5">
              <Label className="text-slate-300">Phone Number</Label>
              <Input
                placeholder="e.g. 0812345678"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                required
                className="bg-slate-700 border-slate-600 text-white placeholder:text-slate-500"
                data-testid="portal-phone-input"
              />
            </div>
            <div className="space-y-1.5">
              <Label className="text-slate-300">Password</Label>
              <Input
                type="password"
                placeholder="Enter password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="bg-slate-700 border-slate-600 text-white placeholder:text-slate-500"
                data-testid="portal-password-input"
              />
            </div>
            {isRegister && (
              <div className="space-y-1.5">
                <Label className="text-slate-300">Accommodation</Label>
                <Select value={accommodation} onValueChange={setAccommodation}>
                  <SelectTrigger className="bg-slate-700 border-slate-600 text-white" data-testid="portal-accommodation-select">
                    <SelectValue placeholder="Select your accommodation" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="MAJOALE ROOMS">Majoale Rooms</SelectItem>
                    <SelectItem value="MAJOLA ROOMS">Majola Rooms</SelectItem>
                    <SelectItem value="91 CENTURY">91 Century</SelectItem>
                    <SelectItem value="MAHLASELA ROOMS">Mahlasela Rooms</SelectItem>
                    <SelectItem value="KB STUDENT ACCOMMODATION">KB Student Accommodation</SelectItem>
                    <SelectItem value="MOKOEPA CLUBVIEW ESTATE">Mokoepa Clubview Estate</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            )}

            {error && (
              <div className="bg-red-900/30 border border-red-700 text-red-400 rounded-lg p-2.5 text-sm" data-testid="portal-error">
                {error}
              </div>
            )}

            <Button
              type="submit"
              disabled={loading || (isRegister && !accommodation)}
              className="w-full h-11 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold"
              data-testid="portal-submit-btn"
            >
              {loading ? "Please wait..." : isRegister ? (
                <span className="flex items-center gap-2"><UserPlus className="w-4 h-4" /> Create Account</span>
              ) : (
                <span className="flex items-center gap-2"><LogIn className="w-4 h-4" /> Login</span>
              )}
            </Button>
          </form>

          <div className="mt-4 text-center">
            <button
              onClick={() => { setIsRegister(!isRegister); setError(null); }}
              className="text-sm text-emerald-400 hover:text-emerald-300"
              data-testid="portal-toggle-auth"
            >
              {isRegister ? "Already have an account? Login" : "Don't have an account? Register"}
            </button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
