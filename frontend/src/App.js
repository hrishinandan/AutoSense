import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Home from "./pages/Home";
import Dashboard from "./pages/Dashboard";
import Analysis from "./pages/Analysis";
import History from "./pages/History";
function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Home />} />
         <Route path="/dashboard" element={<Dashboard />} />
         <Route path="/analysis" element={<Analysis />} />
         <Route path="/history" element={<History />} />
      </Routes>
    </Router>
  );
}

export default App;