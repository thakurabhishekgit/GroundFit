import { Route, Routes } from "react-router-dom";
import { AlignPage, AppLayout, ContextPage, ProfilePage } from "./pages/AppPages";
import { LandingPage } from "./pages/LandingPage";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/app" element={<AppLayout />}>
        <Route index element={<ContextPage />} />
        <Route path="align" element={<AlignPage />} />
        <Route path="profile" element={<ProfilePage />} />
      </Route>
    </Routes>
  );
}
