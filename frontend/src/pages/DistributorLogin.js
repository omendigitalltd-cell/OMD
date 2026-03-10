import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useDistributorAuth } from "../context/DistributorAuthContext";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Wifi, Eye, EyeOff, Users } from "lucide-react";
import { toast } from "sonner";

export default function DistributorLogin() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isLogin, setIsLogin] = useState(true);
  const [loading, setLoading] = useState(false);
  const { login, register } = useDistributorAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      if (isLogin) {
        await login(email, password);
        toast.success("Welcome back!");
      } else {
        await register(name, email, phone, password);
        toast.success("Account created successfully!");
      }
      navigate("/distributor");
    } catch (error) {
      const message = error.response?.data?.detail || "Authentication failed";
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div 
      className="min-h-screen flex items-center justify-center p-4 bg-gradient-to-br from-slate-900 to-slate-800"
      data-testid="distributor-login-page"
    >
      <Card className="w-full max-w-md shadow-xl border-slate-700 bg-slate-800/50 backdrop-blur animate-fade-in">
        <CardHeader className="text-center space-y-4">
          <div className="mx-auto w-16 h-16 bg-orange-500 rounded-2xl flex items-center justify-center shadow-lg">
            <Users className="w-8 h-8 text-white" />
          </div>
          <div>
            <CardTitle className="text-3xl font-extrabold text-white font-heading">
              Distributor Portal
            </CardTitle>
            <CardDescription className="text-slate-400 mt-2">
              {isLogin ? "Sign in to manage your voucher sales" : "Register as a network distributor"}
            </CardDescription>
          </div>
        </CardHeader>

        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-5">
            {!isLogin && (
              <>
                <div className="space-y-2">
                  <Label htmlFor="name" className="text-slate-300">Full Name</Label>
                  <Input
                    id="name"
                    type="text"
                    placeholder="John Doe"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    required={!isLogin}
                    className="h-11 bg-slate-700 border-slate-600 text-white placeholder:text-slate-400"
                    data-testid="name-input"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="phone" className="text-slate-300">Phone Number</Label>
                  <Input
                    id="phone"
                    type="tel"
                    placeholder="+27 XX XXX XXXX"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    required={!isLogin}
                    className="h-11 bg-slate-700 border-slate-600 text-white placeholder:text-slate-400"
                    data-testid="phone-input"
                  />
                </div>
              </>
            )}

            <div className="space-y-2">
              <Label htmlFor="email" className="text-slate-300">Email</Label>
              <Input
                id="email"
                type="email"
                placeholder="distributor@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="h-11 bg-slate-700 border-slate-600 text-white placeholder:text-slate-400"
                data-testid="email-input"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="password" className="text-slate-300">Password</Label>
              <div className="relative">
                <Input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  placeholder="Enter your password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  className="h-11 pr-10 bg-slate-700 border-slate-600 text-white placeholder:text-slate-400"
                  data-testid="password-input"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200"
                >
                  {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
            </div>

            <Button
              type="submit"
              disabled={loading}
              className="w-full h-11 bg-orange-500 hover:bg-orange-600 text-white font-medium transition-colors"
              data-testid="submit-btn"
            >
              {loading ? "Please wait..." : isLogin ? "Sign In" : "Create Account"}
            </Button>
          </form>

          <div className="mt-6 text-center">
            <button
              type="button"
              onClick={() => setIsLogin(!isLogin)}
              className="text-sm text-orange-400 hover:text-orange-300 font-medium"
              data-testid="toggle-auth-mode"
            >
              {isLogin ? "Need an account? Register" : "Already have an account? Sign in"}
            </button>
          </div>

          {/* Info */}
          <div className="mt-8 pt-6 border-t border-slate-700">
            <p className="text-xs text-slate-500 text-center mb-3">Earn 20% commission on every voucher sale!</p>
            <div className="bg-slate-700/50 rounded-lg p-3 text-center">
              <p className="text-sm text-slate-300">Upload proof of payments and earn commission</p>
            </div>
          </div>

          {/* Admin link */}
          <div className="mt-4 text-center">
            <a href="/login" className="text-xs text-slate-500 hover:text-slate-400">
              Admin Login →
            </a>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
