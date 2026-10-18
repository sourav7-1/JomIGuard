export default function Loading() {
  return (
    <div aria-label="পাতা লোড হচ্ছে" aria-busy="true" className="mx-auto w-full max-w-5xl animate-pulse space-y-5 py-4">
      <div className="h-8 w-2/3 rounded bg-line/70" />
      <div className="h-4 w-full rounded bg-line/50" />
      <div className="h-4 w-5/6 rounded bg-line/50" />
      <div className="grid gap-4 pt-4 sm:grid-cols-2">
        <div className="h-36 rounded-xl bg-line/40" />
        <div className="h-36 rounded-xl bg-line/40" />
      </div>
    </div>
  );
}
