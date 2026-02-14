import { Car, LogOut, History, PlusCircle } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  if (!user) return null;

  return (
    <nav className="navbar">
      <div className="navbar-container">
        <Link to="/dashboard" className="navbar-brand">
          <Car size={28} />
          <span>Carval.ai</span>
        </Link>

        <div className="navbar-links">
          <Link to="/dashboard" className="nav-link">
            <History size={18} />
            <span>Dashboard</span>
          </Link>
          <Link to="/valuation" className="nav-link">
            <PlusCircle size={18} />
            <span>New Valuation</span>
          </Link>
        </div>

        <div className="navbar-right">
          <span className="navbar-user">{user.username}</span>
          <button onClick={handleLogout} className="btn-logout">
            <LogOut size={18} />
            <span>Logout</span>
          </button>
        </div>
      </div>
    </nav>
  );
}
