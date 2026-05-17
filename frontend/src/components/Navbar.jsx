import { LogOut, History, PlusCircle, Shield } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import carvalIcon from "../assets/carval-icon.png";

export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  return (
    <nav className="navbar">
      <div className="navbar-container">
        <Link to="/" className="navbar-brand">
          <img src={carvalIcon} alt="Carval.ai" className="navbar-brand-icon" />
          <span>Carval<span className="brand-ai">.ai</span></span>
        </Link>

        {user && (
          <div className="navbar-links">
            <Link to="/dashboard" className="nav-link">
              <History size={18} />
              <span>Geçmiş</span>
            </Link>
            <Link to="/valuation" className="nav-link">
              <PlusCircle size={18} />
              <span>Yeni Değerleme</span>
            </Link>
            {user.is_admin && (
              <Link to="/admin" className="nav-link nav-link-admin">
                <Shield size={18} />
                <span>Admin</span>
              </Link>
            )}
          </div>
        )}

        <div className="navbar-right">
          {user ? (
            <>
              <span className="navbar-user">{user.username}</span>
              <button onClick={handleLogout} className="btn-logout">
                <LogOut size={18} />
                <span>Çıkış</span>
              </button>
            </>
          ) : (
            <>
              <Link to="/login" className="btn-ghost-sm">Giriş Yap</Link>
              <Link to="/register" className="btn-solid-sm">Üye Ol</Link>
            </>
          )}
        </div>
      </div>
    </nav>
  );
}
