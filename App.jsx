import { lazy, Suspense } from "react";
import Loading from "./loading"; // File loading.js

const MyComponent = lazy(() => import("./MyComponent"));

function App() {
  return (
    <Suspense fallback={<Loading />}>
      <MyComponent />
    </Suspense>
  );
}

export default App; 