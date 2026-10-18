import { LoginForm } from "./LoginForm";

export default async function LoginPage({ searchParams }: { searchParams: Promise<{ next?: string; expired?: string }> }) {
  const { next, expired } = await searchParams;
  return <section className="py-8 sm:py-14"><LoginForm nextPath={next || "/cases"} sessionExpired={expired === "1"} /></section>;
}
