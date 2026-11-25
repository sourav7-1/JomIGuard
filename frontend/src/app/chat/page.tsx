import Link from "next/link";
import { T } from "@/lib/lang";

/** The land AI assistant is not ready; this page only says so (no input box, not in the nav). */
export default function ChatPage() {
  return (
    <div className="mx-auto max-w-2xl space-y-6 py-2">
      <header className="border-b border-line pb-7">
        <h1 className="text-3xl font-semibold leading-tight tracking-tight text-ink sm:text-4xl"><T bn="জমি সহকারী: শীঘ্রই আসছে" en="Land assistant: coming soon" /></h1>
        <p className="mt-3 text-base leading-7 text-muted"><T bn="কাগজ নিয়ে প্রশ্নের উত্তর দেওয়ার সহকারী এখনো তৈরি হচ্ছে। এখন কেসের ধাপগুলো ধরে এগোন।" en="The assistant that answers questions about papers is still being built. For now, follow your case's steps." /></p>
      </header>
      <Link href="/help" className="inline-flex min-h-11 items-center text-sm font-semibold text-accent underline decoration-gold decoration-2 underline-offset-4"><T bn="প্রশ্নোত্তর দেখুন" en="See the FAQ" /></Link>
    </div>
  );
}
