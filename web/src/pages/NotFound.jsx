import { Link } from "react-router-dom";

export default function NotFound() {
  return (
    <div className="mx-auto max-w-xl px-4 py-20 text-center">
      <p className="font-display text-6xl font-bold text-teal">404</p>
      <h1 className="mt-3 font-display text-2xl font-semibold">This page doesn’t exist</h1>
      <Link to="/" className="mt-6 inline-block rounded-xl bg-ink px-5 py-3 font-semibold text-white">Back to search</Link>
    </div>
  );
}
