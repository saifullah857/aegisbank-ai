import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { Loading } from "./components/ui";
import { useAuth } from "./hooks/useAuth";
import AppLayout from "./layouts/AppLayout";
import Login from "./pages/Login";

const Dashboard = lazy(() => import("./pages/Dashboard"));
const Cases = lazy(() => import("./pages/Cases"));
const CaseDetail = lazy(() => import("./pages/CaseDetail"));
const Customers = lazy(() => import("./pages/Customers"));
const CustomerDetail = lazy(() => import("./pages/CustomerDetail"));
const Transactions = lazy(() => import("./pages/Transactions"));
const Investigations = lazy(() => import("./pages/Investigations"));
const Agents = lazy(() => import("./pages/Agents"));
const Analytics = lazy(() => import("./pages/Analytics"));
const Policies = lazy(() => import("./pages/Policies"));
const Audit = lazy(() => import("./pages/Audit"));
const SystemHealth = lazy(() => import("./pages/SystemHealth"));
const Settings = lazy(() => import("./pages/Settings"));
const Simulator = lazy(() => import("./pages/Simulator"));
const Demo = lazy(() => import("./pages/Demo"));
const Assistant = lazy(() => import("./pages/Assistant"));

function Protected() {
  const { user } = useAuth();
  return user ? <AppLayout /> : <Navigate to="/login" replace />;
}

export default function App() {
  const { user } = useAuth();
  return (
    <Suspense fallback={<Loading />}>
      <Routes>
        <Route path="/login" element={user ? <Navigate to="/" replace /> : <Login />} />
        <Route element={<Protected />}>
          <Route index element={<Dashboard />} />
          <Route path="cases" element={<Cases />} />
          <Route path="cases/:ref" element={<CaseDetail />} />
          <Route path="customers" element={<Customers />} />
          <Route path="customers/:id" element={<CustomerDetail />} />
          <Route path="transactions" element={<Transactions />} />
          <Route path="investigations" element={<Investigations />} />
          <Route path="agents" element={<Agents />} />
          <Route path="analytics" element={<Analytics />} />
          <Route path="policies" element={<Policies />} />
          <Route path="audit" element={<Audit />} />
          <Route path="health" element={<SystemHealth />} />
          <Route path="simulator" element={<Simulator />} />
          <Route path="demo" element={<Demo />} />
          <Route path="assistant" element={<Assistant />} />
          <Route path="settings" element={<Settings />} />
          <Route path="*" element={<div className="py-20 text-center text-ink-500">Page not found</div>} />
        </Route>
      </Routes>
    </Suspense>
  );
}
