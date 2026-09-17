import { Route, Routes } from "react-router-dom";
import { AlignPage, AppLayout, ContextPage } from "./pages/AppPages";
import { LoginPage } from "./pages/LoginPage";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LoginPage />} />
      <Route path="/app" element={<AppLayout />}>
        <Route index element={<ContextPage />} />
        <Route path="align" element={<AlignPage />} />
      </Route>
    </Routes>
  );
}
