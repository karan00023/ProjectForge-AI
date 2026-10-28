import Link from "next/link";

export default function NotFound() {
  return (
    <main className="mx-auto mt-24 max-w-md space-y-3 px-4 text-center">
      <h1 className="text-2xl font-semibold">Page not found</h1>
      <p className="text-sm text-muted">The page you were looking for does not exist.</p>
      <Link href="/" className="text-sm text-accent-ink hover:underline">
        Back to the Command Center
      </Link>
    </main>
  );
}
